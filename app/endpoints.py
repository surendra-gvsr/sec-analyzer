"""
FastAPI route handlers.
All handlers are registered in main.py.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Dict

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
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
from app.pipeline import graph_builder, query_engine
from app.pipeline.llama_parser import list_parsed
from app.pipeline.sec_downloader import list_downloaded

log = logging.getLogger(__name__)

# In-memory job registry (sufficient for a portfolio demo)
_jobs: Dict[str, Dict] = {}


# ─── Health ──────────────────────────────────────────────────────────────────

def health_check() -> HealthResponse:
    stats = graph_builder.get_index_stats()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        index_ready=query_engine.is_ready(),
        graph_nodes=stats.get("nodes", 0),
        graph_edges=stats.get("edges", 0),
    )


# ─── Query ───────────────────────────────────────────────────────────────────

def _to_query_response(result, mode: str) -> QueryResponse:
    from app.models import StructuredAnswer
    structured = None
    if getattr(result, "structured", None):
        try:
            structured = StructuredAnswer(**result.structured)
        except Exception:
            structured = None
    return QueryResponse(
        answer=result.answer,
        source_nodes=result.source_nodes,
        graph_path=result.graph_path,
        latency_ms=result.latency_ms,
        mode=mode,
        structured=structured,
    )


def query_filings(req: QueryRequest) -> QueryResponse:
    if not query_engine.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Index not built yet. Go to the Pipeline tab and click 'Build Index' to get started.",
        )
    result = query_engine.query(req.question, mode=req.mode)
    return _to_query_response(result, result.mode)


def query_compare(req: QueryRequest) -> CompareResponse:
    if not query_engine.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Index not built yet. Go to the Pipeline tab and click 'Build Index' to get started.",
        )
    graph_result = query_engine.query(req.question, mode="graph")
    naive_result = query_engine.query(req.question, mode="naive")
    return CompareResponse(
        question=req.question,
        graph=_to_query_response(graph_result, "graph"),
        naive=_to_query_response(naive_result, "naive"),
    )


# ─── Pipeline ────────────────────────────────────────────────────────────────

def get_data_status() -> DataStatusResponse:
    return DataStatusResponse(
        downloaded=list_downloaded(),
        parsed=list_parsed(),
        index_stats=graph_builder.get_index_stats(),
    )


def _run_download(job_id: str, tickers, years, force):
    _jobs[job_id] = {"stage": "downloading", "progress": 0, "message": "Starting download…", "errors": []}
    try:
        from app.pipeline.sec_downloader import download_filings
        result = download_filings(tickers=tickers, years=years, force=force)
        count = sum(len(v) for v in result.values())
        _jobs[job_id] = {
            "stage": "done", "progress": 100,
            "message": f"Downloaded {count} filing(s).",
            "errors": [],
        }
    except Exception as exc:
        _jobs[job_id] = {"stage": "error", "progress": 0, "message": str(exc), "errors": [str(exc)]}


def trigger_download(req: PipelineRequest, background_tasks: BackgroundTasks) -> PipelineStatusResponse:
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_download, job_id, req.tickers, req.years, req.force)
    _jobs[job_id] = {"stage": "queued", "progress": 0, "message": "Download queued.", "errors": []}
    return PipelineStatusResponse(job_id=job_id, stage="queued", progress=0, message="Download queued.")


def _run_parse(job_id: str, tickers, years, force):
    _jobs[job_id] = {"stage": "parsing", "progress": 0, "message": "Starting LlamaParse…", "errors": []}
    try:
        from app.pipeline.llama_parser import parse_all_filings
        result = parse_all_filings(tickers=tickers, years=years, force=force)
        _jobs[job_id] = {
            "stage": "done", "progress": 100,
            "message": f"Parsed {len(result)} filing(s).",
            "errors": [],
        }
    except Exception as exc:
        _jobs[job_id] = {"stage": "error", "progress": 0, "message": str(exc), "errors": [str(exc)]}


def trigger_parse(req: PipelineRequest, background_tasks: BackgroundTasks) -> PipelineStatusResponse:
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_parse, job_id, req.tickers, req.years, req.force)
    _jobs[job_id] = {"stage": "queued", "progress": 0, "message": "Parse queued.", "errors": []}
    return PipelineStatusResponse(job_id=job_id, stage="queued", progress=0, message="Parse queued.")


def _run_build_index(job_id: str, tickers, years, force):
    _jobs[job_id] = {"stage": "indexing", "progress": 10, "message": "Building structured index…", "errors": []}
    try:
        from app.benchmarks.structured_chunker import build_structured_index
        from app.benchmarks.naive_chunker import build_naive_index

        structured_count = build_structured_index(tickers=tickers, years=years, force=force)
        _jobs[job_id]["progress"] = 60
        _jobs[job_id]["message"] = (
            f"Structured index done ({structured_count} chunks). Building naive index…"
        )

        naive_count = build_naive_index(tickers=tickers, years=years, force=force)
        _jobs[job_id]["progress"] = 90
        _jobs[job_id]["message"] = "Indexes uploaded to Pinecone. Initialising query engine…"

        query_engine.initialise(force=True)
        _jobs[job_id] = {
            "stage": "done", "progress": 100,
            "message": (
                f"Index built — {structured_count} structured chunks, "
                f"{naive_count} naive chunks uploaded to Pinecone."
            ),
            "errors": [],
        }
    except Exception as exc:
        _jobs[job_id] = {"stage": "error", "progress": 0, "message": str(exc), "errors": [str(exc)]}


def trigger_build_index(req: PipelineRequest, background_tasks: BackgroundTasks) -> PipelineStatusResponse:
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_build_index, job_id, req.tickers, req.years, req.force)
    _jobs[job_id] = {"stage": "queued", "progress": 0, "message": "Index build queued.", "errors": []}
    return PipelineStatusResponse(job_id=job_id, stage="queued", progress=0, message="Index build queued.")


def get_pipeline_status(job_id: str) -> PipelineStatusResponse:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")
    j = _jobs[job_id]
    return PipelineStatusResponse(
        job_id=job_id,
        stage=j["stage"],
        progress=j["progress"],
        message=j["message"],
        errors=j.get("errors", []),
    )


# ─── Benchmark ───────────────────────────────────────────────────────────────

def _run_benchmark_job(job_id: str):
    _jobs[job_id] = {"stage": "running", "progress": 0, "message": "Benchmark running…", "errors": []}
    try:
        from app.benchmarks.benchmark_runner import run_benchmark
        run_benchmark()
        _jobs[job_id] = {"stage": "done", "progress": 100, "message": "Benchmark complete.", "errors": []}
    except Exception as exc:
        _jobs[job_id] = {"stage": "error", "progress": 0, "message": str(exc), "errors": [str(exc)]}


def trigger_benchmark(background_tasks: BackgroundTasks) -> PipelineStatusResponse:
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_benchmark_job, job_id)
    _jobs[job_id] = {"stage": "queued", "progress": 0, "message": "Benchmark queued.", "errors": []}
    return PipelineStatusResponse(job_id=job_id, stage="queued", progress=0, message="Benchmark queued (~5 min).")


def get_benchmark_results() -> BenchmarkResultResponse:
    results_path = Path(settings.benchmark_results_path)
    if not results_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Benchmark results not found. Run POST /api/benchmark/run first.",
        )
    data = json.loads(results_path.read_text(encoding="utf-8"))
    return BenchmarkResultResponse(**data)
