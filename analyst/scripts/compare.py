#!/usr/bin/env python3
"""Put several companies side by side on the same metrics.

An absolute multiple means very little on its own. A 30x P/E is cheap for one
business and rich for another, and the only way to tell is to line the
comparable companies up on identical, consistently computed figures.

    python3 compare.py AAPL MSFT GOOGL
    python3 compare.py KO PEP --no-prices        # skip the price lookup
    python3 compare.py NVDA AMD --json
"""
import argparse, json, sys

import metrics
from metrics import usd, pct, mult

# (label, where it lives, key, formatter)
ROWS = [
    ("Revenue (TTM)",     "ttm",     "revenue",          usd),
    ("Gross margin",      "derived", "gross_margin",     pct),
    ("Operating margin",  "derived", "operating_margin", pct),
    ("Net margin",        "derived", "net_margin",       pct),
    ("FCF margin",        "derived", "fcf_margin",       pct),
    ("Revenue growth",    "derived", "revenue_growth_latest", pct),
    ("Revenue CAGR",      "derived", "revenue_cagr",     pct),
    ("Return on equity",  "derived", "return_on_equity", pct),
    ("Current ratio",     "derived", "current_ratio",    mult),
    ("Debt / equity",     "derived", "debt_to_equity",   mult),
    ("Net cash (debt)",   "derived", "net_cash",         usd),
    ("Market cap",        "derived", "market_cap",       usd),
    ("P/E (TTM)",         "derived", "pe_ttm",           mult),
    ("P/S (TTM)",         "derived", "ps_ttm",           mult),
    ("EV/EBIT",           "derived", "ev_ebit",          mult),
    ("FCF yield",         "derived", "fcf_yield",        pct),
]


def cell(m, where, key, fmt):
    if where == "ttm":
        v = m["ttm"].get(key, {}).get("value")
    else:
        v = m["derived"].get(key)
    return fmt(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--no-prices", action="store_true", help="skip quotes; omits valuation rows")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    if len(a.tickers) > 8:
        sys.exit("Comparing more than 8 companies makes the table unreadable.")

    prices = {}
    if not a.no_prices:
        import prices as px
        for t in a.tickers:
            try:
                prices[t.upper()] = px.quote(t)["price"]
            except RuntimeError as e:
                print(f"note: {e}", file=sys.stderr)

    built = {}
    for t in a.tickers:
        try:
            built[t.upper()] = metrics.build(t, a.years, prices.get(t.upper()), a.refresh)
        except SystemExit as e:
            print(f"skipping {t.upper()}: {e}", file=sys.stderr)

    if not built:
        sys.exit("No companies could be analyzed.")
    if a.json:
        print(json.dumps(built, indent=2))
        return

    names = list(built)
    w = max(18, *(len(n) for n in names)) + 2
    print("| Metric | " + " | ".join(names) + " |")
    print("|---|" + "---:|" * len(names))
    for label, where, key, fmt in ROWS:
        cells = [cell(built[n], where, key, fmt) for n in names]
        if all(c == "Not disclosed" for c in cells):
            continue  # a row nobody reports is noise, not information
        print(f"| {label} | " + " | ".join(cells) + " |")

    print()
    for n in names:
        m = built[n]
        p = m["derived"].get("price")
        asof = next(iter(m["ttm"].values()))["through"] if m["ttm"] else "n/a"
        print(f"{n}: {m['company']} — TTM through {asof}" + (f", price ${p:,.2f}" if p else ""))

    warned = {n: built[n]["warnings"] for n in names if built[n]["warnings"]}
    if warned:
        print("\nWarnings:")
        for n, ws in warned.items():
            for x in ws:
                print(f"  {n}: {x}")


if __name__ == "__main__":
    main()
