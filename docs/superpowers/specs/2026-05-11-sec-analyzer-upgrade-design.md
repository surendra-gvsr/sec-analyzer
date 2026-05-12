# SEC Analyzer Upgrade — Design Spec
**Date:** 2026-05-11  
**Status:** Approved

---

## Overview

Upgrade the SEC Filing Trend Analyzer from a single-file `index.html` frontend to a production-grade Next.js 14 app, deploy the frontend to Vercel, keep the FastAPI backend on Render, and bootstrap project tooling from `my-project-ui`.

---

## Goals

1. Copy project tooling (`.claude/`, `.husky/`, `.prettierrc`, `.secretlintrc.json`) from `C:\Users\gujju\my-project-ui` and run `graphify install` + `graphify claude install`.
2. Convert `index.html` → Next.js 14 TypeScript app with shadcn/ui inside `frontend/`.
3. Add streaming responses, loading stages, and query history sidebar to the Ask tab.
4. Add recharts-based visualizations: multi-year line/bar toggle, benchmark radar chart, confidence heatmaps.
5. Make the entire app fully mobile-responsive with a collapsible sidebar.
6. Code-review the entire frontend for quality and consistency.
7. Push to GitHub and deploy frontend to Vercel (API proxied to Render).

---

## Architecture

### Runtime split

| Layer | Host | Notes |
|---|---|---|
| FastAPI backend | Render | All heavy deps (ChromaDB, fastembed, flashrank, Groq). No changes to Python code. |
| Next.js frontend | Vercel | Calls `NEXT_PUBLIC_API_URL`. Rewrites `/api/*` → Render URL. |

### Repository layout

```
sec_analyzer/
├── app/                        ← Python FastAPI (unchanged)
├── scripts/                    ← Pipeline scripts (unchanged)
├── frontend/                   ← NEW: Next.js 14 app (Vercel target)
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            ← Redirects to /ask
│   │   ├── ask/page.tsx
│   │   ├── benchmark/page.tsx
│   │   └── pipeline/page.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── AppShell.tsx
│   │   ├── ask/
│   │   │   ├── QueryInput.tsx
│   │   │   ├── ModeSelector.tsx
│   │   │   ├── AnswerCard.tsx
│   │   │   ├── TrendCard.tsx
│   │   │   ├── EvidenceAccordion.tsx
│   │   │   ├── LoadingStages.tsx
│   │   │   └── QueryHistory.tsx
│   │   ├── benchmark/
│   │   │   ├── StatsGrid.tsx
│   │   │   ├── BenchmarkTable.tsx
│   │   │   ├── RadarChart.tsx
│   │   │   └── ConfidenceHeatmap.tsx
│   │   └── pipeline/
│   │       ├── DataStatusGrid.tsx
│   │       └── PipelineTriggers.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   ├── .env.local.example
│   └── next.config.ts
├── index.html                  ← Kept as Render fallback
├── vercel.json                 ← Vercel build config + API rewrites
├── render.yaml                 ← Backend on Render (unchanged)
├── .husky/                     ← Copied from my-project-ui
├── .prettierrc                 ← Copied from my-project-ui
└── .secretlintrc.json          ← Copied from my-project-ui
```

---

## Agent Pipeline

```
Orchestrator
│
├── [Phase 0]   Setup Agent        → copy tooling files + graphify install
│
├── [Agent F1]  Frontend Agent 1   → Next.js 14 scaffold (blocks F2)
│                                    3 tabs, shadcn/ui, TypeScript, API client
│
├── [Agent F2]  Frontend Agent 2   → streaming + query history (blocks F3)
│
├── [Agent F3]  Frontend Agent 3   → recharts visualizations (blocks F4)
│
├── [Agent F4]  Frontend Agent 4   → mobile responsive + collapsible sidebar
│
├── [Review]    Code Reviewer      → quality, consistency, coding standards
│
└── [Deploy]    Deploy Agent       → git init + GitHub push + vercel.json + Vercel deploy
```

---

## Frontend Spec

### Technology

- Next.js 14 (App Router)
- TypeScript (strict)
- shadcn/ui + Tailwind CSS
- recharts (replaces Chart.js CDN)
- Fetch API (no extra HTTP lib)

### API contract (unchanged endpoints)

| Method | Path | Used by |
|---|---|---|
| POST | `/api/query` | Ask tab — Smart/Basic/Compare modes |
| POST | `/api/query/compare` | Compare mode |
| GET | `/api/benchmark/results` | Benchmark tab |
| GET | `/api/pipeline/data-status` | Pipeline tab |
| POST | `/api/pipeline/download` | Pipeline tab |
| POST | `/api/pipeline/parse` | Pipeline tab |
| POST | `/api/pipeline/build-index` | Pipeline tab |
| GET | `/api/pipeline/status/{job_id}` | Pipeline polling |
| POST | `/api/benchmark/run` | Benchmark tab |

### Tabs

**Ask tab** (`/ask`)
- `QueryInput` with mode selector (Smart / Basic / Compare pills)
- Example question cards (pre-filled clickable prompts)
- `LoadingStages` — animated 4-step progress (Retrieving → Reranking → Synthesizing → Done)
- `AnswerCard` — big numeric display with confidence bar and source chip
- `TrendCard` — recharts LineChart/BarChart with toggle
- `EvidenceAccordion` — collapsible chunk viewer
- `QueryHistory` — sidebar panel with last 20 queries, click to replay

**Benchmark tab** (`/benchmark`)
- `StatsGrid` — TRA / ACS / CYC stat cards (vs naive baseline)
- `RadarChart` — TRA/ACS/CYC structured vs naive radar
- `ConfidenceHeatmap` — per-question confidence grid
- `BenchmarkTable` — 10-question detail table with pass/fail indicators

**Pipeline tab** (`/pipeline`)
- `DataStatusGrid` — per-ticker/year download/parse/index status dots
- `PipelineTriggers` — download / parse / build-index / run-benchmark buttons with job polling

### Mobile responsiveness

- Sidebar collapses to a drawer on `< 768px` with hamburger toggle
- All grids reflow to single column on mobile
- Chart height reduces on small screens

---

## GitHub + Vercel Setup

### `.gitignore` additions

```
venv/
data/raw_filings/
data/chroma_db/
.env
frontend/.next/
frontend/node_modules/
```

### `vercel.json`

```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/.next",
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://<RENDER_URL>/api/:path*" }
  ]
}
```

### Vercel env vars

- `NEXT_PUBLIC_API_URL` — Render backend URL (set in Vercel dashboard)
- `RENDER_API_URL` — Used in rewrites (same value, server-side only)

---

## Constraints & Rules

- Every frontend agent reads `.claude/rules/` before writing code
- `NEXT_PUBLIC_API_URL` env var for all API calls — no hardcoded URLs
- No `torch`, no heavy Python deps in `frontend/`
- `index.html` is kept untouched (Render fallback)
- Groq throttle / RAG internals are not touched
- Python backend code is read-only throughout this upgrade
