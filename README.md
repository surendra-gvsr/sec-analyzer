# FilingsIQ — Multi-Year SEC 10-K Trend Analyzer

A production-grade RAG system for cross-year SEC 10-K analysis, built to demonstrate that **structure-aware retrieval beats naive vector RAG for financial tables**. Ask plain-English questions about Apple and Microsoft 10-K filings (FY 2021–2024) and get back grounded, cited answers.

**Live demo:** https://filingsiq.vercel.app
**Backend health:** https://filingsiq-api.fly.dev/health

---

## What this project proves

Most "RAG over PDFs" demos chunk documents into fixed-size token windows and feed top-k vector matches to an LLM. That approach falls over on financial filings, where the most important content lives inside Markdown tables that get split mid-row by naive chunkers.

This project implements an alternative pipeline — table-aware chunking + metadata-prefixed nodes + hybrid retrieval + cross-encoder reranking + Groq LLM synthesis — and ships a side-by-side benchmark proving the structured approach wins on the metrics analysts actually care about.

| Metric | Naive RAG | Structured RAG | Delta |
| --- | --- | --- | --- |
| Table Retrieval Accuracy (TRA) | 50% | **90%** | +40 pp |
| Answer Correctness Score (ACS) | 43% | **71%** | +28 pp |
| Cross-Year Coherence (CYC) | 100% | 100% | — |

> **Honest caveat.** These numbers come from the offline benchmark with the full BM25-hybrid + flashrank reranker enabled. The deployed backend currently runs vector-only retrieval (`SKIP_BM25_FETCH=1`) due to a Pinecone Serverless SDK bug — see [Known limitations](#known-limitations). Re-running the benchmark in production-equivalent mode is on the roadmap.

---

## Architecture

```
SEC EDGAR (.htm)
    │  httpx direct fetch — no sec-edgar-downloader dependency
    ▼
data/raw_filings/{TICKER}/{YEAR}/filing.htm
    │  LlamaParse cloud API — preserves Markdown table structure
    ▼
data/parsed_markdown/{TICKER}_{YEAR}.md       (committed to git, ~10 MB total)
    │
    ▼
Two parallel chunkers:
    Naive — fixed 512-token windows         → Pinecone namespace "naive"
    Structured — table-aware + metadata     → Pinecone namespace "structured"
                                                       │
                                                       ▼
                                  Query path (Smart mode):
                                  HyDE rewrite → Vector top-40 + BM25 top-40
                                  → Reciprocal Rank Fusion → flashrank top-10
                                  → Groq JSON-mode synthesis (llama-3.1-8b-instant)
                                  → optional deterministic calculators (gross margin)
                                  → value validation against retrieved context
```

The frontend is a Next.js 14 app with three pages: **Ask**, **Benchmark**, **Pipeline**.

---

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| LLM | Groq Cloud (`llama-3.1-8b-instant`) | Free tier, low latency, JSON-mode |
| Embeddings | `fastembed` (BAAI/bge-small-en-v1.5, ONNX) | No PyTorch dependency, runs on CPU |
| Reranker | `flashrank` (rank-T5-flan, ONNX) | Cross-encoder quality without GPU |
| Vector store | Pinecone Serverless (`us-east-1`) | Managed, persistent, fast cold reads |
| Document parsing | LlamaParse cloud | Best-in-class table preservation in Markdown |
| Orchestration | LlamaIndex 0.12.x | Standard RAG abstractions |
| Backend framework | FastAPI + uvicorn | Async, simple, typed |
| Backend host | Fly.io (`iad` region, 2 GB VM) | Co-located with Pinecone, auto-stop idle machines |
| Frontend framework | Next.js 14 (App Router) | SSR-friendly, fast iteration |
| Frontend host | Vercel | Native Next.js, free for hobby |
| Styling | Tailwind + shadcn/ui + lucide-react | Standard tooling, fast to build with |

---

## How the structured pipeline beats naive RAG

Three specific design choices drive the +40 pp TRA gap:

1. **Table-as-document chunking.** When the parser encounters a Markdown table, the whole table becomes a single chunk regardless of token count. Tables never split mid-row. Implemented in `app/benchmarks/structured_chunker.py`.
2. **Metadata-prefixed nodes.** Every chunk's `text` field begins with `Company: AAPL | Year: 2023 | Document: 10-K | Content: ...`. This buys both vector-space proximity (the embedding model treats year/ticker as salient) and downstream filter-ability without separate metadata calls.
3. **Hybrid retrieval with pre-filter.** When the question regex-matches a ticker or year, BM25 is rebuilt over just the scoped nodes before fusion. Prevents the AAPL table from being displaced by an MSFT table that happens to embed close in 384-dim space.

Production also runs a deterministic calculator for gross-margin questions (verbatim percent extraction from MD&A) before falling back to the LLM. This is the kind of pragmatic "if regex works, skip the LLM" shortcut that ships in real financial-AI products.

---

## Quick start

Prerequisites: Python 3.12, Node 18+, accounts at Pinecone, Groq, and LlamaParse (all have free tiers).

```bash
# Clone and install
git clone https://github.com/surendra-gvsr/sec-analyzer.git
cd sec-analyzer
python -m venv venv
venv/Scripts/activate              # PowerShell / Git-Bash on Windows
pip install -r requirements.txt
cp .env.example .env               # then fill in the four API keys

# One-time data pipeline (~45 min, $5–10 LlamaParse)
python scripts/download_filings.py
python scripts/parse_filings.py
python scripts/build_index.py --naive-only --force   # despite name, builds both namespaces

# Run the benchmark (re-scores from cached index, no rebuild needed)
python scripts/run_benchmark.py

# Backend (no --reload on Windows — file watcher deadlocks)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm install && npm run dev
# Visit http://localhost:3000/ask
```

---

## Deploy

| Layer | Command | Notes |
| --- | --- | --- |
| Backend → Fly | `~/.fly/bin/flyctl.exe deploy --remote-only --wait-timeout 600` | From project root. First build ~5–8 min, subsequent ~2–3 min |
| Frontend → Vercel | `cd frontend && npx vercel --prod --yes` | Required after every push — there is **no** GitHub auto-deploy |

Secrets on Fly: `fly secrets set PINECONE_API_KEY=... GROQ_API_KEY=... LLAMA_CLOUD_API_KEY=... SEC_USER_EMAIL=...`

---

## Project structure

```
sec_analyzer/
├── app/
│   ├── main.py                      # FastAPI app, /api/* routes
│   ├── endpoints.py                 # handler bodies
│   ├── models.py                    # Pydantic request/response types
│   ├── rag_utils.py                 # the 8 production RAG modules
│   ├── pipeline/
│   │   ├── sec_downloader.py        # EDGAR direct fetch
│   │   ├── llama_parser.py          # LlamaParse client + on-disk cache
│   │   └── query_engine.py          # Pinecone init, query dispatch
│   └── benchmarks/
│       ├── naive_chunker.py         # 512-token fixed-window baseline
│       ├── structured_chunker.py    # table-aware production chunker
│       └── evaluator.py             # 10-question benchmark harness
├── scripts/                         # download, parse, build-index, run-benchmark
├── data/parsed_markdown/            # committed Markdown (avoids re-paying LlamaParse)
├── data/benchmark_results.json      # committed; Benchmark page reads this
├── frontend/                        # Next.js 14 app
│   ├── app/                         # /ask, /benchmark, /pipeline pages
│   ├── components/                  # AnswerCard, EvidenceAccordion, BenchmarkTable, …
│   └── lib/                         # api.ts (relative BASE), types.ts
├── Dockerfile + .dockerignore       # production image
├── fly.toml                         # Fly deployment config
├── vercel.json                      # Vercel proxy rewrite to Fly
├── render.yaml                      # stale (Render decommissioned)
├── requirements.txt                 # pinned: llama-index-core 0.12.x, pinecone <7, etc.
└── CLAUDE.md                        # full operational notes
```

---

## Known limitations

This project ships honestly. If you're evaluating this for a hire decision, here is what *doesn't* work yet:

1. **BM25 hybrid retrieval is silently no-op in production.** The Pinecone Serverless v3 SDK returns 2790 IDs from `list(namespace="structured")` but `fetch()` returns 0 vectors for those same IDs. Root cause not yet diagnosed (likely namespace prefix or ID-format mismatch). `SKIP_BM25_FETCH=1` is set in `fly.toml` to avoid the wasted 8 s on every cold start. The published benchmark numbers describe local-dev configuration; production currently runs vector-only.
2. **Some numeric answers are off by orders of magnitude.** The live `/api/query` for "What was Microsoft's net income in 2023?" returns `$82 million USD` (actual: $72.4 B). Likely fallout from vector-only retrieval pulling a less-precise top chunk on questions where BM25 would have caught the canonical income-statement table. AAPL revenue queries return correct $383.3 B.
3. **Dataset is small.** 2 companies × 4 years = 8 filings. The architecture would extend to thousands of filings but has not been tested at that scale.
4. **No XBRL.** SEC publishes structured financial data as XBRL/iXBRL. This project parses the HTML 10-K with LlamaParse instead — appropriate for showing RAG quality wins, less appropriate as a production data pipeline.
5. **No real-time alerting.** Filings are downloaded manually via `scripts/download_filings.py`; no EDGAR webhook subscription.

These are listed as roadmap items, not as bugs I'm hiding.

---

## Roadmap

- [ ] Diagnose and fix the Pinecone `fetch()` empty-result bug; re-run benchmark
- [ ] Investigate the wrong-magnitude answer on numeric queries; harden value validation
- [ ] Expand dataset to top-10 large caps × 5 years (50 filings)
- [ ] Switch to XBRL-driven financial statements where available, fall back to RAG for prose
- [ ] EDGAR webhook subscription + Slack/email notification on new filings
- [ ] Sibling project: year-over-year semantic diff (`FilingsDelta`)

---

## Operational notes

Detailed deployment, environment variables, debugging tips, and the full list of critical constraints are in [`CLAUDE.md`](./CLAUDE.md). That file is the single source of truth for "how do I make a change without breaking production."

---

## Author

Built by Surendra Gvsr — engineering portfolio piece. Reach out if you're hiring for FinTech / RAG / equity-research engineering: gvsr32@gmail.com
