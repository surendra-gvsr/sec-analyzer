# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Multi-Year SEC Filing Trend Analyzer

A production-grade RAG system that downloads SEC 10-K filings, parses them with LlamaParse, and answers cross-year financial questions. The headline value is a benchmark proving structure-aware retrieval beats naive RAG (TRA 80% / ACS 71% / CYC 100% vs naive ~40% / ~43% / 50%).

## Common Commands

All commands assume venv is activated (`venv\Scripts\activate` on Windows).

```bash
# Setup (one-time)
pip install -r requirements.txt
cp .env.example .env   # then fill in LLAMA_CLOUD_API_KEY, GROQ_API_KEY, SEC_USER_EMAIL

# Data pipeline (run once, in order)
python scripts/download_filings.py            # ~5 min: SEC EDGAR direct HTTP
python scripts/parse_filings.py               # ~30 min: LlamaParse cloud API (cached)
python scripts/build_index.py --naive-only --force   # ~10 min: builds naive + structured ChromaDB

# Optional: full GraphRAG index (slow, mostly for completeness)
python scripts/build_index.py --graph-only --force

# Run the benchmark (re-scores with current code, no rebuild needed)
python scripts/run_benchmark.py

# Serve the demo
uvicorn app.main:app --host 127.0.0.1 --port 8000
# DO NOT use --reload on Windows — file watcher deadlocks with ChromaDB/fastembed cache

# Single-filing testing
python scripts/build_index.py --tickers AAPL --years 2023 --naive-only --force
```

## Critical Constraints

- **Windows + Groq free tier + no GPU** — these dictate all architectural choices.
  - No `torch` / no `sentence-transformers`. Use `fastembed` (ONNX) for embeddings, `flashrank` (ONNX) for reranking.
  - Groq free tier limits: 30 RPM, ~30K TPM, **and ~500K TPD (tokens-per-day, rolling 24h window)**. The throttle in `app/rag_utils.py` is set to 28 RPM with retry backoff capped at 8s. Do NOT raise either without explicit user approval. Heavy benchmark iteration (5–6 full runs in a day) burns the daily budget and produces 429s for ~24h — plan re-runs accordingly.
- **Llama-3.1-8b-instant is the bottleneck for arithmetic and prompt-following.** Long, rule-heavy prompts make it WORSE, not better — short prompts produce more consistent JSON. Few-shot examples leak verbatim into outputs (a `"Research and development: 21,914"` example caused the model to hallucinate `"Research and development: $25,000"` as a citation). Don't add per-question prompt rules; they overfit and regress on the next run.
- **Groq HTTP 400 `json_validate_failed` is a real failure mode** when `response_format={"type":"json_object"}` is used. The model's actual output sits in `failed_generation` and is usually recoverable — see `_recover_from_failed_generation()`. Without recovery a trailing comma or unquoted string discards the whole answer.
- **Pre-filtered BM25:** when `filters` (ticker/year) are present, `_retrieve_with_hyde` rebuilds BM25 over the scoped nodes only. This prevents wrong-company chunks from displacing the correct table in the fused top-40. ChromaDB vector search still uses the full index.
- **Confidence assignment must respect `value_verified`** — there's a tempting bug where `parsed["confidence"] = 1.0` runs unconditionally and overwrites the demotion branch. The `value_verified` boolean exists specifically to prevent this; don't collapse the two writes.
  - Tight version pins: `llama-index-core>=0.12.0,<0.13.0` + `llama-index-retrievers-bm25==0.5.2`. The latest `bm25-retriever` pulls core 0.14 which breaks the rest of the stack.
- **`uvicorn --reload` deadlocks on Windows** with this project's file count. Always omit `--reload` when serving.
- **Pydantic Groq class blocks attribute assignment.** `build_throttled_groq()` uses subclassing, not monkey-patching. Don't revert to the latter.
- **PowerShell `curl` is `Invoke-WebRequest`**, which behaves oddly with localhost. Tell users to use `curl.exe` or open the URL in a browser.
- **`sec-edgar-downloader` is intentionally NOT a dependency.** v5.x has a `Limiter` bug, v4.x random-generates User-Agents that SEC blocks. We hit `data.sec.gov` directly via `httpx` in `app/pipeline/sec_downloader.py`. Don't reintroduce the package.

## Architecture

### Data flow

```
SEC EDGAR (.htm)  →  data/raw_filings/{TICKER}/{YEAR}/filing.htm   (sec_downloader.py, direct HTTP)
       ↓
LlamaParse cloud  →  data/parsed_markdown/{TICKER}_{YEAR}.md       (llama_parser.py, cached)
       ↓
Structure-aware chunker  →  ChromaDB collection "structured_chunks"  (structured_chunker.py)
       ↓
Hybrid retriever (Vector + BM25 → RRF) → flashrank reranker → Groq LLM
```

A parallel `naive_chunks` collection is built from the same Markdown using fixed-size 512-token splitting — this is the baseline the benchmark compares against.

### Two pipelines, one codebase

This project deliberately maintains TWO query paths and benchmarks them against each other:

|           | Naive (Basic Mode)                                          | Structured (Smart Mode)                                                                     |
| --------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Chunker   | `app/benchmarks/naive_chunker.py` (fixed 512-token windows) | `app/benchmarks/structured_chunker.py` (table-aware + metadata headers + table-as-document) |
| Retrieval | Vector top-5                                                | Vector + BM25 top-40 → RRF → flashrank top-10                                               |
| Synthesis | Default LlamaIndex tree_summarize                           | Strict context-only prompt OR JSON-mode for numerics OR per-year decomposition for trends   |
| Throttle  | Yes (`build_throttled_groq`)                                | Yes                                                                                         |

Both are exercised by the benchmark (`benchmark_runner.py`) AND by the live `/api/query` endpoint (mode param).

### The 8 production RAG modules

All in `app/rag_utils.py`:

1. `prepend_metadata_header()` — every chunk starts with `Company: X | Year: Y | Document: 10-K | Content: ...` (index-time)
2. `build_throttled_groq()` — Groq subclass with token-bucket throttle + tenacity retry
3. `FastEmbedReranker` — wraps `flashrank.Ranker` to fit LlamaIndex's NodePostprocessor protocol
4. `build_hybrid_retriever()` — Vector + BM25 with `QueryFusionRetriever(mode="reciprocal_rerank")`
5. `HyDEGenerator` — LLM rewrites query as hypothetical 10-K excerpt; in-memory cached
6. `answer_with_json_extraction()` — Groq `response_format={"type":"json_object"}` for numeric answers
7. `extract_filters_from_question()` + `apply_metadata_filter()` — regex-based ticker/year filtering, no LLM
8. `decompose_trend_question()` — regex-based multi-year decomposition (no LLM call)

Plus three optimizations:

- `should_skip_hyde()` — skip HyDE when question is already specific (saves a Groq call). Currently only skips for terse keyword-style queries (≤5 words, no `?`); a more aggressive "factual lookup" path was tried and reverted (it regressed segment-specific queries like q05).
- `RESPONSE_CACHE` — in-memory question→answer cache, capped at 256 entries
- `validate_value_in_context()` — JSON-mode numeric values must appear in retrieved chunks (kills hallucination)

And four extraction-reliability helpers added later:

9. `_truncate_context()` — caps context at 16k chars (~4k tokens) before sending to Groq. Risk-factor chunks can be 8k+ chars each, joining 10 of them blows the 6K TPM cap and triggers 413 errors.
10. `boost_consolidated_chunks()` + `_wants_consolidated()` — when the question asks for a "total/consolidated/net X" figure (and isn't segment-specific), 1.5× the rerank score of chunks containing income-statement / balance-sheet markers (`_CONSOLIDATED_MARKERS`). Skipped automatically if the question mentions `segment` or a known segment name (e.g. `Intelligent Cloud`, `Americas`).
11. `_recover_from_failed_generation()` — when Groq returns HTTP 400 `json_validate_failed`, regex-extracts `{value, unit, year, source}` from the `failed_generation` field of the error payload. Apple expense values appear as `$(29,915)` (parentheses = negative per accounting convention); `abs()` is applied so the magnitude flows through.
12. `compute_gross_margin_from_nodes()` + `is_gross_margin_question()` — verbatim "gross margin XX.X%" extraction with sanity range (15–80%). Falls back to LLM if not stated explicitly. A compute-from-components path was tried and rejected: non-canonical chunks (segment-level, MD&A breakdowns) can have `Net sales`, `Cost of sales`, and `Gross margin` values that reconcile arithmetically without representing the consolidated figure (q07 was extracted as `(394328−239250)/394328 = 39.3%` despite Apple's actual 2022 GM being 43.3%).

### Numeric extraction history

`_extract_number()` in `evaluator.py` had a regex bug where `\d{1,3}(?:[,\s]\d{3})*` matched `"219"` from `"21914"` (zero comma groups, partial match wins over the longer-matching `\d+` alternative). Fixed by changing `*` to `+` (require ≥1 comma group on the comma-formatted branch) so bare numbers fall through to `\d+`. **Don't loosen back to `*` without re-testing q01.**

Other evaluator fixes worth knowing:

- `_keyword_in_text()` — multi-word `table_keyword` like `"net sales"` now passes if all words are present, not just the exact phrase. Without this q03 sometimes failed when the chunk had the heading and the table row separately.
- `_extract_number(expected_unit="percent")` — scans `(\d+(?:\.\d+)?)\s*%` first so q07 finds `43.3%` instead of grabbing a revenue dollar.
- Error-string guard — strings starting with `"error"` short-circuit to `None` so `"Error code: 413"` doesn't get parsed as `413`.

### Live query routing (important)

`/api/query` routes through `app/pipeline/query_engine.py:query()` which dispatches to one of three paths in `structured_chunker.py`:

- `query_structured_trend()` — when `decompose_trend_question()` matches (multi-year), uses `ThreadPoolExecutor` for parallel sub-queries
- `query_structured_json()` — when single year + numeric metric keyword, returns `{value, unit, confidence, ticker, ...}`
- `query_structured()` — fallback prose synthesis with strict context-only prompt

The endpoint also populates a `structured` field on the response (see `StructuredAnswer` in `app/models.py`) so the frontend can render the Answer Card with a big numeric display, the Trend Card with a Chart.js line chart, and a confidence bar.

### Benchmark scoring

`app/benchmarks/evaluator.py` defines 10 ground-truth questions. Three metrics:

- **TRA** — Table Retrieval Accuracy: did the retrieved chunks contain a Markdown table row matching the expected value?
- **ACS** — Answer Correctness Score: numeric answer extracted from prose matches expected (within 5%)?
- **CYC** — Cross-Year Coherence: for trend questions, does the answer mention all required years?

The CYC metric is the headline GraphRAG win — it's where structured chunking + decomposition decisively beats naive RAG.

### Caching layout

- `data/raw_filings/` — gitignored (large .htm files)
- `data/parsed_markdown/` — **commit to git** (text only, ~10 MB; avoids re-paying LlamaParse on deploy)
- `data/chroma_db/` — gitignored (rebuilt from committed Markdown on first run)
- `data/graph_store/property_graph.json` — commit if you build it (~2-5 MB)
- `data/benchmark_results.json` — commit to ensure deployed app has results to display. **The Benchmark tab in `index.html` reads this file directly** — if you regenerate it with broken numbers (e.g. mid-debugging) and commit, the deployed UI shows them. Verify the summary block before committing.

### Frontend

Single-file `index.html` with inline CSS+JS, no build step. Uses Chart.js via CDN. Three tabs: **Ask** (Smart/Basic/Compare modes), **Benchmark**, **Pipeline**. Renders the structured answer payload as Answer Card → Trend Card → collapsible Evidence section.

## Where to make common changes

- **Adjust retrieval params** (top-k, RRF cutoff): `_get_production_components()` in `structured_chunker.py`
- **Add a benchmark question**: append to `BENCHMARK_QUESTIONS` in `evaluator.py`
- **Tune the answer prompt**: `_STRICT_ANSWER_PROMPT` in `structured_chunker.py`
- **Change throttle RPM**: `_GROQ_LIMITER` in `rag_utils.py`
- **Add a new metric label** (for the Answer Card chip): `_METRIC_KEYWORDS` in `query_engine.py`
- **Frontend changes**: edit `index.html` directly, hard-refresh browser (`Ctrl+Shift+R`) — no build/restart needed for HTML changes, but Python changes need uvicorn restart
- **Add a deterministic calculator** (e.g. operating margin, debt/equity ratio): mirror the pattern in `compute_gross_margin_from_nodes` + `is_gross_margin_question` in `rag_utils.py`, then wire it into `query_structured_json` BEFORE the LLM call with a fall-through to `answer_with_json_extraction` if the components aren't found. Verbatim-extract only — don't compute from line items unless you have a strong sanity check.
- **Tune retrieval scope vs. boost balance**: pre-filter logic is in `_retrieve_with_hyde` (`structured_chunker.py`), boost markers are in `_CONSOLIDATED_MARKERS` (`rag_utils.py`). Adding a marker is safe; widening the trigger words in `_wants_consolidated` is risky (can hijack segment queries).
- **Improve trend question handling**: `decompose_trend_question()` in `rag_utils.py` strips interrogative openers (`How did`, `What was`), expands abbreviations (`R&D` → `research and development`, `SG&A`, `COGS`), and removes year mentions before generating per-year sub-queries. Add new abbreviations there if you see new failure modes.
