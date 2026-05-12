"""
Phase 4 — Query engine.

Loads the persisted graph store + ChromaDB and exposes a query() function
used by all API endpoints. The engine is initialised once at startup and
reused across requests (module-level singleton).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

log = logging.getLogger(__name__)


@dataclass
class QueryResult:
    answer: str
    source_nodes: List[Dict[str, Any]] = field(default_factory=list)
    graph_path: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    mode: str = "graph"
    structured: Optional[Dict[str, Any]] = None


# Module-level singleton — populated by initialise()
_query_engine = None
_index = None
_is_ready = False


def initialise(force: bool = False) -> bool:
    """
    Load the persisted PropertyGraphIndex from disk.
    If the graph store doesn't exist, fall back to the structured-chunk
    index (still benefits from LlamaParse's structure preservation, just
    without entity-graph traversal).
    """
    global _query_engine, _index, _is_ready

    if _is_ready and not force:
        return True

    graph_path = Path(settings.graph_store_path)
    if not graph_path.exists():
        log.info(
            "Graph store not found — using structured-chunk index as fallback. "
            "(Build the graph index later with scripts/build_index.py --graph-only)"
        )
        return _initialise_structured_fallback()

    try:
        from llama_index.core import PropertyGraphIndex, StorageContext, Settings as LISettings
        from llama_index.core.graph_stores import SimplePropertyGraphStore
        from llama_index.llms.groq import Groq
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
    except ImportError as e:
        log.error("Missing dependency: %s", e)
        return False

    log.info("Loading PropertyGraphIndex from %s…", graph_path)

    llm = Groq(model=settings.groq_model, api_key=settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    graph_store = SimplePropertyGraphStore.from_persist_path(str(graph_path))
    chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)
    chroma_collection = chroma_client.get_or_create_collection("sec_filings")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(
        graph_store=graph_store,
        vector_store=vector_store,
    )

    _index = PropertyGraphIndex.from_existing(storage_context=storage_context)
    _query_engine = _index.as_query_engine(
        include_text=True,
        response_mode="tree_summarize",
    )
    _is_ready = True
    log.info("Query engine ready.")
    return True


def is_ready() -> bool:
    return _is_ready


def _initialise_structured_fallback() -> bool:
    """Use the structured-chunk ChromaDB index when no graph exists."""
    global _query_engine, _index, _is_ready
    try:
        import chromadb
        from llama_index.core import VectorStoreIndex, StorageContext, Settings as LISettings
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        from llama_index.llms.groq import Groq
        from llama_index.vector_stores.chroma import ChromaVectorStore
    except ImportError as e:
        log.error("Missing dependency: %s", e)
        return False

    # Check collection exists BEFORE downloading the ONNX embedding model.
    # On a fresh deploy (no persistent ChromaDB), failing early avoids a
    # 90-second model download that blocks uvicorn's event loop and causes
    # Render health checks to time out.
    chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)
    try:
        collection = chroma_client.get_collection("structured_chunks")
    except Exception:
        log.warning("structured_chunks collection not found — run build_index.py --naive-only")
        _is_ready = False
        return False

    llm = Groq(model=settings.groq_model, api_key=settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    _index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    _query_engine = _index.as_query_engine(similarity_top_k=5)
    _is_ready = True
    log.info("Query engine ready (structured-chunk fallback mode).")
    return True


def query(question: str, mode: str = "graph") -> QueryResult:
    """
    Route the live API to the SAME pipelines used in the benchmark:
      mode='graph' → query_structured() (HyDE + hybrid + RRF + reranker + decomposition)
      mode='naive' → query_naive() (fixed-size chunks + vector search baseline)
    """
    if mode == "naive":
        return _naive_query_via_benchmark(question)

    # mode == "graph": use the production pipeline from structured_chunker
    t0 = time.perf_counter()
    structured: Optional[Dict[str, Any]] = None
    try:
        from app.benchmarks.structured_chunker import (
            query_structured,
            query_structured_json,
            query_structured_trend,
        )
        from app.rag_utils import (
            decompose_trend_question,
            extract_filters_from_question,
        )

        filters = extract_filters_from_question(question)
        is_trend = decompose_trend_question(question) is not None
        looks_numeric = (
            len(filters.get("years", [])) == 1
            and any(kw in question.lower() for kw in (
                "expense", "revenue", "income", "margin", "sales", "profit",
                "cost", "asset", "liability", "cash", "earning", "tax",
                "what was", "how much", "what is",
            ))
        )

        if is_trend:
            answer, raw_nodes, series = query_structured_trend(question)
            if series:
                structured = {
                    "kind": "trend",
                    "metric": _guess_metric(question),
                    "ticker": (filters.get("tickers") or [None])[0],
                    "unit": series[0].get("unit", "") if series else "",
                    "series": series,
                    "confidence": min(1.0, len(series) / max(len(filters.get("years", [])) or len(series), 1)),
                }
        elif looks_numeric:
            answer, raw_nodes, parsed = query_structured_json(question)
            structured = {
                "kind": "value" if parsed.get("value") is not None else "qualitative",
                "value": parsed.get("value"),
                "unit": parsed.get("unit"),
                "year": parsed.get("year"),
                "ticker": parsed.get("ticker") or (filters.get("tickers") or [None])[0],
                "metric": _guess_metric(question),
                "source": parsed.get("source"),
                "confidence": float(parsed.get("confidence", 0.0)),
                "series": [],
            }
        else:
            answer, raw_nodes = query_structured(question)
            structured = {
                "kind": "qualitative",
                "ticker": (filters.get("tickers") or [None])[0],
                "metric": _guess_metric(question),
                "confidence": 0.5,
                "series": [],
            }

        source_nodes = [
            {
                "text": (n.get("text") or "")[:300],
                "ticker": (n.get("metadata") or {}).get("ticker", ""),
                "year": (n.get("metadata") or {}).get("year", ""),
                "score": round(float(n.get("score") or 0), 4),
            }
            for n in raw_nodes
        ]
        path_pairs = []
        seen = set()
        for n in source_nodes:
            key = (n["ticker"], n["year"])
            if key not in seen and n["ticker"]:
                seen.add(key)
                path_pairs.append(f"{n['ticker']}:{n['year']}")
        graph_path = path_pairs[:5]
    except Exception as exc:
        log.error("Query failed: %s", exc)
        answer = f"Query error: {exc}"
        source_nodes = []
        graph_path = []

    latency_ms = (time.perf_counter() - t0) * 1000
    return QueryResult(
        answer=answer,
        source_nodes=source_nodes,
        graph_path=graph_path,
        latency_ms=round(latency_ms, 1),
        mode=mode,
        structured=structured,
    )


# Metric tokens we recognize in questions — shown in the Answer Card label
_METRIC_KEYWORDS = [
    ("R&D Expenses", ["research and development", "r&d", "r & d"]),
    ("Revenue", ["net sales", "revenue", "total revenue"]),
    ("Operating Expenses", ["operating expense", "opex"]),
    ("Net Income", ["net income", "net earnings", "net profit"]),
    ("Gross Margin", ["gross margin", "gross profit"]),
    ("Cost of Revenue", ["cost of revenue", "cost of sales", "cogs"]),
    ("Cash & Equivalents", ["cash", "cash equivalents"]),
    ("Total Assets", ["total assets"]),
    ("Operating Income", ["operating income"]),
    ("Cloud Revenue", ["intelligent cloud", "cloud services", "cloud revenue"]),
    ("Segment Revenue", ["americas", "europe", "greater china", "japan", "rest of asia"]),
    ("Risk Factor", ["risk factor", "risk", "supply chain", "litigation"]),
]


def _guess_metric(question: str) -> str:
    q = question.lower()
    for label, terms in _METRIC_KEYWORDS:
        if any(t in q for t in terms):
            return label
    return "Financial Metric"


def _extract_graph_path(response) -> List[str]:
    """Best-effort: collect entity names traversed during graph retrieval."""
    path: List[str] = []
    try:
        for node in response.source_nodes or []:
            meta = node.metadata or {}
            if "entity" in meta:
                path.append(meta["entity"])
            elif "ticker" in meta and "year" in meta:
                path.append(f"{meta['ticker']}:{meta['year']}")
    except Exception:
        pass
    return list(dict.fromkeys(path))  # deduplicate while preserving order


def _naive_query_via_benchmark(question: str) -> QueryResult:
    """
    Run the same naive baseline used in the benchmark — fixed-size 512-token
    chunks, top-5 vector search, no reranking. Demonstrates what 'standard RAG'
    looks like compared to the production GraphRAG path.
    """
    t0 = time.perf_counter()
    try:
        from app.benchmarks.naive_chunker import query_naive
        answer, raw_nodes = query_naive(question)
        source_nodes = [
            {
                "text": (n.get("text") or "")[:300],
                "ticker": (n.get("metadata") or {}).get("ticker", ""),
                "year": (n.get("metadata") or {}).get("year", ""),
                "score": round(float(n.get("score") or 0), 4),
            }
            for n in raw_nodes
        ]
    except Exception as exc:
        log.error("Naive query failed: %s", exc)
        answer = f"Naive query error: {exc}"
        source_nodes = []

    latency_ms = (time.perf_counter() - t0) * 1000
    return QueryResult(
        answer=answer,
        source_nodes=source_nodes,
        graph_path=[],
        latency_ms=round(latency_ms, 1),
        mode="naive",
    )
