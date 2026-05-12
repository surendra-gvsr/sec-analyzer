"""
Phase 2 — LlamaParse cloud parsing.

Sends downloaded 10-K .htm files to the LlamaParse API and receives
structured Markdown back with tables preserved as pipe-delimited blocks.
Results are cached in data/parsed_markdown/{TICKER}_{YEAR}.md.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm

from app.config import settings
from app.pipeline.sec_downloader import get_filing_path, list_downloaded

log = logging.getLogger(__name__)

_PARSING_INSTRUCTION = (
    "This is an SEC 10-K annual report. "
    "Preserve all financial tables exactly as pipe-delimited Markdown tables — "
    "do not summarise or skip any rows. "
    "Use ## for major section headings (e.g. ## Risk Factors, ## Financial Statements). "
    "Treat footnotes as indented bullet points placed immediately after the table they annotate. "
    "Do not add commentary or interpretation."
)


def _cache_path(ticker: str, year: int) -> Path:
    return Path(settings.parsed_markdown_dir) / f"{ticker}_{year}.md"


def parse_filing(ticker: str, year: int, force: bool = False) -> Optional[str]:
    """
    Parse a single filing. Returns the Markdown string.
    Uses the local cache unless force=True.
    """
    cache = _cache_path(ticker, year)
    if cache.exists() and not force:
        log.info("Cache hit for %s %d.", ticker, year)
        return cache.read_text(encoding="utf-8")

    filing_path = get_filing_path(ticker, year)
    if not filing_path:
        log.warning("No downloaded filing for %s %d. Run download first.", ticker, year)
        return None

    try:
        from llama_parse import LlamaParse  # type: ignore
    except ImportError:
        raise RuntimeError("llama-parse is not installed. Run: pip install llama-parse")

    api_key = settings.llama_cloud_api_key
    if not api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY is not set in .env")

    log.info("Parsing %s %d via LlamaParse…", ticker, year)
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        parsing_instruction=_PARSING_INSTRUCTION,
        num_workers=1,       # stay within free-tier rate limits
        verbose=False,
    )

    documents = parser.load_data(str(filing_path))
    if not documents:
        log.warning("LlamaParse returned no documents for %s %d.", ticker, year)
        return None

    markdown = "\n\n".join(doc.text for doc in documents)

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(markdown, encoding="utf-8")
    log.info("Saved parsed Markdown → %s", cache)
    return markdown


def parse_all_filings(
    tickers: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    force: bool = False,
) -> Dict[Tuple[str, int], str]:
    """
    Parse all downloaded filings. Returns {(ticker, year): markdown_text}.
    """
    tickers = tickers or settings.tickers_list
    years = years or settings.years_list

    downloaded = list_downloaded()
    results: Dict[Tuple[str, int], str] = {}

    pairs = [
        (t, y)
        for t in tickers
        for y in years
        if y in downloaded.get(t, [])
    ]

    for ticker, year in tqdm(pairs, desc="Parsing filings"):
        md = parse_filing(ticker, year, force=force)
        if md:
            results[(ticker, year)] = md

    return results


def get_parsed_markdown(ticker: str, year: int) -> Optional[str]:
    """Return cached Markdown for a filing, or None if not yet parsed."""
    p = _cache_path(ticker, year)
    return p.read_text(encoding="utf-8") if p.exists() else None


def list_parsed() -> Dict[str, List[int]]:
    """Return {ticker: [years]} for all filings with cached Markdown."""
    base = Path(settings.parsed_markdown_dir)
    out: Dict[str, List[int]] = {}
    if not base.exists():
        return out
    for f in base.glob("*.md"):
        parts = f.stem.split("_")
        if len(parts) == 2:
            ticker, year_str = parts
            try:
                out.setdefault(ticker, []).append(int(year_str))
            except ValueError:
                pass
    return {k: sorted(v) for k, v in out.items()}
