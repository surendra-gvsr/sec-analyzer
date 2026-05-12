"""
Production-grade RAG utilities.

This module exposes:
  - ThrottledGroq            — Groq LLM with proactive RPM throttle + tenacity retry
  - FastEmbedReranker        — BGE-based cross-encoder NodePostprocessor (no torch)
  - build_hybrid_retriever   — Vector + BM25 retriever fused with Reciprocal Rank Fusion
  - prepend_metadata_header  — index-time chunk prefix with Company/Year/Document context
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, List, Optional, Sequence

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)


# ─── 1. Index-time metadata prepending ───────────────────────────────────────

def prepend_metadata_header(text: str, ticker: str, year: int, filing_type: str = "10-K") -> str:
    """
    Inject global filing context into every chunk so the embedding and the LLM
    always know which company/year a fragment belongs to. Critical when the
    same financial table appears across multiple years with near-identical text.
    """
    header = f"Company: {ticker} | Year: {year} | Document: {filing_type} | Content: "
    return header + text


# ─── 2. Throttled Groq LLM ───────────────────────────────────────────────────

class _RateLimiter:
    """
    Token-bucket-ish throttle: enforces a minimum gap between LLM calls so we
    stay under Groq free-tier RPM. Thread-safe across sync and async call sites.
    """

    def __init__(self, requests_per_minute: int = 25):
        self.min_interval = 60.0 / max(requests_per_minute, 1)
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = self._last_call + self.min_interval - now
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_call = time.monotonic()


# Single shared limiter — tuned just below Groq free tier (30 RPM for chat).
# Lifted to 28 to maximize throughput while still leaving headroom.
_GROQ_LIMITER = _RateLimiter(requests_per_minute=28)


def _is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


_retry_on_rate_limit = retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),                       # was 5
    wait=wait_exponential(multiplier=1.5, min=1, max=8),  # was max=30
    reraise=True,
)


def build_throttled_groq(model: str, api_key: str):
    """
    Returns a Groq LLM (subclass) whose chat methods are wrapped with proactive
    throttle + exponential backoff retry on 429s. Failures other than 429 still
    raise. Uses subclassing because the Groq class is a Pydantic model that
    forbids attribute assignment.
    """
    from llama_index.llms.groq import Groq

    class ThrottledGroq(Groq):
        @_retry_on_rate_limit
        def chat(self, *args, **kwargs):
            _GROQ_LIMITER.wait()
            try:
                return super().chat(*args, **kwargs)
            except Exception as exc:
                if _is_rate_limit_error(exc):
                    log.warning("Groq 429 — backing off and retrying.")
                raise

        @_retry_on_rate_limit
        async def achat(self, *args, **kwargs):
            _GROQ_LIMITER.wait()
            try:
                return await super().achat(*args, **kwargs)
            except Exception as exc:
                if _is_rate_limit_error(exc):
                    log.warning("Groq 429 — backing off and retrying.")
                raise

        @_retry_on_rate_limit
        def complete(self, *args, **kwargs):
            _GROQ_LIMITER.wait()
            try:
                return super().complete(*args, **kwargs)
            except Exception as exc:
                if _is_rate_limit_error(exc):
                    log.warning("Groq 429 — backing off and retrying.")
                raise

        @_retry_on_rate_limit
        async def acomplete(self, *args, **kwargs):
            _GROQ_LIMITER.wait()
            try:
                return await super().acomplete(*args, **kwargs)
            except Exception as exc:
                if _is_rate_limit_error(exc):
                    log.warning("Groq 429 — backing off and retrying.")
                raise

    # temperature=0 makes JSON extraction deterministic across runs.
    # Empirically: Llama-3.1-8b at default temperature picks different numbers
    # from the same chunk on different runs (q05 oscillates between $75.251B
    # and $15.2B). Zero temperature locks the output for reproducible benchmarks.
    return ThrottledGroq(model=model, api_key=api_key, temperature=0.0)


# ─── 3. BGE Reranker (fastembed, no torch dependency) ────────────────────────

class FastEmbedReranker:
    """
    NodePostprocessor that re-scores retrieved nodes using a cross-encoder.
    Implements the LlamaIndex BaseNodePostprocessor protocol via duck-typing.
    Uses flashrank (ONNX-based ms-marco-MiniLM) — no torch / no sentence-transformers.
    """

    def __init__(self, model_name: str = "rank-T5-flan", top_n: int = 5):
        try:
            from flashrank import Ranker
        except ImportError as exc:
            raise RuntimeError(
                "flashrank must be installed for FastEmbedReranker. "
                "Run: pip install flashrank"
            ) from exc

        self.model = Ranker(model_name=model_name)
        self.top_n = top_n
        self.model_name = model_name

    def postprocess_nodes(
        self,
        nodes: List[Any],
        query_bundle: Optional[Any] = None,
        query_str: Optional[str] = None,
    ) -> List[Any]:
        """
        Re-score `nodes` against the query and return the top_n highest-scoring.
        Compatible with LlamaIndex retriever pipelines.
        """
        if not nodes:
            return nodes

        query_text = query_str
        if query_text is None and query_bundle is not None:
            query_text = getattr(query_bundle, "query_str", None) or str(query_bundle)
        if not query_text:
            log.warning("Reranker received empty query — returning input nodes unchanged.")
            return nodes[: self.top_n]

        from flashrank import RerankRequest

        passages = []
        for i, n in enumerate(nodes):
            text = getattr(n, "get_content", lambda: getattr(n, "text", ""))()
            passages.append({"id": i, "text": text})

        try:
            request = RerankRequest(query=query_text, passages=passages)
            results = self.model.rerank(request)
        except Exception as exc:
            log.warning("Reranker call failed (%s) — falling back to original order.", exc)
            return nodes[: self.top_n]

        # Map results back to nodes by id, attach scores
        id_to_score = {r["id"]: float(r.get("score", 0)) for r in results}
        for i, node in enumerate(nodes):
            try:
                node.score = id_to_score.get(i, 0.0)
            except Exception:
                pass

        ranked = sorted(
            nodes,
            key=lambda n: float(getattr(n, "score", 0) or 0),
            reverse=True,
        )
        return ranked[: self.top_n]


# ─── 4. Hybrid retriever (Vector + BM25 with RRF) ────────────────────────────

def build_hybrid_retriever(
    vector_index,
    nodes: Sequence[Any],
    similarity_top_k: int = 20,
    bm25_top_k: int = 20,
    fused_top_k: int = 20,
):
    """
    Build a QueryFusionRetriever that combines:
      - Vector retrieval over `vector_index` (semantic similarity)
      - BM25 retrieval over `nodes` (keyword match — catches "2024", "Amortization")
    using Reciprocal Rank Fusion. The fused top-k is what the reranker sees next.
    """
    try:
        from llama_index.core.retrievers import QueryFusionRetriever
        from llama_index.retrievers.bm25 import BM25Retriever
    except ImportError as exc:
        raise RuntimeError(
            "llama-index-retrievers-bm25 must be installed. "
            "Run: pip install llama-index-retrievers-bm25"
        ) from exc

    vector_retriever = vector_index.as_retriever(similarity_top_k=similarity_top_k)
    bm25_retriever = BM25Retriever.from_defaults(
        nodes=list(nodes),
        similarity_top_k=bm25_top_k,
    )

    fusion = QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        similarity_top_k=fused_top_k,
        num_queries=1,            # disable query rewrites (would burn LLM tokens)
        mode="reciprocal_rerank", # RRF
        use_async=False,
        verbose=False,
    )
    return fusion


# ─── 5. HyDE (Hypothetical Document Embeddings) ──────────────────────────────

class HyDEGenerator:
    """
    Generates a "hypothetical 10-K excerpt" answering the user's question, then
    uses THAT text as the embedding query for vector search. Bridges the
    vocabulary gap between short user questions and verbose financial language.

    Caches outputs in-memory so repeated questions during a benchmark run
    don't re-spend Groq tokens.
    """

    _PROMPT_TEMPLATE = (
        "Write a 2-3 sentence excerpt as it might appear verbatim in an SEC "
        "10-K annual report, answering the following question. Use formal, "
        "GAAP-aligned financial language. Include realistic placeholder "
        "numbers if the question asks for a metric. Do not say you cannot "
        "answer — just produce the excerpt.\n\n"
        "Question: {question}\n\nExcerpt:"
    )

    def __init__(self, llm):
        self.llm = llm
        self._cache: dict[str, str] = {}

    def generate(self, question: str) -> str:
        if question in self._cache:
            return self._cache[question]
        try:
            from llama_index.core.llms import ChatMessage, MessageRole
            prompt = self._PROMPT_TEMPLATE.format(question=question)
            msg = ChatMessage(role=MessageRole.USER, content=prompt)
            response = self.llm.chat([msg])
            text = str(response.message.content).strip()
            # Combine original + HyDE so neither vocab is lost
            combined = f"{question}\n\n{text}"
            self._cache[question] = combined
            return combined
        except Exception as exc:
            log.warning("HyDE generation failed (%s) — falling back to raw query.", exc)
            return question


# ─── 6. JSON-mode answer extraction for numeric questions ────────────────────

def answer_with_json_extraction(llm, question: str, context_text: str) -> dict:
    """
    Force Groq to return a strict JSON object so numeric ACS scoring works
    reliably. Returns {value, unit, year, source, prose_answer}.

    If JSON parsing fails, returns {"prose_answer": <raw text>}.
    """
    import json
    from llama_index.core.llms import ChatMessage, MessageRole

    system_prompt = (
        "You are a financial analyst extracting answers from SEC 10-K filings. "
        "Find the line item in the context that matches the question's wording "
        "and report its value from the column for the asked-about fiscal year.\n"
        "Notes:\n"
        "  - Prefer the consolidated income statement, balance sheet, or "
        "segment table as your source. These are the canonical totals.\n"
        "  - Values in parentheses (e.g. $(29,915)) are negative per accounting "
        "convention; report the magnitude as a positive number.\n"
        "  - For percentage questions: use the percent verbatim if stated. If "
        "only the dollar components are given, compute the ratio and report "
        "it as a percent. State the inputs you used in prose_answer so the "
        "math can be checked.\n"
        "  - Report dollar values in millions, not thousands.\n"
        "Always respond with a single JSON object: "
        '{"value": <number or null>, "unit": "million USD" | "billion USD" | "percent" | null, '
        '"year": <integer or null>, "source": <short citation>, "prose_answer": <full sentence>}. '
        "If the answer is not in the context, set value=null and explain in prose_answer."
    )
    user_prompt = (
        f"Context from SEC filings:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Respond with the JSON object only, no markdown."
    )
    try:
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]
        # Groq supports JSON mode via additional_kwargs
        response = llm.chat(messages, response_format={"type": "json_object"})
        raw = str(response.message.content).strip()
        # Some models wrap JSON in code fences — strip them
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        return json.loads(raw)
    except Exception as exc:
        # Groq's strict JSON validator returns HTTP 400 with the model's
        # invalid output in `failed_generation`. Recover the value from there
        # rather than discarding the whole answer.
        recovered = _recover_from_failed_generation(str(exc))
        if recovered is not None:
            log.info("Recovered value from failed_generation: %s", recovered.get("value"))
            return recovered
        log.warning("JSON extraction failed (%s) — returning raw text.", exc)
        return {"prose_answer": str(exc), "value": None}


def _recover_from_failed_generation(err_str: str) -> Optional[dict]:
    """
    When Groq's response_format=json_object validator rejects the LLM output,
    the actual generated text is included in the 400 error under the key
    `failed_generation`. The text is usually almost-valid JSON with one bug
    (an unquoted string, a stray comment, a trailing comma). We extract value/
    unit/year/source via regex so a single formatting bug doesn't cost the
    whole answer.

    Financial line items shown in parentheses (e.g. "$(29,915)") represent
    negative values per accounting convention. For expense-type questions the
    benchmark expects the magnitude, so we return abs(value).
    """
    fg_match = _re.search(r"failed_generation['\"]?\s*:\s*['\"](.*?)['\"]\s*\}", err_str, _re.DOTALL)
    if not fg_match:
        return None
    fg = fg_match.group(1)

    val_match = _re.search(r'["\']value["\']\s*:\s*(-?\d+(?:\.\d+)?)', fg)
    if not val_match:
        return None
    try:
        raw_val = float(val_match.group(1))
    except ValueError:
        return None
    value = abs(raw_val)  # 10-K parentheses notation → negative; expense magnitude is positive

    unit_match = _re.search(r'["\']unit["\']\s*:\s*["\']([^"\']+)["\']', fg)
    year_match = _re.search(r'["\']year["\']\s*:\s*(\d{4})', fg)
    src_match = _re.search(r'["\']source["\']\s*:\s*["\']([^"\']*)["\']', fg)

    return {
        "value": value,
        "unit": unit_match.group(1) if unit_match else None,
        "year": int(year_match.group(1)) if year_match else None,
        "source": src_match.group(1) if src_match else "",
        "prose_answer": f"Recovered value: {value}",
    }


# ─── 7. Metadata extraction + filtering ──────────────────────────────────────

import re as _re

_TICKER_KEYWORDS = {
    "AAPL": ["apple", "aapl"],
    "MSFT": ["microsoft", "msft"],
    "GOOGL": ["google", "alphabet", "googl"],
    "TSLA": ["tesla", "tsla"],
    "AMZN": ["amazon", "amzn"],
}


def extract_filters_from_question(question: str) -> dict:
    """
    Cheap, deterministic metadata extraction. No LLM calls — just regex/keywords.
    Returns {tickers: [...], years: [...]}, omitting absent keys.
    """
    q = question.lower()
    tickers = [t for t, names in _TICKER_KEYWORDS.items() if any(n in q for n in names)]
    years = sorted({int(m) for m in _re.findall(r"\b(20\d{2})\b", q) if 2010 <= int(m) <= 2030})
    out: dict = {}
    if tickers:
        out["tickers"] = tickers
    if years:
        out["years"] = years
    return out


_CONSOLIDATED_MARKERS = (
    # Apple-style canonical headings
    "consolidated statements of operations",
    "consolidated statement of operations",
    "consolidated balance sheet",
    "consolidated statements of cash flows",
    "consolidated statement of cash flows",
    "consolidated statements of comprehensive income",
    "consolidated statements of stockholders",
    "consolidated statements of equity",
    # Microsoft-style headings (and other shorter variants)
    "income statements",
    "income statement",
    "balance sheets",
    "cash flows statements",
    "statements of cash flows",
    # Useful in-table labels that signal a canonical income statement chunk
    "total revenue",
    "total operating expenses",
    "operating income",
    "net income",
    "gross margin",
    "gross profit",
)


def _wants_consolidated(question: str) -> bool:
    """
    Heuristic: does the question ask for a company-wide / consolidated figure
    rather than a segment-specific one?
    Returns False if 'segment' or specific segment names are mentioned, since
    those queries should use segment chunks (e.g. 'Intelligent Cloud segment').
    """
    q = question.lower()
    if "segment" in q:
        return False
    # Common segment names — treat as segment-specific even without 'segment' word
    segment_names = (
        "intelligent cloud", "productivity and business processes",
        "more personal computing", "americas", "europe", "greater china",
        "japan", "rest of asia pacific",
    )
    if any(s in q for s in segment_names):
        # Exception: "net sales by segment" type questions still want segment data,
        # but "Apple's Americas revenue" is also segment-level. Keep segment focus.
        return False
    # Trigger words that indicate a consolidated/total figure
    triggers = (
        "total", "consolidated", "company-wide", "overall",
        "net sales", "net income", "net revenue",
        "operating expenses", "operating income", "gross margin",
        "gross profit", "research and development", "cost of",
    )
    return any(t in q for t in triggers)


_GROSS_MARGIN_PATTERNS = (
    _re.compile(r"gross\s+margin\s+(percentage|percent|ratio|%)", _re.I),
    _re.compile(r"gross\s+(profit|margin)\s+as\s+a\s+percent", _re.I),
)


def is_gross_margin_question(question: str) -> bool:
    return any(p.search(question) for p in _GROSS_MARGIN_PATTERNS)


def _parse_dollar(s: str) -> Optional[float]:
    """Parse strings like '394,328', '$ 223,546', '170.8' into floats (millions)."""
    if not s:
        return None
    cleaned = s.replace(",", "").replace("$", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def compute_gross_margin_from_nodes(nodes, year: Optional[int] = None) -> Optional[dict]:
    """
    Deterministic gross margin % resolver — verbatim extraction only.

    Scans retrieved chunks for an explicit "gross margin ... XX.X%" statement
    (e.g. Apple's MD&A typically states "Total gross margin percentage was
    43.3%"). If a chunk shows the percent directly with a value in the
    sane 15–80% range, return it. Otherwise return None and let the caller
    fall back to the LLM.

    A previous version attempted to compute the ratio from Net sales and
    Cost of sales when the % wasn't stated. That approach was dropped: a
    non-canonical chunk (segment breakdown, MD&A discussion of a sub-metric)
    can contain numbers that reconcile arithmetically without representing
    the actual consolidated gross margin. Compute-then-verify produced
    wrong-with-confidence results on q07 (extracted COS=239,250 instead of
    223,546). Verbatim-only is honest.
    """
    direct_re = _re.compile(
        r"gross\s+margin[^\n]{0,80}?(\d{1,2}(?:\.\d+)?)\s*%", _re.I
    )
    for n in nodes:
        text = getattr(n, "get_content", lambda: getattr(n, "text", ""))()
        if not text:
            continue
        m = direct_re.search(text)
        if not m:
            continue
        try:
            pct = float(m.group(1))
        except ValueError:
            continue
        # Sanity range — tech-company gross margin is typically 15–80%
        if 15 <= pct <= 80:
            return {
                "value": pct,
                "unit": "percent",
                "year": year,
                "source": f"Stated verbatim: {m.group(0).strip()}",
                "prose_answer": (
                    f"Gross margin percentage was {pct}% as stated "
                    f"directly in the filing."
                ),
            }
    return None


def boost_consolidated_chunks(nodes, question: str, boost_factor: float = 1.5):
    """
    When the question asks for a consolidated/total figure, multiply the score
    of chunks that contain consolidated-statement section markers. Re-sorts the
    list so boosted chunks float to the top.

    Side-steps the case where reranker scoring puts segment-level discussion
    chunks ahead of the canonical income statement table.
    """
    if not nodes or not _wants_consolidated(question):
        return nodes

    for n in nodes:
        text = getattr(n, "get_content", lambda: getattr(n, "text", ""))().lower()
        if any(marker in text for marker in _CONSOLIDATED_MARKERS):
            try:
                current = float(getattr(n, "score", 0) or 0)
                n.score = current * boost_factor + 0.01  # +0.01 in case score was 0
            except Exception:
                pass

    return sorted(nodes, key=lambda n: float(getattr(n, "score", 0) or 0), reverse=True)


def apply_metadata_filter(nodes, filters: dict):
    """
    Filter retrieved/loaded nodes by ticker and/or year metadata.
    Used to scope BM25 nodes; ChromaDB filtering is done via `where` at query time.
    """
    if not filters:
        return nodes
    tickers = set(filters.get("tickers") or [])
    years = set(filters.get("years") or [])

    out = []
    for n in nodes:
        meta = getattr(n, "metadata", {}) or {}
        if tickers and meta.get("ticker") not in tickers:
            continue
        if years and meta.get("year") not in years:
            continue
        out.append(n)
    return out


# ─── 8. Multi-year query decomposition ───────────────────────────────────────

_TREND_PATTERNS = [
    _re.compile(r"\bfrom\s+(20\d{2})\s+to\s+(20\d{2})\b", _re.I),
    _re.compile(r"\bbetween\s+(20\d{2})\s+and\s+(20\d{2})\b", _re.I),
    _re.compile(r"\bchange.*(20\d{2}).*(20\d{2})", _re.I),
    _re.compile(r"\bcompare.*(20\d{2}).*(20\d{2})", _re.I),
    _re.compile(r"\bevolved?.*(20\d{2}).*(20\d{2})", _re.I),
    _re.compile(r"\btrend.*(20\d{2}).*(20\d{2})", _re.I),
]


def decompose_trend_question(question: str) -> Optional[List[dict]]:
    """
    If the question asks about a multi-year trend, return one sub-query per year.
    Returns None if the question is single-year or non-temporal.

    Sub-query format: {"year": int, "question": str}
    """
    # Find an explicit year range
    year_range = None
    for pat in _TREND_PATTERNS:
        m = pat.search(question)
        if m:
            try:
                y1, y2 = int(m.group(1)), int(m.group(2))
                year_range = (min(y1, y2), max(y1, y2))
                break
            except (ValueError, IndexError):
                continue

    # Or three+ years explicitly listed
    explicit_years = sorted({int(y) for y in _re.findall(r"\b(20\d{2})\b", question)})
    if year_range is None and len(explicit_years) >= 2:
        year_range = (min(explicit_years), max(explicit_years))

    if year_range is None:
        return None

    y1, y2 = year_range
    if y2 - y1 > 5:  # sanity bound
        return None

    years = list(range(y1, y2 + 1))
    sub_queries = []
    # Strip the "trend" phrasing to make per-year queries cleaner
    base = question
    for pat in _TREND_PATTERNS:
        base = pat.sub("", base)
    # Drop interrogative openers ("How did", "What was/were") and
    # trend verbs so the residue is just the metric noun phrase.
    base = _re.sub(
        r"^\s*(how\s+(did|has|have)|what\s+(was|were|is|are)|describe|show)\b",
        "", base, flags=_re.I,
    ).strip()
    base = _re.sub(
        r"\b(change|changed|evolved?|trend|comparison|compare|grow(n|th)?|increase|decrease)\b",
        "", base, flags=_re.I,
    )
    # Expand common SEC abbreviations so BM25 can match the indexed phrasing
    base = _re.sub(r"\bR&D\b", "research and development", base, flags=_re.I)
    base = _re.sub(r"\bSG&A\b", "selling, general and administrative", base, flags=_re.I)
    base = _re.sub(r"\bCOGS\b", "cost of goods sold", base, flags=_re.I)
    # Strip leftover year mentions ("from fiscal year 2021 to fiscal year 2023")
    # so per-year sub-queries don't double-name the year.
    base = _re.sub(r"\bfrom\s+fiscal\s+year\s+20\d{2}\s+to\s+fiscal\s+year\s+20\d{2}\b", "", base, flags=_re.I)
    base = _re.sub(r"\b(in|during|for)\s+(fiscal\s+year\s+)?20\d{2}\b", "", base, flags=_re.I)
    base = _re.sub(r"\b20\d{2}\b", "", base)
    # Drop trailing possessive-question fragments and tidy whitespace
    base = _re.sub(r"\s+", " ", base).strip(" ?.,'s")
    # Drop a stray leading possessive ("Apple's R&D ..." → "Apple's R&D ...")
    if not base:
        base = question  # fallback to original phrasing

    for y in years:
        sub_queries.append({
            "year": y,
            "question": f"What was {base} in fiscal year {y}?".replace("  ", " "),
        })
    return sub_queries


# ─── 9. HyDE skip heuristic ──────────────────────────────────────────────────

def should_skip_hyde(question: str) -> bool:
    """
    Skip HyDE only for VERY specific bare-keyword queries where rewriting
    can't help (e.g., "AAPL revenue 2023"). Default is False — empirical
    benchmarking showed HyDE consistently improves TRA when the user asks
    full-sentence questions, even short ones.
    """
    filters = extract_filters_from_question(question)
    has_company = bool(filters.get("tickers"))
    has_year = bool(filters.get("years"))
    is_terse = len(question.split()) <= 5 and "?" not in question
    return has_company and has_year and is_terse


# ─── 10. Response cache ──────────────────────────────────────────────────────

class _ResponseCache:
    """
    Simple in-memory LRU-ish cache keyed on (question, mode). Lifetime is the
    process — survives across requests during a single uvicorn run, cleared on
    restart. Max 256 entries to keep memory bounded.
    """
    _MAX = 256

    def __init__(self):
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, question: str, mode: str = "graph"):
        with self._lock:
            return self._store.get((question.strip().lower(), mode))

    def put(self, question: str, mode: str, value):
        with self._lock:
            if len(self._store) >= self._MAX:
                # drop oldest (insertion order)
                self._store.pop(next(iter(self._store)))
            self._store[(question.strip().lower(), mode)] = value


RESPONSE_CACHE = _ResponseCache()


# ─── 11. Validate extracted JSON value appears in retrieved context ─────────

def validate_value_in_context(parsed: dict, source_nodes: List) -> bool:
    """
    Returns True if the JSON 'value' appears (in some recognizable form) in at
    least one retrieved chunk. Prevents the LLM from confidently hallucinating
    a number that isn't in the source documents.

    A value passes if any of these forms appear in any node text:
      - exact digits (21914)
      - comma-formatted (21,914)
      - rounded thousands (~$22M, $21.9 billion, etc.)
    """
    value = parsed.get("value")
    if value is None:
        return True   # nothing to validate (qualitative answer)

    try:
        v = float(value)
    except (TypeError, ValueError):
        return True

    integer_str = str(int(v))
    formatted = f"{int(v):,}"
    # A few rounded forms (within 1%) — handles "$21.9 billion" when value=21914
    rounded_variants = []
    if v >= 1000:
        # millions → billions
        billions = v / 1000
        rounded_variants += [f"{billions:.1f}", f"{billions:.2f}"]
    if v >= 1_000_000:
        billions = v / 1_000_000
        rounded_variants += [f"{billions:.1f}", f"{billions:.2f}"]

    candidates = {integer_str, formatted, *rounded_variants}

    for n in source_nodes:
        text = ""
        if isinstance(n, dict):
            text = n.get("text", "")
        else:
            text = getattr(n, "text", "") or (
                getattr(n, "get_content", lambda: "")() if callable(getattr(n, "get_content", None)) else ""
            )
        for cand in candidates:
            if cand and cand in text:
                return True
    return False
