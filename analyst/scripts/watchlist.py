#!/usr/bin/env python3
"""Track what you hold and what you are watching, and flag what needs a look.

The point of `check`: for every name on the list it compares the newest SEC
filing against the date of your last note. Anything that has filed since you
last wrote something down is work waiting for you. That is the difference
between a research tool and a research habit.

    python3 watchlist.py add MSFT --held --tag software
    python3 watchlist.py add KO --tag staples
    python3 watchlist.py list
    python3 watchlist.py check
    python3 watchlist.py remove KO
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

import edgar

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "watchlist.json"
NOTES = ROOT / "notes"
DATED_HEADING = re.compile(r"^#{1,3}\s*(\d{4}-\d{2}-\d{2})", re.M)


def load():
    if not LIST.exists():
        return {"positions": []}
    try:
        return json.loads(LIST.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{LIST} is not valid JSON ({e}). Fix or delete it.")


def save(d):
    LIST.write_text(json.dumps(d, indent=2) + "\n")


def find(d, ticker):
    return next((p for p in d["positions"] if p["ticker"] == ticker.upper()), None)


def last_reviewed(ticker):
    """The most recent dated heading in this company's note, if there is one."""
    f = NOTES / f"{ticker.upper()}.md"
    if not f.exists():
        return None
    found = DATED_HEADING.findall(f.read_text())
    return max(found) if found else None


def cmd_add(a):
    d = load()
    if find(d, a.ticker):
        sys.exit(f"{a.ticker.upper()} is already on the list. Use remove first to change it.")
    cik, name = edgar.resolve_cik(a.ticker)   # fails loudly on a bad ticker
    d["positions"].append({
        "ticker": a.ticker.upper(), "company": name, "cik": cik,
        "status": "held" if a.held else "watching",
        "tag": a.tag or "", "added": date.today().isoformat(),
    })
    d["positions"].sort(key=lambda p: p["ticker"])
    save(d)
    print(f"added {a.ticker.upper()} — {name} ({'held' if a.held else 'watching'})")


def cmd_remove(a):
    d = load()
    p = find(d, a.ticker)
    if not p:
        sys.exit(f"{a.ticker.upper()} is not on the list.")
    d["positions"].remove(p)
    save(d)
    print(f"removed {a.ticker.upper()}")


def cmd_list(a):
    d = load()
    if not d["positions"]:
        print("Watchlist is empty. Add one with:  python3 watchlist.py add MSFT --held")
        return
    print(f"{'ticker':<8}{'status':<10}{'tag':<14}{'last note':<12}company")
    for p in d["positions"]:
        print(f"{p['ticker']:<8}{p['status']:<10}{p.get('tag',''):<14}"
              f"{last_reviewed(p['ticker']) or '—':<12}{p['company']}")


def cmd_check(a):
    d = load()
    if not d["positions"]:
        print("Watchlist is empty.")
        return
    stale, current, never = [], [], []
    for p in d["positions"]:
        try:
            fl = edgar.recent_filings(p["ticker"], forms=("10-K", "10-Q", "8-K"), limit=1)
        except SystemExit as e:
            print(f"note: could not check {p['ticker']}: {e}", file=sys.stderr)
            continue
        newest = fl[0] if fl else None
        seen = last_reviewed(p["ticker"])
        row = (p, newest, seen)
        if seen is None:
            never.append(row)
        elif newest and newest["filed"] > seen:
            stale.append(row)
        else:
            current.append(row)

    if stale:
        print("Filed since your last note:\n")
        for p, f, seen in stale:
            print(f"  {p['ticker']:<6} {p['status']:<9} {f['form']:<5} filed {f['filed']} "
                  f"(your note: {seen})")
            print(f"         {f['url']}")
        print()
    if never:
        print("On the list but never analyzed:\n")
        for p, f, _ in never:
            latest = f"latest {f['form']} {f['filed']}" if f else "no filings found"
            print(f"  {p['ticker']:<6} {p['status']:<9} {latest}")
        print()
    if current:
        print("Up to date: " + ", ".join(p["ticker"] for p, _, _ in current))
    if not stale and not never:
        print("\nNothing needs attention.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add", help="add a company")
    a1.add_argument("ticker")
    a1.add_argument("--held", action="store_true", help="you own it, rather than watching it")
    a1.add_argument("--tag", help="free-form grouping, e.g. a sector")
    a1.set_defaults(fn=cmd_add)
    a2 = sub.add_parser("remove", help="remove a company")
    a2.add_argument("ticker")
    a2.set_defaults(fn=cmd_remove)
    sub.add_parser("list", help="show the watchlist").set_defaults(fn=cmd_list)
    sub.add_parser("check", help="flag anything that has filed since your last note").set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
