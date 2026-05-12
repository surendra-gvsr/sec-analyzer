"""
Benchmark runner — orchestrates both pipelines and produces the comparison table.

Runs all BENCHMARK_QUESTIONS through both the naive and structured-chunk query
engines, scores each answer, and writes the results to data/benchmark_results.json.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from app.benchmarks.evaluator import (
    BENCHMARK_QUESTIONS,
    compute_summary,
    score_acs,
    score_cyc,
    score_tra,
)
from app.benchmarks.naive_chunker import query_naive
from app.benchmarks.structured_chunker import query_structured, query_structured_json
from app.config import settings

log = logging.getLogger(__name__)


def run_benchmark(questions: List[Dict] = None) -> Dict:
    """
    Run all benchmark questions through naive and structured query engines.
    Returns the full results dict and also writes it to benchmark_results.json.
    """
    questions = questions or BENCHMARK_QUESTIONS
    results: List[Dict] = []

    for i, q in enumerate(questions, 1):
        log.info("[%d/%d] %s: %s", i, len(questions), q["id"], q["question"][:60])

        # ── Naive query ──────────────────────────────────────────────────────
        t0 = time.perf_counter()
        try:
            naive_answer, naive_nodes = query_naive(q["question"])
        except Exception as exc:
            log.error("Naive query failed for %s: %s", q["id"], exc)
            naive_answer = f"Error: {exc}"
            naive_nodes = []
        naive_latency = round((time.perf_counter() - t0) * 1000, 1)

        # ── Structured query (JSON-mode for numeric questions) ──────────────
        t0 = time.perf_counter()
        struct_json: Dict = {}
        is_numeric = q.get("expected_value") is not None
        try:
            if is_numeric:
                struct_answer, struct_nodes, struct_json = query_structured_json(q["question"])
            else:
                struct_answer, struct_nodes = query_structured(q["question"])
        except Exception as exc:
            log.error("Structured query failed for %s: %s", q["id"], exc)
            struct_answer = f"Error: {exc}"
            struct_nodes = []
        struct_latency = round((time.perf_counter() - t0) * 1000, 1)

        # When JSON mode succeeded, augment the prose answer with the exact value
        # so the existing ACS scorer (which extracts numbers from text) finds it.
        if struct_json.get("value") is not None:
            try:
                val_f = float(str(struct_json["value"]).replace(",", ""))
                # Preserve decimals (e.g. 43.3 for percentages); drop .0 for integers
                clean_str = f"{int(val_f)}" if val_f == int(val_f) else f"{val_f}"
                unit_str = struct_json.get("unit") or ""
                struct_answer = f"{clean_str} {unit_str}. {struct_answer}".strip()
            except (ValueError, TypeError):
                pass

        # ── Score ────────────────────────────────────────────────────────────
        result_entry = {
            "question_id": q["id"],
            "question": q["question"],
            "type": q["type"],
            "ticker": q["ticker"],
            "years": q["years"],
            "expected_value": q.get("expected_value"),
            "naive": {
                "answer": naive_answer,
                "tra": score_tra(q, naive_nodes),
                "acs": score_acs(q, naive_answer),
                "cyc": score_cyc(q, naive_answer),
                "latency_ms": naive_latency,
                "retrieved_chunks": len(naive_nodes),
                "table_in_context": any("|" in n.get("text", "") for n in naive_nodes),
            },
            "structured": {
                "answer": struct_answer,
                "tra": score_tra(q, struct_nodes),
                "acs": score_acs(q, struct_answer),
                "cyc": score_cyc(q, struct_answer),
                "latency_ms": struct_latency,
                "retrieved_chunks": len(struct_nodes),
                "table_in_context": any(n.get("metadata", {}).get("has_table") for n in struct_nodes),
            },
        }
        results.append(result_entry)
        log.info(
            "  naive TRA=%d ACS=%s | structured TRA=%d ACS=%s",
            result_entry["naive"]["tra"],
            result_entry["naive"]["acs"],
            result_entry["structured"]["tra"],
            result_entry["structured"]["acs"],
        )

    summary = compute_summary(results)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(results),
        "summary": summary,
        "results": results,
    }

    out_path = Path(settings.benchmark_results_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log.info("Benchmark results written → %s", out_path)

    _print_summary_table(summary)
    return output


def _print_summary_table(summary: Dict) -> None:
    """Print the recruiter-hook comparison table to stdout."""
    print("\n" + "=" * 65)
    print("  BENCHMARK RESULTS — Structure-Aware vs Naive RAG")
    print("=" * 65)
    fmt = "{:<35} {:>10} {:>10} {:>8}"
    print(fmt.format("Metric", "Naive RAG", "GraphRAG", "Delta"))
    print("-" * 65)
    print(fmt.format(
        "Table Retrieval Accuracy (TRA)",
        f"{summary['naive_tra']:.0%}",
        f"{summary['structured_tra']:.0%}",
        f"+{summary['improvement_tra_pct']:.0f}%",
    ))
    print(fmt.format(
        "Answer Correctness Score (ACS)",
        f"{summary['naive_acs']:.0%}",
        f"{summary['structured_acs']:.0%}",
        f"+{summary['improvement_acs_pct']:.0f}%",
    ))
    print(fmt.format(
        "Cross-Year Coherence (CYC)",
        f"{summary['naive_cyc']:.0%}",
        f"{summary['structured_cyc']:.0%}",
        f"+{summary['improvement_cyc_pct']:.0f}%",
    ))
    print(fmt.format(
        "Avg Latency (ms)",
        f"{summary['naive_avg_latency_ms']:.0f}",
        f"{summary['structured_avg_latency_ms']:.0f}",
        "—",
    ))
    print("=" * 65 + "\n")
