"""
Naive chunker — baseline for the benchmark comparison.

Splits Markdown text using fixed-size character windows with overlap,
blind to table or section boundaries. This intentionally mirrors what
a standard RAG pipeline does when no structure-aware parsing is applied.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.pipeline.llama_parser import get_parsed_markdown, list_parsed

log = logging.getLogger(__name__)

CHUNK_SIZE = 512    # tokens (approximated as chars / 4)
CHUNK_OVERLAP = 50  # tokens


def _split_fixed(text: str, chunk_chars: int = CHUNK_SIZE * 4, overlap_chars: int = CHUNK_OVERLAP * 4) -> List[str]:
    """Simple sliding-window split on character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunks.append(text[start:end])
        start = end - overlap_chars
    return [c for c in chunks if c.strip()]


def build_naive_index(
    tickers: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    force: bool = False,
) -> int:
    """
    Build the naive Pinecone index (namespace "naive").
    Returns the total number of chunks indexed.
    """
    try:
        from pinecone import Pinecone, ServerlessSpec
        from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings as LISettings
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    tickers = tickers or settings.tickers_list
    years = years or settings.years_list

    from app.rag_utils import build_throttled_groq
    llm = build_throttled_groq(settings.groq_model, settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = {idx.name for idx in pc.list_indexes()}
    if settings.pinecone_index_name not in existing:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    pinecone_index = pc.Index(settings.pinecone_index_name)

    if force:
        try:
            pinecone_index.delete(delete_all=True, namespace="naive")
        except Exception:
            pass

    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace="naive",
        text_key="text",
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents: List[Document] = []
    parsed = list_parsed()

    for ticker in tickers:
        for year in years:
            if year not in parsed.get(ticker, []):
                continue
            markdown = get_parsed_markdown(ticker, year)
            if not markdown:
                continue
            chunks = _split_fixed(markdown)
            for i, chunk in enumerate(chunks):
                documents.append(
                    Document(
                        text=chunk,
                        metadata={"ticker": ticker, "year": year, "chunk_index": i, "method": "naive"},
                    )
                )

    if not documents:
        log.warning("No documents found for naive index — run parse_filings first.")
        return 0

    log.info("Indexing %d naive chunks…", len(documents))
    VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)
    log.info("Naive index built (%d chunks).", len(documents))
    return len(documents)


def query_naive(question: str, top_k: int = 5) -> Tuple[str, List[Dict]]:
    """
    Run a question against the naive index. Returns (answer_text, source_nodes).
    Used by the benchmark evaluator — not the main API path.
    """
    try:
        from pinecone import Pinecone
        from llama_index.core import VectorStoreIndex, StorageContext, Settings as LISettings
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    from app.rag_utils import build_throttled_groq
    llm = build_throttled_groq(settings.groq_model, settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    pc = Pinecone(api_key=settings.pinecone_api_key)
    pinecone_index = pc.Index(settings.pinecone_index_name)
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace="naive",
        text_key="text",
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    engine = index.as_query_engine(similarity_top_k=top_k)

    response = engine.query(question)
    nodes = [
        {"text": n.text, "metadata": n.metadata, "score": float(n.score or 0)}
        for n in (response.source_nodes or [])
    ]
    return str(response), nodes
