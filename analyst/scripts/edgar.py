#!/usr/bin/env python3
"""Fetch and cache SEC EDGAR company data.

EDGAR's XBRL API is free and needs no key, but it does require a User-Agent
header that identifies you, and it rate-limits at roughly 10 requests/second.
Set ANALYST_UA to "Your Name your@email.com" before using this.

    python3 edgar.py fetch AAPL          # download + cache company facts
    python3 edgar.py filings AAPL -n 5   # list recent 10-K / 10-Q with URLs
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
TICKER_TTL = 30 * 86400
FACTS_TTL = 86400


def user_agent() -> str:
    ua = os.environ.get("ANALYST_UA", "").strip()
    if not ua:
        sys.exit(
            "ANALYST_UA is not set. SEC EDGAR rejects requests that do not identify "
            'the caller.\n  export ANALYST_UA="Your Name your@email.com"'
        )
    return ua


def get_json(url: str, cache: Path, ttl: int, refresh: bool = False) -> dict:
    """Fetch JSON, serving from cache when it is younger than ttl seconds."""
    if cache.exists() and not refresh and (time.time() - cache.stat().st_mtime) < ttl:
        return json.loads(cache.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(),
                                               "Accept-Encoding": "gzip, deflate"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            sys.exit(f"EDGAR returned 403 — check that ANALYST_UA is a real name and email.\n  {url}")
        if e.code == 404:
            sys.exit(f"EDGAR has no data at {url}\n(Foreign issuers filing 20-F and funds often have no XBRL company facts.)")
        if e.code == 429:
            sys.exit("EDGAR rate-limited you (429). Wait a minute and retry.")
        raise
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(raw)
    return json.loads(raw)


def resolve_cik(ticker: str, refresh: bool = False) -> tuple[int, str]:
    """Map a ticker symbol to its CIK number and registered company name."""
    data = get_json(TICKERS_URL, DATA / "company_tickers.json", TICKER_TTL, refresh)
    want = ticker.upper().replace(".", "-")
    for row in data.values():
        if row["ticker"].upper() == want:
            return int(row["cik_str"]), row["title"]
    sys.exit(f"No CIK found for ticker {ticker!r}. It may be foreign-listed, an ETF, or delisted.")


def company_facts(ticker: str, refresh: bool = False) -> dict:
    """Every XBRL fact the company has ever reported, as EDGAR returns it."""
    cik, name = resolve_cik(ticker, refresh)
    facts = get_json(FACTS_URL.format(cik=cik), DATA / f"{ticker.upper()}_facts.json",
                     FACTS_TTL, refresh)
    facts["_ticker"], facts["_cik"], facts["_name"] = ticker.upper(), cik, name
    return facts


def recent_filings(ticker: str, forms=("10-K", "10-Q"), limit: int = 5, refresh: bool = False):
    """Recent filings with direct URLs, so the agent can go read the actual document."""
    cik, _ = resolve_cik(ticker, refresh)
    sub = get_json(SUBMISSIONS_URL.format(cik=cik), DATA / f"{ticker.upper()}_submissions.json",
                   FACTS_TTL, refresh)
    r = sub["filings"]["recent"]
    out = []
    for i, form in enumerate(r["form"]):
        if form not in forms:
            continue
        accn = r["accessionNumber"][i].replace("-", "")
        out.append({
            "form": form,
            "filed": r["filingDate"][i],
            "period": r["reportDate"][i],
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{r['primaryDocument'][i]}",
        })
        if len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download and cache company facts")
    f.add_argument("ticker")
    f.add_argument("--refresh", action="store_true", help="ignore cached copy")
    g = sub.add_parser("filings", help="list recent filings with URLs")
    g.add_argument("ticker")
    g.add_argument("-n", type=int, default=5)
    g.add_argument("--forms", default="10-K,10-Q")
    g.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    if a.cmd == "fetch":
        facts = company_facts(a.ticker, a.refresh)
        tags = facts["facts"].get("us-gaap", {})
        print(f"{facts['_name']} (CIK {facts['_cik']}) — {len(tags)} us-gaap tags cached")
        print(f"cached at {DATA / (a.ticker.upper() + '_facts.json')}")
    else:
        for x in recent_filings(a.ticker, tuple(a.forms.split(",")), a.n, a.refresh):
            print(f"{x['form']:6} filed {x['filed']}  period {x['period']}  {x['url']}")


if __name__ == "__main__":
    main()
