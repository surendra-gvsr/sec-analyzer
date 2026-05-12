"""
Phase 3 — GraphRAG index construction.

Builds a PropertyGraphIndex (LlamaIndex) backed by SimplePropertyGraphStore
(networkx, no external DB) + ChromaDB for vector search.

Key design decisions:
- Markdown is split at ## section boundaries before entity extraction so each
  Groq call stays well within the 8192-token context window.
- After entity extraction, YEAR_OVER_YEAR edges are computed by matching the
  same metric name across different filing years for the same ticker.
- The graph is persisted to data/graph_store/property_graph.json so the API
  server can load it in ~1-2 s at startup without rebuilding.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.pipeline.llama_parser import get_parsed_markdown, list_parsed

log = logging.getLogger(__name__)


def _split_by_sections(markdown: str, max_tokens: int = 1800) -> List[str]:
    """
    Split a Markdown document at ## headings, keeping each section under
    max_tokens characters (rough proxy: 1 token ≈ 4 chars).
    """
    max_chars = max_tokens * 4
    raw_sections = re.split(r"(?=^## )", markdown, flags=re.MULTILINE)
    chunks: List[str] = []
    for section in raw_sections:
        if len(section) <= max_chars:
            chunks.append(section)
        else:
            # Split long sections on blank lines
            paragraphs = re.split(r"\n{2,}", section)
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + 2 > max_chars and current:
                    chunks.append(current.strip())
                    current = para
                else:
                    current = current + "\n\n" + para if current else para
            if current:
                chunks.append(current.strip())
    return [c for c in chunks if c.strip()]


def build_index(
    tickers: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    force: bool = False,
) -> None:
    """
    Build and persist the PropertyGraphIndex from parsed Markdown files.
    Skips the build if the graph store file already exists, unless force=True.
    """
    graph_path = Path(settings.graph_store_path)
    if graph_path.exists() and not force:
        log.info("Graph store already exists at %s. Use force=True to rebuild.", graph_path)
        return

    try:
        from llama_index.core import Document, PropertyGraphIndex, StorageContext, Settings as LISettings
        from llama_index.core.graph_stores import SimplePropertyGraphStore
        from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
        from llama_index.llms.groq import Groq
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}. Run: pip install -r requirements.txt")

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set in .env")

    tickers = tickers or settings.tickers_list
    years = years or settings.years_list

    # Configure LlamaIndex global settings
    # Use larger chunks + low concurrency to stay under Groq free-tier TPM limits
    llm = Groq(model=settings.groq_model, api_key=settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model
    LISettings.chunk_size = 1500  # bigger chunks = fewer LLM calls
    LISettings.chunk_overlap = 100

    # Path extractor with single worker to avoid rate limits
    kg_extractor = SimpleLLMPathExtractor(
        llm=llm,
        max_paths_per_chunk=10,
        num_workers=1,
    )

    # Storage
    graph_store = SimplePropertyGraphStore()
    chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)
    chroma_collection = chroma_client.get_or_create_collection("sec_filings")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(
        graph_store=graph_store,
        vector_store=vector_store,
    )

    # Load documents from cached Markdown
    documents: List[Document] = []
    parsed = list_parsed()
    for ticker in tickers:
        for year in years:
            if year not in parsed.get(ticker, []):
                log.warning("No parsed Markdown for %s %d — skipping.", ticker, year)
                continue
            markdown = get_parsed_markdown(ticker, year)
            if not markdown:
                continue
            sections = _split_by_sections(markdown)
            log.info("  %s %d → %d sections", ticker, year, len(sections))
            for i, section_text in enumerate(sections):
                documents.append(
                    Document(
                        text=section_text,
                        metadata={
                            "ticker": ticker,
                            "year": year,
                            "filing_type": "10-K",
                            "section_index": i,
                        },
                        excluded_llm_metadata_keys=["section_index"],
                    )
                )

    if not documents:
        raise RuntimeError("No documents to index. Run parse_filings first.")

    log.info("Building PropertyGraphIndex from %d document chunks…", len(documents))
    index = PropertyGraphIndex.from_documents(
        documents,
        storage_context=storage_context,
        kg_extractors=[kg_extractor],
        show_progress=True,
    )

    # Persist graph store
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_store.persist(persist_path=str(graph_path))
    log.info("Graph store persisted → %s", graph_path)

    # Add YEAR_OVER_YEAR edges across FinancialMetric nodes
    _add_year_over_year_edges(graph_store, tickers)

    # Re-persist with the new edges
    graph_store.persist(persist_path=str(graph_path))
    log.info("Graph store updated with YEAR_OVER_YEAR edges.")


def _add_year_over_year_edges(graph_store, tickers: List[str]) -> None:
    """
    Post-process the graph to add YEAR_OVER_YEAR directed edges between
    FinancialMetric nodes representing the same metric in consecutive years.
    """
    try:
        from llama_index.core.graph_stores.types import EntityNode, Relation
    except ImportError:
        log.warning("Cannot add YEAR_OVER_YEAR edges: LlamaIndex types unavailable.")
        return

    # Collect all nodes from the graph store (networkx backend)
    try:
        nx_graph = graph_store.graph
    except AttributeError:
        log.warning("Graph store does not expose .graph — skipping YEAR_OVER_YEAR edges.")
        return

    # Find pairs of FinancialMetric nodes with same label across different years
    metric_nodes: Dict[str, List] = {}  # key: (ticker, metric_name) → sorted by year
    for node_id, data in nx_graph.nodes(data=True):
        node_type = data.get("type", "")
        if "metric" in node_type.lower() or "financial" in node_type.lower():
            ticker = data.get("ticker", "")
            metric_name = data.get("name", data.get("label", node_id))
            year = data.get("year", 0)
            key = f"{ticker}::{metric_name}"
            metric_nodes.setdefault(key, []).append((year, node_id))

    added = 0
    for key, node_list in metric_nodes.items():
        sorted_nodes = sorted(node_list, key=lambda x: x[0])
        for i in range(len(sorted_nodes) - 1):
            year_a, id_a = sorted_nodes[i]
            year_b, id_b = sorted_nodes[i + 1]
            if year_a and year_b and year_a < year_b:
                try:
                    nx_graph.add_edge(
                        id_a, id_b,
                        relation="YEAR_OVER_YEAR",
                        from_year=year_a,
                        to_year=year_b,
                    )
                    added += 1
                except Exception:
                    pass

    log.info("Added %d YEAR_OVER_YEAR edges.", added)


def get_index_stats() -> Dict:
    """Return basic stats about the persisted graph (node/edge counts)."""
    graph_path = Path(settings.graph_store_path)
    if not graph_path.exists():
        return {"status": "not_built", "nodes": 0, "edges": 0}

    try:
        from llama_index.core.graph_stores import SimplePropertyGraphStore
        gs = SimplePropertyGraphStore.from_persist_path(str(graph_path))
        nx_graph = gs.graph
        return {
            "status": "ready",
            "nodes": nx_graph.number_of_nodes(),
            "edges": nx_graph.number_of_edges(),
            "graph_path": str(graph_path),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "nodes": 0, "edges": 0}
