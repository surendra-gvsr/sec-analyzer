#!/usr/bin/env python3
"""
CLI — Phase 4: Run the benchmark and print the comparison table.

Usage:
    python scripts/run_benchmark.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app.benchmarks.benchmark_runner import run_benchmark

if __name__ == "__main__":
    print("Running benchmark — this will take ~5 minutes (10 questions × 2 engines)…\n")
    results = run_benchmark()
    print(f"\nResults saved to: data/benchmark_results.json")
    print(f"Serve the app and visit Tab 2 to see the interactive comparison table.")
