"""
Benchmark evaluator — ground-truth questions and scoring logic.

Ground-truth values are sourced from Apple and Microsoft 10-K filings
(publicly available on SEC EDGAR). All dollar amounts in millions USD.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ─── Ground-Truth Benchmark Questions ────────────────────────────────────────
# Each entry has:
#   id            — unique identifier
#   question      — natural language question
#   type          — "single_year_table" | "multi_year_trend" | "risk_factor"
#   ticker        — company ticker
#   years         — list of years the answer must reference (for CYC metric)
#   expected_value — exact numeric answer (str, in millions unless noted)
#   expected_unit  — e.g. "million", "percent"
#   table_keyword  — a word that should appear in any retrieved chunk that
#                    contains the answer (used for TRA scoring)

BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "q01",
        "question": "What was Apple's research and development expense in fiscal year 2021?",
        "type": "single_year_table",
        "ticker": "AAPL",
        "years": [2021],
        "expected_value": "21914",
        "expected_unit": "million",
        "table_keyword": "research",
    },
    {
        "id": "q02",
        "question": "What was Apple's research and development expense in fiscal year 2023?",
        "type": "single_year_table",
        "ticker": "AAPL",
        "years": [2023],
        "expected_value": "29915",
        "expected_unit": "million",
        "table_keyword": "research",
    },
    {
        "id": "q03",
        "question": "What was Apple's net sales (total revenue) in fiscal year 2022?",
        "type": "single_year_table",
        "ticker": "AAPL",
        "years": [2022],
        "expected_value": "394328",
        "expected_unit": "million",
        "table_keyword": "net sales",
    },
    {
        "id": "q04",
        "question": "How did Apple's R&D expenses change from 2021 to 2023?",
        "type": "multi_year_trend",
        "ticker": "AAPL",
        "years": [2021, 2023],
        "expected_value": None,
        "expected_unit": None,
        "table_keyword": "research",
    },
    {
        "id": "q05",
        "question": "What was Microsoft's revenue from cloud services (Intelligent Cloud segment) in fiscal year 2022?",
        "type": "single_year_table",
        "ticker": "MSFT",
        "years": [2022],
        "expected_value": "75251",
        "expected_unit": "million",
        "table_keyword": "intelligent cloud",
    },
    {
        "id": "q06",
        "question": "What was Microsoft's total revenue in fiscal year 2023?",
        "type": "single_year_table",
        "ticker": "MSFT",
        "years": [2023],
        "expected_value": "211915",
        "expected_unit": "million",
        "table_keyword": "revenue",
    },
    {
        "id": "q07",
        "question": "What was Apple's gross margin percentage in fiscal year 2022?",
        "type": "single_year_table",
        "ticker": "AAPL",
        "years": [2022],
        "expected_value": "43.3",
        "expected_unit": "percent",
        "table_keyword": "gross margin",
    },
    {
        "id": "q08",
        "question": "What risk factors did Apple identify related to supply chain in its 2022 10-K filing?",
        "type": "risk_factor",
        "ticker": "AAPL",
        "years": [2022],
        "expected_value": None,
        "expected_unit": None,
        "table_keyword": "supply chain",
    },
    {
        "id": "q09",
        "question": "How did Microsoft's net income change from fiscal year 2021 to fiscal year 2023?",
        "type": "multi_year_trend",
        "ticker": "MSFT",
        "years": [2021, 2022, 2023],
        "expected_value": None,
        "expected_unit": None,
        "table_keyword": "net income",
    },
    {
        "id": "q10",
        "question": "What was Apple's Americas segment revenue in fiscal year 2021?",
        "type": "single_year_table",
        "ticker": "AAPL",
        "years": [2021],
        "expected_value": "153306",
        "expected_unit": "million",
        "table_keyword": "americas",
    },
]


# ─── Scoring Functions ────────────────────────────────────────────────────────

_UNIT_MULTIPLIERS = {
    "k": 1e3, "thousand": 1e3,
    "m": 1, "million": 1, "mn": 1, "mm": 1,    # values are stored as millions
    "b": 1e3, "billion": 1e3, "bn": 1e3,        # 1 billion = 1000 million
    "t": 1e6, "trillion": 1e6,
}


def _extract_number(text: str, expected_unit: str = None) -> Optional[float]:
    """
    Extract a numeric value from free-form text, normalizing units.
    Supports formats:
      - "21,914"      → 21914
      - "$21,914 million" → 21914
      - "$21.9 billion" → 21900 (in millions)
      - "$22B" → 22000
      - "29915"       → 29915
      - "43.3%"       → 43.3  (when expected_unit="percent")

    Returns the value normalized to millions where applicable. Caller is
    responsible for knowing the expected unit context.
    """
    if not text:
        return None

    # Guard: API error strings (e.g. "Error code: 413") should not be parsed
    if text.strip().lower().startswith("error"):
        return None

    # Unit-aware scan: for percent questions prefer a "NN.N%" match first
    if expected_unit == "percent":
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if pct_match:
            try:
                return float(pct_match.group(1))
            except ValueError:
                pass

    # Generic scan: first number followed by optional unit token.
    # Comma-formatted branch uses + (one-or-more comma groups) so bare numbers
    # like "21914" fall through to the plain \d+ branch and are matched in full,
    # not as a 3-digit prefix ("219").
    pattern = r"\$?\s*(\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(thousand|million|mm|mn|billion|bn|trillion|[kmbt])?"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        raw = match.group(1).replace(",", "").replace(" ", "")
        value = float(raw)
    except ValueError:
        return None

    unit = (match.group(2) or "").lower()
    if unit:
        value *= _UNIT_MULTIPLIERS.get(unit, 1)
    return value


def _keyword_in_text(keyword: str, text: str) -> bool:
    """
    Returns True if the full keyword phrase is present, OR (for multi-word
    keywords) all individual words are present. Handles cases where a heading
    like "net sales" and its table row live in the same chunk but are not
    adjacent as a phrase.
    """
    if not keyword:
        return True
    if keyword in text:
        return True
    words = keyword.split()
    if len(words) > 1 and all(w in text for w in words):
        return True
    return False


def score_tra(question: Dict, source_nodes: List[Dict]) -> int:
    """
    Table Retrieval Accuracy (TRA): 1 if a retrieved chunk contains BOTH:
      (a) the question's keyword (semantic match), AND
      (b) the expected numeric value as a complete number (not a substring).

    For questions without expected_value (risk factors, trend Qs), falls back
    to: keyword present AND the chunk contains a pipe-delimited table row.
    This is stricter than just "has '|' and keyword" — it tests that the
    retriever actually fetched the chunk with the answer.
    """
    keyword = question.get("table_keyword", "").lower()
    expected = question.get("expected_value")

    for node in source_nodes:
        text = node.get("text", "").lower()
        if keyword and not _keyword_in_text(keyword, text):
            continue

        if expected:
            # Match the number with optional comma separators, as a whole token
            num_str = str(expected).replace(",", "")
            # Build a regex that matches the number with or without commas, surrounded by non-digit
            patterns = [
                rf"(?<!\d){num_str}(?!\d)",                           # 21914
                rf"(?<!\d){num_str[:-3]},{num_str[-3:]}(?!\d)" if len(num_str) > 3 else None,  # 21,914
            ]
            for p in filter(None, patterns):
                if re.search(p, text):
                    return 1
        else:
            # No expected number — require a real Markdown table row
            if "|" in text and re.search(r"\|[^\n]{2,}\|[^\n]{2,}\|", text):
                return 1
    return 0


def score_acs(question: Dict, answer: str) -> float:
    """
    Answer Correctness Score (ACS): 1.0 for exact match, 0.5 for near match
    (within 5%), 0.0 otherwise. Returns None for questions without expected_value.
    """
    expected_str = question.get("expected_value")
    if not expected_str:
        return None  # type: ignore[return-value]

    try:
        expected = float(expected_str.replace(",", ""))
    except ValueError:
        return None  # type: ignore[return-value]

    actual = _extract_number(answer, expected_unit=question.get("expected_unit"))
    if actual is None:
        return 0.0

    # Normalise units: if expected is in millions and actual looks like billions
    if expected > 1000 and actual < expected / 100:
        actual *= 1000

    diff_pct = abs(actual - expected) / max(abs(expected), 1)
    if diff_pct <= 0.01:
        return 1.0
    if diff_pct <= 0.05:
        return 0.5
    return 0.0


def score_cyc(question: Dict, answer: str) -> Optional[int]:
    """
    Cross-Year Coherence (CYC): 1 if the answer mentions all required years.
    Only applies to multi_year_trend questions.
    """
    if question.get("type") != "multi_year_trend":
        return None
    required_years = question.get("years", [])
    for year in required_years:
        if str(year) not in answer:
            return 0
    return 1


def compute_summary(results: List[Dict]) -> Dict:
    """Aggregate per-question scores into a summary dict."""
    tra_naive, tra_struct = [], []
    acs_naive, acs_struct = [], []
    cyc_naive, cyc_struct = [], []
    lat_naive, lat_struct = [], []

    for r in results:
        n = r["naive"]
        s = r["structured"]

        tra_naive.append(n["tra"])
        tra_struct.append(s["tra"])

        if n["acs"] is not None:
            acs_naive.append(n["acs"])
        if s["acs"] is not None:
            acs_struct.append(s["acs"])

        if n["cyc"] is not None:
            cyc_naive.append(n["cyc"])
        if s["cyc"] is not None:
            cyc_struct.append(s["cyc"])

        lat_naive.append(n["latency_ms"])
        lat_struct.append(s["latency_ms"])

    def avg(lst): return round(sum(lst) / len(lst), 4) if lst else 0.0
    def pct_improvement(a, b): return round((b - a) / max(a, 0.001) * 100, 1)

    naive_tra = avg(tra_naive)
    struct_tra = avg(tra_struct)
    naive_acs = avg(acs_naive)
    struct_acs = avg(acs_struct)
    naive_cyc = avg(cyc_naive)
    struct_cyc = avg(cyc_struct)

    return {
        "naive_tra": naive_tra,
        "structured_tra": struct_tra,
        "naive_acs": naive_acs,
        "structured_acs": struct_acs,
        "naive_cyc": naive_cyc,
        "structured_cyc": struct_cyc,
        "naive_avg_latency_ms": round(avg(lat_naive), 1),
        "structured_avg_latency_ms": round(avg(lat_struct), 1),
        "improvement_tra_pct": pct_improvement(naive_tra, struct_tra),
        "improvement_acs_pct": pct_improvement(naive_acs, struct_acs),
        "improvement_cyc_pct": pct_improvement(naive_cyc, struct_cyc),
        "total_questions": len(results),
    }
