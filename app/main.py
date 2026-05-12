from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.logging_config import setup_logging
from app.models import (
    BenchmarkResultResponse,
    CompareResponse,
    DataStatusResponse,
    HealthResponse,
    PipelineRequest,
    PipelineStatusResponse,
    QueryRequest,
    QueryResponse,
)
from app.endpoints import (
    get_benchmark_results,
    get_data_status,
    get_pipeline_status,
    health_check,
    query_compare,
    query_filings,
    trigger_benchmark,
    trigger_build_index,
    trigger_download,
    trigger_parse,
)

setup_logging()
log = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Year SEC Filing Trend Analyzer",
    description=(
        "GraphRAG system for cross-year SEC 10-K analysis. "
        "Demonstrates structure-aware chunking vs naive RAG for financial table retrieval."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from app.pipeline import query_engine
    log.info("Starting SEC Analyzer…")
    ok = query_engine.initialise()
    if ok:
        log.info("GraphRAG index loaded successfully.")
    else:
        log.warning(
            "Graph index not found — API will serve limited functionality until "
            "POST /api/pipeline/build-index is called."
        )


# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    index_path = Path("index.html")
    if not index_path.exists():
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    return FileResponse(str(index_path), headers={"Cache-Control": "no-cache"})


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    return health_check()


# ─── Query ────────────────────────────────────────────────────────────────────

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def query(req: QueryRequest):
    """Query the GraphRAG engine (mode=graph) or naive vector index (mode=naive)."""
    return query_filings(req)


@app.post("/api/query/compare", response_model=CompareResponse, tags=["Query"])
async def compare(req: QueryRequest):
    """Run the same question through both modes and return side-by-side answers."""
    return query_compare(req)


# ─── Pipeline ─────────────────────────────────────────────────────────────────

@app.get("/api/pipeline/data-status", response_model=DataStatusResponse, tags=["Pipeline"])
async def data_status():
    """Return which tickers/years have been downloaded, parsed, and indexed."""
    return get_data_status()


@app.post("/api/pipeline/download", response_model=PipelineStatusResponse, tags=["Pipeline"])
async def download(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Trigger SEC EDGAR 10-K download for the specified tickers and years."""
    return trigger_download(req, background_tasks)


@app.post("/api/pipeline/parse", response_model=PipelineStatusResponse, tags=["Pipeline"])
async def parse(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Trigger LlamaParse structure-aware parsing on downloaded filings."""
    return trigger_parse(req, background_tasks)


@app.post("/api/pipeline/build-index", response_model=PipelineStatusResponse, tags=["Pipeline"])
async def build_index(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Build (or rebuild) the PropertyGraphIndex + ChromaDB indexes."""
    return trigger_build_index(req, background_tasks)


@app.get("/api/pipeline/status/{job_id}", response_model=PipelineStatusResponse, tags=["Pipeline"])
async def pipeline_status(job_id: str):
    """Poll job status for any pipeline stage."""
    return get_pipeline_status(job_id)


# ─── Benchmark ────────────────────────────────────────────────────────────────

@app.post("/api/benchmark/run", response_model=PipelineStatusResponse, tags=["Benchmark"])
async def benchmark_run(background_tasks: BackgroundTasks):
    """Run the full 10-question benchmark (naive vs structured). Takes ~5 minutes."""
    return trigger_benchmark(background_tasks)


@app.get("/api/benchmark/results", response_model=BenchmarkResultResponse, tags=["Benchmark"])
async def benchmark_results():
    """Return the latest benchmark results (pre-built results served on cold start)."""
    return get_benchmark_results()
