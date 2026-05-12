#!/usr/bin/env python3
"""
CLI — Phase 2: Parse downloaded filings with LlamaParse.

Usage:
    python scripts/parse_filings.py
    python scripts/parse_filings.py --tickers AAPL --years 2022 2023
    python scripts/parse_filings.py --force   # re-parse even if cache exists
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.llama_parser import parse_all_filings, list_parsed


def main():
    parser = argparse.ArgumentParser(description="Parse SEC filings with LlamaParse.")
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--years", nargs="+", type=int)
    parser.add_argument("--force", action="store_true", help="Re-parse even if cached")
    args = parser.parse_args()

    print("Parsing filings with LlamaParse…")
    results = parse_all_filings(tickers=args.tickers, years=args.years, force=args.force)

    print(f"\nParsed {len(results)} filing(s).")
    print("\nAll parsed filings:")
    for ticker, years in list_parsed().items():
        print(f"  {ticker}: {years}")


if __name__ == "__main__":
    main()
