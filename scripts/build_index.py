#!/usr/bin/env python3
"""
CLI — Phase 3: Build the GraphRAG + naive ChromaDB indexes.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --force   # rebuild from scratch
    python scripts/build_index.py --naive-only
    python scripts/build_index.py --graph-only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.graph_builder import build_index, get_index_stats


def main():
    parser = argparse.ArgumentParser(description="Build GraphRAG and/or naive chunk indexes.")
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--years", nargs="+", type=int)
    parser.add_argument("--force", action="store_true", help="Rebuild even if index exists")
    parser.add_argument("--naive-only", action="store_true", help="Only build naive chunk index")
    parser.add_argument("--graph-only", action="store_true", help="Only build graph index")
    args = parser.parse_args()

    if not args.naive_only:
        print("Building PropertyGraphIndex…")
        build_index(tickers=args.tickers, years=args.years, force=args.force)
        stats = get_index_stats()
        print(f"Graph index ready: {stats['nodes']} nodes, {stats['edges']} edges")

    if not args.graph_only:
        print("\nBuilding naive chunk index…")
        from app.benchmarks.naive_chunker import build_naive_index
        count = build_naive_index(tickers=args.tickers, years=args.years, force=args.force)
        print(f"Naive index ready: {count} chunks")

        print("\nBuilding structured chunk index…")
        from app.benchmarks.structured_chunker import build_structured_index
        count = build_structured_index(tickers=args.tickers, years=args.years, force=args.force)
        print(f"Structured index ready: {count} chunks")


if __name__ == "__main__":
    main()
