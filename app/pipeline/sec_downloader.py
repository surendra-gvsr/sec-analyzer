"""
Phase 1 — SEC EDGAR downloader (direct HTTP).

Fetches 10-K filings directly from data.sec.gov using httpx. This avoids the
sec-edgar-downloader dependency hell and gives us full control over the
User-Agent header (SEC requires a real email, otherwise returns 403).

Pipeline:
  1. Look up CIK for each ticker via company_tickers.json
  2. Fetch submissions JSON at data.sec.gov/submissions/CIK{cik}.json
  3. Filter for 10-K filings in the requested fiscal years
  4. Download the primary HTML document for each filing
  5. Save to data/raw_filings/{TICKER}/{YEAR}/filing.htm
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from tqdm import tqdm

from app.config import settings

log = logging.getLogger(__name__)

# SEC requires User-Agent in format "Name <email@example.com>" or similar.
# Hits over 10 req/sec get throttled — we sleep 0.15s between requests.
_REQUEST_DELAY = 0.15
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_doc}"


def _user_agent() -> str:
    return f"{settings.sec_company_name} {settings.sec_user_email}"


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": _user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov",
    }


def _data_headers() -> Dict[str, str]:
    return {
        "User-Agent": _user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }


_ticker_to_cik_cache: Optional[Dict[str, int]] = None


def _get_ticker_to_cik() -> Dict[str, int]:
    global _ticker_to_cik_cache
    if _ticker_to_cik_cache is not None:
        return _ticker_to_cik_cache

    log.info("Fetching ticker → CIK mapping from SEC…")
    with httpx.Client(timeout=30.0, headers=_headers()) as client:
        resp = client.get(_TICKER_MAP_URL)
        resp.raise_for_status()
        data = resp.json()

    mapping = {}
    for _, entry in data.items():
        ticker = entry["ticker"].upper()
        cik = int(entry["cik_str"])
        mapping[ticker] = cik

    _ticker_to_cik_cache = mapping
    log.info("Loaded %d ticker mappings.", len(mapping))
    return mapping


def _fetch_submissions(cik: int) -> Dict:
    url = _SUBMISSIONS_URL.format(cik=cik)
    with httpx.Client(timeout=30.0, headers=_data_headers()) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _find_10k_filings(submissions: Dict, target_years: List[int]) -> List[Dict]:
    """
    Find 10-K filings whose fiscal year (reportDate) falls in target_years.
    Returns list of {accession, filing_date, report_date, primary_doc}.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    primary_docs = recent.get("primaryDocument", [])

    found = []
    for i, form in enumerate(forms):
        if form != "10-K":
            continue
        report_date = report_dates[i] if i < len(report_dates) else ""
        if not report_date:
            continue
        try:
            report_year = int(report_date.split("-")[0])
        except (ValueError, IndexError):
            continue
        if report_year not in target_years:
            continue
        found.append({
            "fiscal_year": report_year,
            "accession": accessions[i],
            "filing_date": filing_dates[i],
            "report_date": report_date,
            "primary_doc": primary_docs[i],
        })
    return found


def _download_filing(cik: int, accession: str, primary_doc: str, dest: Path) -> bool:
    accession_clean = accession.replace("-", "")
    url = _ARCHIVE_URL.format(cik=cik, accession_clean=accession_clean, primary_doc=primary_doc)

    with httpx.Client(timeout=120.0, headers=_headers(), follow_redirects=True) as client:
        try:
            resp = client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            log.error("Failed to download %s: %s", url, exc)
            return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return True


def download_filings(
    tickers: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    force: bool = False,
) -> Dict[str, Dict[int, Path]]:
    """
    Download 10-K filings for each (ticker, year) pair via SEC EDGAR direct HTTP.
    Returns {ticker: {year: Path}}.
    """
    tickers = tickers or settings.tickers_list
    years = years or settings.years_list

    base_dir = Path(settings.raw_filings_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    if not settings.sec_user_email or "@" not in settings.sec_user_email:
        raise RuntimeError(
            "SEC_USER_EMAIL must be set to a real email in .env "
            "(SEC EDGAR requires it in the User-Agent header)."
        )

    ticker_map = _get_ticker_to_cik()
    result: Dict[str, Dict[int, Path]] = {}

    for ticker in tqdm(tickers, desc="Tickers"):
        result[ticker] = {}
        ticker = ticker.upper()
        if ticker not in ticker_map:
            log.error("Ticker %s not found in SEC mapping.", ticker)
            continue
        cik = ticker_map[ticker]

        # Check cache first
        years_to_fetch = []
        for year in years:
            dest = base_dir / ticker / str(year) / "filing.htm"
            if dest.exists() and not force:
                log.info("Already downloaded %s %d, skipping.", ticker, year)
                result[ticker][year] = dest
            else:
                years_to_fetch.append(year)

        if not years_to_fetch:
            continue

        log.info("Fetching submissions for %s (CIK=%d)…", ticker, cik)
        try:
            submissions = _fetch_submissions(cik)
        except Exception as exc:
            log.error("Failed to fetch submissions for %s: %s", ticker, exc)
            continue
        time.sleep(_REQUEST_DELAY)

        filings = _find_10k_filings(submissions, years_to_fetch)
        log.info("  Found %d matching 10-K filings.", len(filings))

        for filing in filings:
            year = filing["fiscal_year"]
            dest = base_dir / ticker / str(year) / "filing.htm"
            log.info("  Downloading %s %d (%s)…", ticker, year, filing["accession"])
            if _download_filing(cik, filing["accession"], filing["primary_doc"], dest):
                log.info("  Saved → %s", dest)
                result[ticker][year] = dest
            time.sleep(_REQUEST_DELAY)

    return result


def get_filing_path(ticker: str, year: int) -> Optional[Path]:
    p = Path(settings.raw_filings_dir) / ticker / str(year) / "filing.htm"
    return p if p.exists() else None


def list_downloaded() -> Dict[str, List[int]]:
    base = Path(settings.raw_filings_dir)
    out: Dict[str, List[int]] = {}
    if not base.exists():
        return out
    for ticker_dir in base.iterdir():
        if not ticker_dir.is_dir() or ticker_dir.name.startswith("_"):
            continue
        years = []
        for year_dir in ticker_dir.iterdir():
            if year_dir.is_dir() and (year_dir / "filing.htm").exists():
                try:
                    years.append(int(year_dir.name))
                except ValueError:
                    pass
        if years:
            out[ticker_dir.name] = sorted(years)
    return out
