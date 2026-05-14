# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Multi-Year SEC Filing Trend Analyzer (FilingsIQ)

A production-grade RAG system that downloads SEC 10-K filings, parses them with LlamaParse, and answers cross-year financial questions. The headline value is a benchmark proving structure-aware retrieval beats naive RAG:

**Current benchmark (structured vs naive):**

- TRA (Table Retrieval Accuracy): **90% vs 50%**
- ACS (Answer Correctness Score): **71% vs 43%**
- CYC (Cross-Year Coherence): **100% vs 100%**

## Deployment Architecture

Two services, both live:

| Layer    | Service                                  | URL                                |
| -------- | ---------------------------------------- | ---------------------------------- |
| Frontend | Vercel (Next.js)                         | https://filingsiq.vercel.app       |
| Backend  | Fly.io (FastAPI, `iad` region, 2 GB VM)  | https://filingsiq-api.fly.dev      |

> **History:** the backend used to run on Render free tier at `sec-analyzer-t2hx.onrender.com`. The 512 MB / 0.1 CPU plan could not host fastembed + flashrank + Pinecone-fetch buffers simultaneously — queries OOM-killed the worker around the 30 s edge timeout. Migrated to Fly.io: 2 GB shared-cpu-1x, `min_machines_running = 1` so users never hit a cold start, second machine auto-stops when idle. `render.yaml` is still in the repo but unused; the Render service should be deleted.

**Request routing — Vercel proxy:**
`vercel.json` (both root and `frontend/vercel.json`) rewrites `/api/*` to `filingsiq-api.fly.dev`. `BASE = ''` in `frontend/lib/api.ts` keeps API calls as relative URLs through this proxy. **Both `vercel.json` files must be updated together** — Vercel deploys from `frontend/` and reads that one, but the root copy is kept for parity.

**Cold start latency:** With `min_machines_running = 1` one Fly VM is always warm; a cached query returns in ~0.5 s, a fresh query in ~16 s. The client timeout is 240 s (`QUERY_TIMEOUT_MS` in `frontend/lib/api.ts`) — generous holdover from the Render era, leave it. The Ask page pings `/api/pipeline/data-status` on mount as a no-op warmup; harmless on Fly but doesn't change anything.

**Vercel deployment:** No GitHub auto-deploy integration. To deploy frontend changes: `npx vercel --prod --yes` from `frontend/`. Do NOT use the Vercel dashboard "Redeploy" button — it re-runs the old build without picking up git changes.

**Fly deployment:** Use the CLI from project root: `~/.fly/bin/flyctl.exe deploy --remote-only --wait-timeout 600`. There is no GitHub auto-deploy wired up. `Dockerfile`, `fly.toml`, `.dockerignore` at project root define the build; `fly.toml` sets the model + env, secrets are set with `fly secrets set KEY=value`.

**Vector store:** Pinecone Serverless (index name: `sec-filings`, AWS us-east-1). Two namespaces:

- `structured` — production query path
- `naive` — benchmark baseline

**Pinecone data is persistent** — built locally once, lives in Pinecone forever. Fly never needs to rebuild it (no `Build Index` step needed on cold start).

**Required Fly secrets** (set via `fly secrets set KEY=value --app filingsiq-api`):

- `PINECONE_API_KEY`
- `GROQ_API_KEY`
- `LLAMA_CLOUD_API_KEY`
- `SEC_USER_EMAIL`

**Production env vars in `fly.toml` `[env]`** (non-secret, committed to repo):

- `ENVIRONMENT = "production"`
- `GROQ_MODEL = "llama-3.1-8b-instant"` — **do NOT use `llama3-8b-8192`, it has been decommissioned by Groq** and returns HTTP 400 `model_decommissioned`.
- `TARGET_TICKERS = "AAPL,MSFT"`
- `TARGET_YEARS = "2021,2022,2023,2024"`
- `SKIP_BM25_FETCH = "1"` — short-circuits `_fetch_all_nodes_from_pinecone` which is broken on Pinecone Serverless v3 (`list()` returns 2790 IDs but `fetch()` returns 0 vectors). Saves ~8 s per cold start. Production has been silently vector-only since launch.

## Common Commands

All commands assume venv is activated (`venv\Scripts\activate` on Windows).

```bash
# Setup (one-time)
pip install -r requirements.txt
cp .env.example .env   # fill in LLAMA_CLOUD_API_KEY, GROQ_API_KEY, SEC_USER_EMAIL, PINECONE_API_KEY

# Data pipeline (run once, in order)
python scripts/download_filings.py            # ~5 min: SEC EDGAR direct HTTP
python scripts/parse_filings.py               # ~30 min: LlamaParse cloud API (cached)
python scripts/build_index.py --naive-only --force   # ~10 min: builds naive + structured into Pinecone (skips slow PropertyGraph)

# Optional: full GraphRAG index (slow, mostly for completeness)
python scripts/build_index.py --graph-only --force

# Run the benchmark (re-scores with current code, no rebuild needed)
python scripts/run_benchmark.py

# Serve the backend locally
uvicorn app.main:app --host 127.0.0.1 --port 8000
# DO NOT use --reload on Windows — file watcher deadlocks with fastembed cache

# Run frontend locally
cd frontend && npm run dev

# Deploy
~/.fly/bin/flyctl.exe deploy --remote-only --wait-timeout 600    # backend (run from project root)
cd frontend && npx vercel --prod --yes                            # frontend
```

## Critical Constraints

- **Windows + Groq free tier + no GPU** — these dictate all architectural choices.
  - No `torch` / no `sentence-transformers`. Use `fastembed` (ONNX) for embeddings, `flashrank` (ONNX) for reranking.
  - Groq free tier limits: 30 RPM, ~30K TPM, **and ~500K TPD (tokens-per-day, rolling 24h window)**. The throttle in `app/rag_utils.py` is set to 28 RPM with retry backoff capped at 8s. Do NOT raise either without explicit user approval. Heavy benchmark iteration (5–6 full runs in a day) burns the daily budget and produces 429s for ~24h — plan re-runs accordingly.
- **Llama-3.1-8b-instant is the bottleneck for arithmetic and prompt-following.** Long, rule-heavy prompts make it WORSE, not better — short prompts produce more consistent JSON. Few-shot examples leak verbatim into outputs. Don't add per-question prompt rules; they overfit and regress on the next run.
- **Groq HTTP 400 `json_validate_failed` is a real failure mode** when `response_format={"type":"json_object"}` is used. The model's actual output sits in `failed_generation` and is usually recoverable — see `_recover_from_failed_generation()`.
- **Pre-filtered BM25:** when `filters` (ticker/year) are present, `_retrieve_with_hyde` rebuilds BM25 over the scoped nodes only. This prevents wrong-company chunks from displacing the correct table in the fused top-40. **Note:** in production this code path is bypassed because `SKIP_BM25_FETCH=1` keeps `nodes=[]`; everything runs vector-only.
- **Empty Pinecone namespace guard:** `_get_production_components()` in `structured_chunker.py` checks if `_fetch_all_nodes_from_pinecone` returns empty. If so, falls back to vector-only retrieval instead of crashing BM25. If structured queries return 0% across the board, the namespace is empty — run `build_index.py --naive-only --force`.
- **`DISABLE_RERANKER=1` env toggle** in `_get_production_components()` skips flashrank entirely when set. Kept around as a defensive switch for memory-constrained hosts (Render free tier was the original need). Currently UNSET in `fly.toml` because 2 GB has the headroom; if you ever downsize the VM, set this first.
- **`SKIP_BM25_FETCH=1` env toggle** in `_get_production_components()` skips the broken `_fetch_all_nodes_from_pinecone()` call. The Pinecone v3 Serverless SDK returns 2790 IDs from `list(namespace="structured")` but the corresponding `fetch()` returns 0 vectors — root cause unknown (likely namespace prefix or ID format mismatch). Until fixed, production runs vector-only. **This means the published benchmark numbers (TRA 90% vs 50%, ACS 71% vs 43%) describe a local-dev configuration that no longer matches prod.** Either fix the SDK call, or re-run the benchmark with `SKIP_BM25_FETCH=1` and update the headline.
- **Confidence assignment must respect `value_verified`** — `parsed["confidence"] = 1.0` must only run when `value_verified=True`. Don't collapse the two writes.
- **Tight version pins:** `llama-index-core>=0.12.0,<0.13.0` + `llama-index-retrievers-bm25==0.5.2`. The latest `bm25-retriever` pulls core 0.14 which breaks the rest of the stack.
- **`uvicorn --reload` deadlocks on Windows** with this project's file count. Always omit `--reload` when serving.
- **Pydantic Groq class blocks attribute assignment.** `build_throttled_groq()` uses subclassing, not monkey-patching. Don't revert to the latter.
- **PowerShell `curl` is `Invoke-WebRequest`** — use `curl.exe` or a browser for local API testing.
- **`sec-edgar-downloader` is intentionally NOT a dependency.** We hit `data.sec.gov` directly via `httpx` in `app/pipeline/sec_downloader.py`. Don't reintroduce the package.

## Architecture

### Data flow

```
SEC EDGAR (.htm)  →  data/raw_filings/{TICKER}/{YEAR}/filing.htm   (sec_downloader.py)
       ↓
LlamaParse cloud  →  data/parsed_markdown/{TICKER}_{YEAR}.md       (llama_parser.py, cached)
       ↓
Structure-aware chunker  →  Pinecone namespace "structured"        (structured_chunker.py)
       ↓
Hybrid retriever (Vector + BM25 → RRF) → flashrank reranker → Groq LLM
```

A parallel `naive` namespace is built from the same Markdown using fixed-size 512-token splitting — this is the baseline the benchmark compares against.

### Two pipelines, one codebase

|           | Naive (Basic Mode)                                          | Structured (Smart Mode)                                                                     |
| --------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Chunker   | `app/benchmarks/naive_chunker.py` (fixed 512-token windows) | `app/benchmarks/structured_chunker.py` (table-aware + metadata headers + table-as-document) |
| Retrieval | Vector top-5                                                | Vector + BM25 top-40 → RRF → flashrank top-10                                               |
| Synthesis | Default LlamaIndex tree_summarize                           | Strict context-only prompt OR JSON-mode for numerics OR per-year decomposition for trends   |

### The 8 production RAG modules (all in `app/rag_utils.py`)

1. `prepend_metadata_header()` — every chunk starts with `Company: X | Year: Y | Document: 10-K | Content: ...`
2. `build_throttled_groq()` — Groq subclass with token-bucket throttle + tenacity retry
3. `FastEmbedReranker` — wraps `flashrank.Ranker` to fit LlamaIndex NodePostprocessor protocol
4. `build_hybrid_retriever()` — Vector + BM25 with `QueryFusionRetriever(mode="reciprocal_rerank")`
5. `HyDEGenerator` — LLM rewrites query as hypothetical 10-K excerpt; in-memory cached
6. `answer_with_json_extraction()` — Groq JSON-mode for numeric answers
7. `extract_filters_from_question()` + `apply_metadata_filter()` — regex-based ticker/year filtering
8. `decompose_trend_question()` — regex-based multi-year decomposition (no LLM call)

Plus optimizations:

- `should_skip_hyde()` — skips HyDE for terse keyword queries (≤5 words, no `?`)
- `RESPONSE_CACHE` — in-memory question→answer cache, capped at 256 entries
- `validate_value_in_context()` — JSON-mode numeric values must appear in retrieved chunks
- `_truncate_context()` — caps context at 16k chars to avoid Groq 413 errors
- `boost_consolidated_chunks()` — 1.5× score for consolidated-statement chunks on total-figure questions
- `_recover_from_failed_generation()` — recovers values from Groq 400 `json_validate_failed` errors
- `compute_gross_margin_from_nodes()` — two-pass year-aware verbatim % extractor (pass 1: MD&A "was X%"; pass 2: broad scan preferring year-qualified matches)

### Benchmark questions (`app/benchmarks/evaluator.py`)

10 ground-truth questions, three metrics:

- **TRA** — Table Retrieval Accuracy: retrieved chunks contain the expected numeric value + keyword
- **ACS** — Answer Correctness Score: extracted number within 5% of ground truth
- **CYC** — Cross-Year Coherence: trend answers mention all required years

q06 was changed from "MSFT total operating expenses" (ambiguous, wrong ground truth ~134K) to "MSFT total revenue FY2023" (unambiguous, $211,915M). Don't revert q06 to the old question.

### Caching layout

- `data/raw_filings/` — gitignored (large .htm files)
- `data/parsed_markdown/` — **commit to git** (text only, ~10 MB; avoids re-paying LlamaParse)
- `data/chroma_db/` — gitignored (legacy, no longer used)
- `data/benchmark_results.json` — **commit to git** — Benchmark tab reads this file; verify numbers before committing

### Frontend

Next.js app in `frontend/`. Three pages: **Ask** (`/ask`), **Benchmark** (`/benchmark`), **Pipeline** (`/pipeline`).

- API calls are in `frontend/lib/api.ts`. `BASE = ''` so all calls are relative URLs proxied through Vercel → Fly.
- Query timeout is 240s client-side (`QUERY_TIMEOUT_MS`) — generous holdover from the Render era, leave it.
- Ask page pings `/api/pipeline/data-status` on mount as a no-op warmup (kept for cheap safety on first paint).
- Ask page shows a dismissible **`WelcomeCard`** above the input (`frontend/components/ask/WelcomeCard.tsx`) explaining the project to new visitors. Dismissal is stored in `localStorage` under `filingsiq:welcome-dismissed:v1`.
- `app/main.py` has a `cors_fallback` HTTP middleware that handles OPTIONS preflights and adds `Access-Control-Allow-Origin: *` to all responses (needed if routing ever switches back to direct calls).

**Benchmark page response shape contract — DO NOT silently break this.** The frontend types in `frontend/lib/types.ts` (`BenchmarkResultResponse`, `BenchmarkSummary`, `BenchmarkResult`) mirror the actual backend response from `/api/benchmark/results`:
- `summary` is **flat snake_case** (`naive_tra`, `structured_tra`, `naive_acs`, ..., `improvement_tra_pct`, etc.) — not nested objects.
- `results[i]` has nested `naive` / `structured` objects, each with `{ answer, tra, acs, cyc, latency_ms, retrieved_chunks, table_in_context }`.
- The page-level field is `r.type` (not `r.question_type`).

If you change the backend response shape, update `types.ts`, `StatsGrid.tsx`, `RadarChart.tsx`, and `BenchmarkTable.tsx` in lockstep. A previous mismatch crashed the `/benchmark` page with "Application error: a client-side exception has occurred."

## Where to make common changes

- **Adjust retrieval params** (top-k, RRF cutoff): `_get_production_components()` in `structured_chunker.py`
- **Add a benchmark question**: append to `BENCHMARK_QUESTIONS` in `evaluator.py`
- **Tune the answer prompt**: `_STRICT_ANSWER_PROMPT` in `structured_chunker.py`
- **Change throttle RPM**: `_GROQ_LIMITER` in `rag_utils.py`
- **Change deployed Groq model**: `[env].GROQ_MODEL` in `fly.toml`, then `fly deploy`. Verify the model is still listed at console.groq.com/docs/models before shipping.
- **Frontend changes**: edit files in `frontend/`, run `npm run dev` to preview, deploy with `npx vercel --prod --yes` from `frontend/`
- **Backend changes**: edit, then `~/.fly/bin/flyctl.exe deploy --remote-only --wait-timeout 600` from project root. First image build is ~5–8 min, subsequent layer-cached builds ~2–3 min
- **Update onboarding copy**: `frontend/components/ask/WelcomeCard.tsx`. Bump the localStorage key suffix (`v1` → `v2`) if you want previously-dismissed users to see it again
- **Add a deterministic calculator**: mirror `compute_gross_margin_from_nodes` + `is_gross_margin_question` in `rag_utils.py`, wire into `query_structured_json` BEFORE the LLM call
- **Tune retrieval scope vs. boost**: pre-filter logic in `_retrieve_with_hyde` (`structured_chunker.py`), boost markers in `_CONSOLIDATED_MARKERS` (`rag_utils.py`)

## Known issues (not yet fixed)

- **BM25 hybrid retrieval is silently disabled in production** via `SKIP_BM25_FETCH=1`. Root cause: Pinecone Serverless v3 SDK `index.fetch(ids=...)` returns 0 vectors for IDs that `index.list(namespace=...)` enumerates fine (2790 IDs → 0 fetched). Until diagnosed, the `structured` retrieval path is effectively vector-only and the published structured-vs-naive benchmark deltas are not currently produced by the live code.
- **Wrong-magnitude numeric answers on some questions.** Live `/api/query` for "What was Microsoft's net income in 2023?" returned `$82 million USD` (actual: $72.4 B). Likely fallout from vector-only retrieval pulling a less-precise top chunk; not seen on AAPL revenue queries which return correct $383.3 B.
- **`render.yaml` is stale.** The Render service is decommissioned; the file should either be deleted or left with a comment noting it's unused.
