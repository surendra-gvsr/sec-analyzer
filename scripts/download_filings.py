#!/usr/bin/env python3
"""
CLI — Phase 1: Download SEC 10-K filings.

Usage:
    python scripts/download_filings.py
    python scripts/download_filings.py --tickers AAPL MSFT --years 2022 2023
    python scripts/download_filings.py --force
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.sec_downloader import download_filings, list_downloaded


def main():
    parser = argparse.ArgumentParser(description="Download SEC 10-K filings from EDGAR.")
    parser.add_argument("--tickers", nargs="+", help="Ticker symbols (default: from .env)")
    parser.add_argument("--years", nargs="+", type=int, help="Fiscal years (default: from .env)")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    print("Downloading 10-K filings…")
    result = download_filings(tickers=args.tickers, years=args.years, force=args.force)

    print("\nDownload summary:")
    for ticker, year_map in result.items():
        for year, path in year_map.items():
            print(f"  {ticker} {year} → {path}")

    print("\nAll downloaded filings:")
    for ticker, years in list_downloaded().items():
        print(f"  {ticker}: {years}")


if __name__ == "__main__":
    main()
