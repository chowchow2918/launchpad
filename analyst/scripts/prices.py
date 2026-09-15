#!/usr/bin/env python3
"""Current share price, used only to turn filed fundamentals into multiples.

There is no free, keyless, officially supported quote API. This uses Yahoo's
chart endpoint, which is undocumented and unsupported — it works today and may
stop without notice. When it fails, pass the price by hand instead:

    python3 metrics.py AAPL --price 245.30

Usage:
    python3 prices.py AAPL
    python3 prices.py AAPL MSFT KO
"""
import argparse, json, sys, urllib.error, urllib.request

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"


def quote(symbol: str) -> dict:
    req = urllib.request.Request(CHART.format(sym=symbol.upper()),
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            meta = json.load(r)["chart"]["result"][0]["meta"]
    except (urllib.error.URLError, KeyError, TypeError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(
            f"Could not read a price for {symbol}: {e}. "
            "Pass it manually with metrics.py --price instead."
        ) from e
    return {
        "symbol": meta.get("symbol", symbol.upper()),
        "price": meta.get("regularMarketPrice"),
        "currency": meta.get("currency"),
        "change_pct": meta.get("regularMarketChangePercent"),
        "exchange": meta.get("fullExchangeName"),
        "source": "Yahoo Finance chart endpoint (unofficial)",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    out, failed = [], False
    for t in a.tickers:
        try:
            out.append(quote(t))
        except RuntimeError as e:
            print(e, file=sys.stderr)
            failed = True
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        for q in out:
            chg = f"{q['change_pct']:+.2f}%" if q.get("change_pct") is not None else "n/a"
            print(f"{q['symbol']:6} {q['price']:>12,.2f} {q['currency']}  {chg:>8}  {q['exchange']}")
    sys.exit(1 if failed and not out else 0)


if __name__ == "__main__":
    main()
