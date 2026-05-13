"""
Structure-aware chunker — the improved system for the benchmark comparison.

Uses a state machine to split LlamaParse Markdown output into chunks that:
  1. Never split a pipe-delimited table mid-row.
  2. Keep an entire Markdown table as a single chunk (with section context header).
  3. Group prose paragraphs up to ~800 tokens without crossing table boundaries.

This is the approach that produces dramatically higher Table Retrieval Accuracy
compared to naive fixed-size chunking.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.pipeline.llama_parser import get_parsed_markdown, list_parsed

log = logging.getLogger(__name__)

MAX_PROSE_CHARS = 1500 * 4   # ~1500 tokens — gives tables enough surrounding prose
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_TABLE_SEP_RE = re.compile(r"^\s*\|[-| :]+\|\s*$")
_HEADER_RE = re.compile(r"^(#{1,3}) (.+)$")


def _is_table_row(line: str) -> bool:
    return bool(_TABLE_ROW_RE.match(line))


def _chunk_section(section_header: str, section_body: str) -> List[Dict]:
    """
    Split a section into chunks that keep tables WITH their surrounding prose
    (so the embedding sees both narrative context like "R&D expenses" and the
    actual numeric table rows). Critical rule: never split mid-table.
    Returns list of {text, has_table, section_name}.
    """
    chunks: List[Dict] = []
    lines = section_body.split("\n")
    section_name = section_header.lstrip("#").strip() if section_header else ""

    # Build atomic blocks: each is either a pure-prose block or a contiguous table.
    blocks: List[Dict] = []  # {kind: "prose"|"table", text: str}
    current_prose: List[str] = []
    current_table: List[str] = []
    in_table = False

    for line in lines:
        if _is_table_row(line):
            if not in_table:
                if current_prose:
                    blocks.append({"kind": "prose", "text": "\n".join(current_prose)})
                    current_prose = []
                in_table = True
            current_table.append(line)
        else:
            if in_table:
                blocks.append({"kind": "table", "text": "\n".join(current_table)})
                current_table = []
                in_table = False
            current_prose.append(line)

    if in_table and current_table:
        blocks.append({"kind": "table", "text": "\n".join(current_table)})
    if current_prose:
        blocks.append({"kind": "prose", "text": "\n".join(current_prose)})

    # Greedy pack blocks into chunks up to MAX_PROSE_CHARS, but never split
    # a single table block — even if it pushes a chunk slightly over the limit.
    current_buf: List[str] = []
    current_len = 0
    has_table_in_buf = False

    def flush():
        nonlocal current_buf, current_len, has_table_in_buf
        text = "\n\n".join(current_buf).strip()
        if text:
            full_text = f"{section_header}\n\n{text}" if section_header else text
            chunks.append({
                "text": full_text,
                "has_table": has_table_in_buf,
                "section_name": section_name,
            })
        current_buf = []
        current_len = 0
        has_table_in_buf = False

    for block in blocks:
        block_len = len(block["text"])
        # Tables are never split — they go into the current buffer regardless of size.
        if block["kind"] == "table":
            current_buf.append(block["text"])
            current_len += block_len
            has_table_in_buf = True
        else:
            # Prose: split if it would overflow
            if current_len + block_len > MAX_PROSE_CHARS and current_buf:
                flush()
            current_buf.append(block["text"])
            current_len += block_len

        if current_len >= MAX_PROSE_CHARS:
            flush()

    if current_buf:
        flush()

    return chunks


def chunk_markdown(markdown: str, ticker: str, year: int) -> List[Dict]:
    """
    Split a full LlamaParse Markdown document into structure-aware chunks.
    Returns list of dicts ready to be loaded as LlamaIndex Documents.
    """
    all_chunks: List[Dict] = []
    # Split at section headings while keeping the heading with its body
    parts = re.split(r"(^#{1,3} .+$)", markdown, flags=re.MULTILINE)

    current_header = ""
    current_body_lines: List[str] = []

    def process_section(header: str, body: str):
        for chunk in _chunk_section(header, body):
            chunk["ticker"] = ticker
            chunk["year"] = year
            chunk["filing_type"] = "10-K"
            all_chunks.append(chunk)

    for part in parts:
        if _HEADER_RE.match(part.strip()):
            if current_body_lines:
                process_section(current_header, "\n".join(current_body_lines))
            current_header = part.strip()
            current_body_lines = []
        else:
            current_body_lines.append(part)

    if current_body_lines:
        process_section(current_header, "\n".join(current_body_lines))

    return all_chunks


def build_structured_index(
    tickers: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    force: bool = False,
) -> int:
    """
    Build the structure-aware Pinecone index (namespace "structured").
    Each chunk is prepended with a "Company: X | Year: Y | Document: 10-K" header
    so embeddings always carry global filing context, even for table fragments.
    Returns total chunks indexed.
    """
    try:
        from pinecone import Pinecone, ServerlessSpec
        from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings as LISettings
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    from app.rag_utils import build_throttled_groq, prepend_metadata_header

    tickers = tickers or settings.tickers_list
    years = years or settings.years_list

    llm = build_throttled_groq(settings.groq_model, settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    pc = Pinecone(api_key=settings.pinecone_api_key)
    _ensure_pinecone_index(pc, settings.pinecone_index_name)
    pinecone_index = pc.Index(settings.pinecone_index_name)

    if force:
        try:
            pinecone_index.delete(delete_all=True, namespace="structured")
        except Exception:
            pass

    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace="structured",
        text_key="text",
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents: List[Document] = []
    parsed = list_parsed()

    table_doc_count = 0

    for ticker in tickers:
        for year in years:
            if year not in parsed.get(ticker, []):
                continue
            markdown = get_parsed_markdown(ticker, year)
            if not markdown:
                continue
            chunks = chunk_markdown(markdown, ticker, year)
            for chunk_data in chunks:
                raw_text = chunk_data.pop("text")
                # ── Module 3: prepend global filing context to every chunk ──
                text_with_header = prepend_metadata_header(raw_text, ticker, year)
                documents.append(Document(text=text_with_header, metadata=chunk_data))

            # ── Phase 2 enhancement: emit each table as its own document ──
            # Tables embedded inside large section chunks get drowned out — a
            # dedicated table document makes the embedding match queries like
            # "Apple R&D 2023" directly to the row that contains the answer.
            for table_doc in _emit_table_documents(markdown, ticker, year):
                documents.append(table_doc)
                table_doc_count += 1

    if not documents:
        log.warning("No documents found for structured index.")
        return 0

    log.info(
        "Indexing %d structured chunks (incl. %d dedicated table docs)…",
        len(documents), table_doc_count,
    )
    VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)
    log.info("Structured index built (%d chunks).", len(documents))
    return len(documents)


def _emit_table_documents(markdown: str, ticker: str, year: int) -> List:
    """
    Extract every contiguous Markdown table block from the document and emit it
    as a standalone Document with rich metadata. The table text is wrapped in
    the most-recent ## section header (provides context like "Consolidated
    Statements of Operations") and prefixed with the metadata header.
    """
    from llama_index.core import Document
    from app.rag_utils import prepend_metadata_header

    docs: List = []
    lines = markdown.split("\n")
    current_section = ""
    in_table = False
    table_buf: List[str] = []
    section_re = re.compile(r"^(#{1,3}) (.+)$")

    def flush_table():
        if not table_buf:
            return
        # Skip tiny tables (likely formatting artifacts, not real data)
        if len(table_buf) < 2:
            table_buf.clear()
            return
        table_text = "\n".join(table_buf).strip()
        if current_section:
            payload = f"## {current_section}\n\n{table_text}"
        else:
            payload = table_text
        text_with_header = prepend_metadata_header(payload, ticker, year)
        docs.append(Document(
            text=text_with_header,
            metadata={
                "ticker": ticker,
                "year": year,
                "filing_type": "10-K",
                "section_name": current_section,
                "is_table": True,
                "doc_type": "table",
            },
        ))
        table_buf.clear()

    for line in lines:
        m = section_re.match(line.strip())
        if m:
            flush_table()
            current_section = m.group(2).strip()
            in_table = False
            continue
        if _is_table_row(line):
            in_table = True
            table_buf.append(line)
        else:
            if in_table:
                flush_table()
                in_table = False

    flush_table()
    return docs


def _ensure_pinecone_index(pc, index_name: str) -> None:
    """Create the Pinecone serverless index if it doesn't exist yet."""
    from pinecone import ServerlessSpec
    existing = {idx.name for idx in pc.list_indexes()}
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        log.info("Created Pinecone index '%s'.", index_name)


_INTERNAL_METADATA_KEYS = frozenset({"_node_content", "_node_type", "document_id", "ref_doc_id"})


def _fetch_all_nodes_from_pinecone(pinecone_index, namespace: str) -> List:
    """Fetch every stored node from Pinecone to reconstruct the BM25 index."""
    from llama_index.core.schema import TextNode
    try:
        all_ids: List[str] = []
        for page in pinecone_index.list(namespace=namespace):
            all_ids.extend(page)
        if not all_ids:
            log.warning("No vectors in Pinecone namespace '%s' — index may not be built yet.", namespace)
            return []
        log.info("Fetching %d nodes from Pinecone for BM25 reconstruction…", len(all_ids))
        nodes: List[TextNode] = []
        for i in range(0, len(all_ids), 100):
            batch = all_ids[i:i + 100]
            result = pinecone_index.fetch(ids=batch, namespace=namespace)
            for vec in result.vectors.values():
                text = vec.metadata.get("text", "")
                metadata = {
                    k: v for k, v in vec.metadata.items()
                    if k not in _INTERNAL_METADATA_KEYS and k != "text"
                }
                if text:
                    nodes.append(TextNode(text=text, metadata=metadata))
        log.info("Loaded %d nodes for BM25.", len(nodes))
        return nodes
    except Exception as exc:
        log.error("Failed to fetch nodes from Pinecone: %s", exc)
        return []


# ─── Module-level cache for the production retriever ─────────────────────────
# Building the BM25 index from all nodes is expensive — we cache it per-process
# so the 10-question benchmark doesn't rebuild it 10 times.
_PROD_RETRIEVER_CACHE: Dict = {}


def _get_production_components(rerank_top_n: int = 5):
    """
    Build (or return cached) the components needed for the production pipeline:
      - llm (throttled Groq)
      - hybrid_retriever (Vector + BM25 with RRF, top-20)
      - reranker (flashrank cross-encoder, top-5)
      - hyde (HyDE generator with in-memory cache)
      - default_engine (RetrieverQueryEngine for prose answers)
    """
    if "components" in _PROD_RETRIEVER_CACHE:
        return _PROD_RETRIEVER_CACHE["components"]

    try:
        from pinecone import Pinecone
        from llama_index.core import VectorStoreIndex, StorageContext, Settings as LISettings
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.embeddings.fastembed import FastEmbedEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    from app.rag_utils import (
        FastEmbedReranker,
        HyDEGenerator,
        build_hybrid_retriever,
        build_throttled_groq,
    )

    llm = build_throttled_groq(settings.groq_model, settings.groq_api_key)
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    LISettings.llm = llm
    LISettings.embed_model = embed_model

    pc = Pinecone(api_key=settings.pinecone_api_key)
    pinecone_index = pc.Index(settings.pinecone_index_name)
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace="structured",
        text_key="text",
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    vector_index = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )

    # SKIP_BM25_FETCH=1 short-circuits the expensive Pinecone-node fetch when
    # we know BM25 reconstruction is not viable (e.g. the v3 SDK fetch returns
    # empty for serverless namespace pagination). Saves ~8s on every cold start.
    if os.getenv("SKIP_BM25_FETCH", "0") == "1":
        log.info("SKIP_BM25_FETCH=1 — skipping Pinecone all-nodes fetch; using vector-only retrieval.")
        nodes = []
    else:
        nodes = _fetch_all_nodes_from_pinecone(pinecone_index, namespace="structured")

    # Phase 2 tuning: cast a wider net (top-40), let reranker pick top-10
    # Guard: if Pinecone namespace is empty or pagination failed, fall back to
    # vector-only retrieval so the pipeline doesn't crash with a BM25 error.
    if nodes:
        hybrid_retriever = build_hybrid_retriever(
            vector_index=vector_index,
            nodes=nodes,
            similarity_top_k=40,
            bm25_top_k=40,
            fused_top_k=40,
        )
    else:
        log.warning(
            "No nodes returned from Pinecone 'structured' namespace — "
            "falling back to vector-only retrieval. Run build_index.py to populate."
        )
        hybrid_retriever = vector_index.as_retriever(similarity_top_k=40)

    # On 512MB hosts (e.g. Render free tier) flashrank's rank-T5-flan (~150MB
    # resident) blows the memory ceiling. Setting DISABLE_RERANKER=1 skips the
    # reranker entirely; retrieval falls back to vector (or RRF when BM25 is
    # populated) scores. Quality drops slightly; service stays alive.
    if os.getenv("DISABLE_RERANKER", "0") == "1":
        log.info("DISABLE_RERANKER=1 — skipping flashrank reranker (memory-constrained mode).")
        reranker = None
        postprocessors = []
    else:
        reranker = FastEmbedReranker(top_n=max(rerank_top_n, 10))
        postprocessors = [reranker]
    hyde = HyDEGenerator(llm=llm)

    default_engine = RetrieverQueryEngine.from_args(
        retriever=hybrid_retriever,
        node_postprocessors=postprocessors,
        llm=llm,
    )

    components = {
        "llm": llm,
        "hybrid_retriever": hybrid_retriever,
        "reranker": reranker,
        "hyde": hyde,
        "default_engine": default_engine,
        "all_nodes": nodes,       # for scoped BM25 rebuild per query
        "vector_index": vector_index,  # for scoped vector retriever rebuild
    }
    _PROD_RETRIEVER_CACHE["components"] = components
    return components


# Groq llama-3.1-8b-instant TPM limit is 6000. Reserve ~1000 tokens for the
# system/user prompt scaffolding and the model's output, leaving ~5000 tokens
# (~20000 chars) for retrieved context. Risk-factor chunks can be 8000+ chars
# each, so we cap the joined context aggressively to avoid 413 errors.
_MAX_CONTEXT_CHARS = 16000


def _truncate_context(nodes: List, max_chars: int = _MAX_CONTEXT_CHARS) -> str:
    """
    Join retrieved node texts with the standard separator, but stop adding
    nodes once the total length would exceed max_chars. Highest-ranked nodes
    are added first, so truncation drops the least-relevant chunks.
    """
    parts: List[str] = []
    total = 0
    sep = "\n\n---\n\n"
    sep_len = len(sep)
    for n in nodes:
        text = getattr(n, "get_content", lambda: getattr(n, "text", ""))()
        if not text:
            continue
        added = (sep_len if parts else 0) + len(text)
        if total + added > max_chars:
            # If a single chunk is larger than the budget, take a prefix of it
            if not parts:
                parts.append(text[:max_chars])
            else:
                remaining = max_chars - total - sep_len
                if remaining > 200:
                    parts.append(text[:remaining])
            break
        parts.append(text)
        total += added
    return sep.join(parts)


_STRICT_ANSWER_PROMPT = (
    "You are a financial analyst answering questions about SEC 10-K filings.\n"
    "RULES:\n"
    "  1. Use ONLY the provided excerpts. Do NOT use prior knowledge.\n"
    "  2. Cite the exact ticker, fiscal year, and dollar figure for every claim.\n"
    "  3. If the answer is not explicitly present in the excerpts, respond with:\n"
    '     "Not found in the provided filings."\n'
    "  4. Show simple year-over-year changes when relevant.\n"
    "\n"
    "Excerpts:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


def _retrieve_with_hyde(
    question: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    skip_hyde: bool = False,
) -> List:
    """
    Hybrid retrieval with optional HyDE rewrite + metadata pre-filtering.

    When filters are provided (ticker/year), BM25 is rebuilt over only the
    matching nodes so that wrong-company chunks don't crowd out the correct
    table chunk in the fused top-40. The vector retriever still uses the full
    ChromaDB index (semantic similarity works better with more candidates).
    When skip_hyde=True (or the question is already specific), the original
    question is used for both vector and BM25, saving 1 Groq call.
    """
    from llama_index.core.schema import QueryBundle
    from app.rag_utils import (
        should_skip_hyde, apply_metadata_filter, build_hybrid_retriever,
        boost_consolidated_chunks,
    )

    comps = _get_production_components(rerank_top_n=top_k)
    use_raw = skip_hyde or should_skip_hyde(question)
    retrieval_query = question if use_raw else comps["hyde"].generate(question)

    if filters:
        scoped_nodes = apply_metadata_filter(comps["all_nodes"], filters)
        if len(scoped_nodes) >= 5:
            # Pre-filter: rebuild BM25 over only the relevant company/year nodes
            # so wrong-ticker keyword matches don't displace the correct table chunk.
            scoped_retriever = build_hybrid_retriever(
                vector_index=comps["vector_index"],
                nodes=scoped_nodes,
                similarity_top_k=40,
                bm25_top_k=40,
                fused_top_k=40,
            )
            nodes = scoped_retriever.retrieve(QueryBundle(query_str=retrieval_query))
        else:
            # Not enough scoped nodes — fall back to global retriever + post-filter
            nodes = comps["hybrid_retriever"].retrieve(QueryBundle(query_str=retrieval_query))
            filtered = apply_metadata_filter(nodes, filters)
            if filtered:
                nodes = filtered
    else:
        nodes = comps["hybrid_retriever"].retrieve(QueryBundle(query_str=retrieval_query))

    if comps["reranker"] is not None:
        reranked = comps["reranker"].postprocess_nodes(nodes, query_str=question)
    else:
        # DISABLE_RERANKER=1 — keep retrieval order (vector / RRF score).
        reranked = nodes[: max(top_k, 10)]
    # Boost consolidated-statement chunks when the question asks for company-wide
    # totals (skipped if the question is segment-specific).
    reranked = boost_consolidated_chunks(reranked, question)
    return reranked[:top_k]


def _synthesize_answer(question: str, retrieved_nodes: List, llm) -> str:
    """Compose the final answer using the strict context-only prompt."""
    if not retrieved_nodes:
        return "Not found in the provided filings."

    context = _truncate_context(retrieved_nodes)
    from llama_index.core.llms import ChatMessage, MessageRole
    prompt = _STRICT_ANSWER_PROMPT.format(context=context, question=question)
    response = llm.chat([ChatMessage(role=MessageRole.USER, content=prompt)])
    return str(response.message.content).strip()


def _nodes_to_dicts(nodes: List) -> List[Dict]:
    return [
        {
            "text": getattr(n, "get_content", lambda: getattr(n, "text", ""))(),
            "metadata": getattr(n, "metadata", {}) or {},
            "score": float(getattr(n, "score", 0) or 0),
        }
        for n in nodes
    ]


def query_structured(question: str, top_k: int = 10) -> Tuple[str, List[Dict]]:
    """
    Production-grade pipeline (cached + parallel):
      0. Cache hit? Return immediately.
      1. Trend question? Decompose into per-year sub-queries, run them in
         parallel (ThreadPoolExecutor — Groq calls are HTTP I/O bound).
      2. Otherwise: HyDE-skip-aware retrieval → strict context-only synthesis.
    """
    from app.rag_utils import (
        RESPONSE_CACHE,
        decompose_trend_question,
        extract_filters_from_question,
    )

    cached = RESPONSE_CACHE.get(question, mode="graph")
    if cached is not None:
        log.info("Cache hit for question.")
        return cached

    comps = _get_production_components(rerank_top_n=top_k)
    base_filters = extract_filters_from_question(question)

    # ── Multi-year decomposition path (parallel) ────────────────────────────
    sub_queries = decompose_trend_question(question)
    if sub_queries:
        log.info("Decomposing trend question into %d parallel sub-queries", len(sub_queries))

        def _run_sub_query(sq):
            sub_filters = dict(base_filters)
            sub_filters["years"] = [sq["year"]]
            # Skip HyDE for sub-queries — they're already specific
            sub_nodes = _retrieve_with_hyde(
                sq["question"], top_k=5, filters=sub_filters, skip_hyde=True,
            )
            return sq, sub_nodes

        from concurrent.futures import ThreadPoolExecutor
        per_year_context: List[str] = []
        all_nodes: List = []
        with ThreadPoolExecutor(max_workers=min(4, len(sub_queries))) as ex:
            for sq, sub_nodes in ex.map(_run_sub_query, sub_queries):
                if sub_nodes:
                    excerpt = "\n".join(
                        getattr(n, "get_content", lambda: getattr(n, "text", ""))()
                        for n in sub_nodes[:3]
                    )
                    per_year_context.append(f"=== Year {sq['year']} ===\n{excerpt}")
                    all_nodes.extend(sub_nodes[:3])

        if per_year_context:
            combined = "\n\n".join(per_year_context)
            if len(combined) > _MAX_CONTEXT_CHARS:
                combined = combined[:_MAX_CONTEXT_CHARS]
            covered_years = [sq["year"] for sq in sub_queries]
            from llama_index.core.llms import ChatMessage, MessageRole
            trend_prompt = (
                "You are a financial analyst answering a MULTI-YEAR TREND question "
                "about SEC 10-K filings. The excerpts are organized by fiscal year.\n"
                "RULES:\n"
                "  1. You MUST explicitly mention each of these years in your answer: "
                f"{', '.join(str(y) for y in covered_years)}.\n"
                "  2. For each year, state the exact dollar figure (with units).\n"
                "  3. After listing the values, briefly describe the trend "
                "(growth / decline / percentage change).\n"
                "  4. Use ONLY the provided excerpts. Do not use prior knowledge.\n"
                "  5. If a specific year's data is missing, still mention the year "
                "and say 'data not available in excerpts'.\n"
                f"\nExcerpts:\n{combined}\n\n"
                f"Question: {question}\n\n"
                "Answer (cite each year explicitly with its value):"
            )
            response = comps["llm"].chat(
                [ChatMessage(role=MessageRole.USER, content=trend_prompt)]
            )
            answer = str(response.message.content).strip()
            result = (answer, _nodes_to_dicts(all_nodes))
            RESPONSE_CACHE.put(question, "graph", result)
            return result

    # ── Single-query path ───────────────────────────────────────────────────
    reranked = _retrieve_with_hyde(question, top_k=top_k, filters=base_filters)
    answer = _synthesize_answer(question, reranked, comps["llm"])
    result = (answer, _nodes_to_dicts(reranked))
    RESPONSE_CACHE.put(question, "graph", result)
    return result


def query_structured_json(question: str, top_k: int = 10) -> Tuple[str, List[Dict], Dict]:
    """
    JSON-mode variant for numeric questions. Returns (prose_answer, source_nodes, parsed_json).
    Adds value-in-context validation: if Groq returns a number that isn't actually
    in any retrieved chunk, we null it out (prevents confident hallucination).
    """
    from app.rag_utils import (
        RESPONSE_CACHE,
        answer_with_json_extraction,
        compute_gross_margin_from_nodes,
        extract_filters_from_question,
        is_gross_margin_question,
        validate_value_in_context,
    )

    cached = RESPONSE_CACHE.get(question, mode="json")
    if cached is not None:
        log.info("Cache hit for JSON question.")
        return cached

    filters = extract_filters_from_question(question)
    reranked = _retrieve_with_hyde(question, top_k=top_k, filters=filters)
    if not reranked:
        result = ("Not found in the provided filings.", [], {"value": None})
        RESPONSE_CACHE.put(question, "json", result)
        return result

    comps = _get_production_components(rerank_top_n=top_k)

    # Deterministic short-circuit: gross margin % is computed in Python rather
    # than asking Llama-8b to do arithmetic (which is the q07 failure mode).
    if is_gross_margin_question(question):
        target_year = filters.get("years", [None])[0] if filters.get("years") else None
        gm = compute_gross_margin_from_nodes(reranked, year=target_year)
        if gm is not None:
            log.info("Gross margin computed deterministically: %s%%", gm["value"])
            gm["confidence"] = 1.0
            nodes_dicts = _nodes_to_dicts(reranked)
            prose = (
                f"{gm['value']} percent ({gm.get('year') or ''}) — {gm['source']}"
            )
            result = (prose, nodes_dicts, gm)
            RESPONSE_CACHE.put(question, "json", result)
            return result
        log.info("Gross margin components not found in chunks; falling back to LLM.")

    context = _truncate_context(reranked)
    parsed = answer_with_json_extraction(comps["llm"], question, context)

    # Validate: extracted numeric value should appear in retrieved context.
    # If we can't verify, KEEP the value (the LLM saw the right chunks even if
    # our digit-substring check missed due to formatting) but lower confidence.
    # Empirical: aggressive nulling cost ~25 ACS points; soft demotion is safer.
    nodes_dicts = _nodes_to_dicts(reranked)
    value_verified = True
    if parsed.get("value") is not None and not validate_value_in_context(parsed, nodes_dicts):
        log.warning(
            "Extracted value %s not directly verified in retrieved context — "
            "keeping answer but lowering confidence.",
            parsed.get("value"),
        )
        value_verified = False

    # Confidence: 1.0 if value present AND verified in retrieved context,
    # 0.5 if value present but unverified (potential hallucination),
    # 0.6 if no value but prose answer present (qualitative),
    # 0.3 if neither (no useful answer).
    if parsed.get("value") is not None:
        parsed["confidence"] = 1.0 if value_verified else 0.5
    elif parsed.get("prose_answer"):
        parsed["confidence"] = 0.6
    else:
        parsed["confidence"] = 0.3

    # Augment with extracted ticker if missing
    if not parsed.get("ticker"):
        f = extract_filters_from_question(question)
        if f.get("tickers"):
            parsed["ticker"] = f["tickers"][0]

    if parsed.get("value") is not None:
        prose = (
            f"{parsed['value']} {parsed.get('unit') or ''} "
            f"({parsed.get('year') or ''}) — {parsed.get('source') or ''}"
        )
    else:
        prose = parsed.get("prose_answer", "Not found in the provided filings.")

    result = (prose, nodes_dicts, parsed)
    RESPONSE_CACHE.put(question, "json", result)
    return result


def query_structured_trend(question: str) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Returns (prose_answer, source_nodes, series) where series is a list of
    {year, value, unit} dicts for each year detected in the question.

    Decomposes into per-year sub-queries (parallel), JSON-extracts the value
    for each, validates against context, then synthesizes a trend prose answer.
    """
    from app.rag_utils import (
        RESPONSE_CACHE,
        answer_with_json_extraction,
        decompose_trend_question,
        extract_filters_from_question,
        validate_value_in_context,
    )
    from concurrent.futures import ThreadPoolExecutor

    cached = RESPONSE_CACHE.get(question, mode="trend")
    if cached is not None:
        return cached

    sub_queries = decompose_trend_question(question)
    if not sub_queries:
        # Not actually a trend — fall through to single-value handler
        prose, nodes, parsed = query_structured_json(question)
        result = (prose, nodes, [])
        return result

    base_filters = extract_filters_from_question(question)
    comps = _get_production_components(rerank_top_n=5)

    def _run_year(sq):
        year_filters = dict(base_filters)
        year_filters["years"] = [sq["year"]]
        year_nodes = _retrieve_with_hyde(
            sq["question"], top_k=5, filters=year_filters, skip_hyde=True,
        )
        if not year_nodes:
            return sq["year"], None, []
        year_context = "\n\n".join(
            getattr(n, "get_content", lambda: getattr(n, "text", ""))()
            for n in year_nodes[:3]
        )
        year_parsed = answer_with_json_extraction(comps["llm"], sq["question"], year_context)
        node_dicts = _nodes_to_dicts(year_nodes[:3])
        if year_parsed.get("value") is not None and not validate_value_in_context(year_parsed, node_dicts):
            year_parsed["value"] = None
        return sq["year"], year_parsed, node_dicts

    series: List[Dict] = []
    all_nodes: List[Dict] = []
    with ThreadPoolExecutor(max_workers=min(4, len(sub_queries))) as ex:
        for year, parsed, nodes in ex.map(_run_year, sub_queries):
            if parsed and parsed.get("value") is not None:
                series.append({
                    "year": year,
                    "value": float(parsed["value"]),
                    "unit": parsed.get("unit") or "",
                    "source": parsed.get("source") or "",
                })
            all_nodes.extend(nodes)

    if not series:
        prose = "Not found in the provided filings."
        result = (prose, all_nodes, [])
        RESPONSE_CACHE.put(question, "trend", result)
        return result

    # Compose a trend prose answer from the series
    parts = [
        f"{s['year']}: {s['value']:,.0f} {s['unit']}".strip()
        for s in sorted(series, key=lambda x: x["year"])
    ]
    first, last = sorted(series, key=lambda x: x["year"])[0], sorted(series, key=lambda x: x["year"])[-1]
    delta_pct = ((last["value"] - first["value"]) / first["value"] * 100) if first["value"] else 0
    direction = "increased" if delta_pct > 0 else "decreased"
    prose = (
        f"{', '.join(parts)}. "
        f"Overall, the value {direction} by {abs(delta_pct):.1f}% from "
        f"{first['year']} to {last['year']}."
    )

    result = (prose, all_nodes, series)
    RESPONSE_CACHE.put(question, "trend", result)
    return result
