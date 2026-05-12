from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional  # noqa

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    mode: Literal["graph", "naive"] = "graph"


class StructuredAnswer(BaseModel):
    """Optional structured payload populated when the query was numeric or a trend."""
    kind: Literal["value", "trend", "qualitative"] = "qualitative"
    # Single-value answers (numeric questions)
    value: Optional[float] = None
    unit: Optional[str] = None
    year: Optional[int] = None
    ticker: Optional[str] = None
    metric: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 0.0   # 0..1
    # Trend answers — per-year series for charting
    series: List[Dict[str, Any]] = []


class QueryResponse(BaseModel):
    answer: str
    source_nodes: List[Dict[str, Any]] = []
    graph_path: List[str] = []
    latency_ms: float
    mode: str
    structured: Optional[StructuredAnswer] = None


class CompareResponse(BaseModel):
    question: str
    graph: QueryResponse
    naive: QueryResponse


class PipelineRequest(BaseModel):
    tickers: Optional[List[str]] = None
    years: Optional[List[int]] = None
    force: bool = False


class PipelineStatusResponse(BaseModel):
    job_id: str
    stage: str
    progress: int
    message: str
    errors: List[str] = []


class DataStatusResponse(BaseModel):
    downloaded: Dict[str, List[int]]
    parsed: Dict[str, List[int]]
    index_stats: Dict[str, Any]


class BenchmarkResultResponse(BaseModel):
    generated_at: str
    total_questions: int
    summary: Dict[str, Any]
    results: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    environment: str
    index_ready: bool
    graph_nodes: int
    graph_edges: int
