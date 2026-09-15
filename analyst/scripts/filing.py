#!/usr/bin/env python3
"""Download an SEC filing and pull readable text out of it.

A 10-K is well over a megabyte of inline-XBRL HTML, most of it markup. This
strips it to text and extracts the section you asked for, so the parts worth
reading -- MD&A, risk factors -- arrive at a size you can actually read.

    python3 filing.py AAPL --list                 # sections in the latest 10-K
    python3 filing.py AAPL --section mda          # management's discussion
    python3 filing.py AAPL --section risk
    python3 filing.py AAPL --form 10-Q --section mda
    python3 filing.py AAPL --section mda --out mda.txt
"""
import argparse, html, re, sys, urllib.request
from pathlib import Path

import edgar

CACHE = Path(__file__).resolve().parent.parent / "data" / "filings"

# Each section is (start patterns, end patterns). Filings vary in how they
# punctuate headings, so these match loosely and the span logic sorts it out.
ITEM = r"(?im)^\s*Item\s+{n}\b[\.\:\s—–\-]*"
SECTIONS_10K = {
    "business":    ([ITEM.format(n="1")],  [ITEM.format(n="1A")]),
    "risk":        ([ITEM.format(n="1A")], [ITEM.format(n="1B"), ITEM.format(n="2")]),
    "properties":  ([ITEM.format(n="2")],  [ITEM.format(n="3")]),
    "legal":       ([ITEM.format(n="3")],  [ITEM.format(n="4")]),
    "mda":         ([ITEM.format(n="7")],  [ITEM.format(n="7A"), ITEM.format(n="8")]),
    "market-risk": ([ITEM.format(n="7A")], [ITEM.format(n="8")]),
    "financials":  ([ITEM.format(n="8")],  [ITEM.format(n="9")]),
    "controls":    ([ITEM.format(n="9A")], [ITEM.format(n="9B"), ITEM.format(n="10")]),
}
SECTIONS_10Q = {
    "financials": ([ITEM.format(n="1")],  [ITEM.format(n="2")]),
    "mda":        ([ITEM.format(n="2")],  [ITEM.format(n="3")]),
    "market-risk":([ITEM.format(n="3")],  [ITEM.format(n="4")]),
    "controls":   ([ITEM.format(n="4")],  [r"(?im)^\s*Part\s+II", ITEM.format(n="1A"),
                                           ITEM.format(n="5"), ITEM.format(n="6")]),
    "legal":      ([r"(?im)^\s*Part\s+II.{0,200}?" + ITEM.format(n="1")[6:]], [ITEM.format(n="1A")]),
    "risk":       ([ITEM.format(n="1A")], [ITEM.format(n="2"), ITEM.format(n="5")]),
}


def to_text(raw: str) -> str:
    """HTML to plain text, preserving paragraph breaks and dropping markup."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    s = re.sub(r"(?is)<(br|/p|/div|/tr|/h[1-6]|/li)[^>]*>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def find_span(text, start_pats, end_pats):
    """Locate a section, skipping the table of contents.

    Every item heading appears at least twice: once in the TOC and once at the
    real section. In the TOC the next heading follows within a few dozen
    characters, so the correct span is simply the longest one.
    """
    starts = [m.end() for p in start_pats for m in re.finditer(p, text)]
    ends = [m.start() for p in end_pats for m in re.finditer(p, text)]
    if not starts:
        return None
    best = None
    for s in starts:
        after = [e for e in ends if e > s]
        stop = min(after) if after else len(text)
        if best is None or (stop - s) > (best[1] - best[0]):
            best = (s, stop)
    return best if best and (best[1] - best[0]) > 150 else None


def fetch(ticker, form="10-K", index=0, refresh=False):
    """Download the primary document of a recent filing, caching the HTML."""
    fl = edgar.recent_filings(ticker, forms=(form,), limit=index + 1, refresh=refresh)
    if len(fl) <= index:
        sys.exit(f"No {form} found for {ticker} at position {index}.")
    f = fl[index]
    cache = CACHE / f"{ticker.upper()}_{form.replace('/', '')}_{f['period']}.htm"
    if cache.exists() and not refresh:
        return f, cache.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(f["url"], headers={"User-Agent": edgar.user_agent()})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8", errors="replace")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(raw, encoding="utf-8")
    return f, raw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--form", default="10-K", help="10-K (default), 10-Q, 8-K")
    ap.add_argument("--index", type=int, default=0, help="0 = most recent, 1 = the one before")
    ap.add_argument("--section", help="business, risk, mda, market-risk, financials, controls, legal")
    ap.add_argument("--list", action="store_true", help="show which sections were found, and their size")
    ap.add_argument("--chars", type=int, default=0, help="truncate output to this many characters")
    ap.add_argument("--out", help="write to a file instead of stdout")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    meta, raw = fetch(a.ticker, a.form, a.index, a.refresh)
    text = to_text(raw)
    table = SECTIONS_10Q if a.form.upper().startswith("10-Q") else SECTIONS_10K
    header = f"{a.ticker.upper()} {meta['form']} — period {meta['period']}, filed {meta['filed']}\n{meta['url']}"

    if a.list:
        print(header + "\n")
        print(f"{'section':<12} {'chars':>9}  note")
        crossref = False
        for name, (sp, ep) in table.items():
            span = find_span(text, sp, ep)
            if not span:
                print(f"{name:<12} {'not found':>9}")
                continue
            n = span[1] - span[0]
            # Filings may satisfy an item by pointing at an exhibit or at page
            # numbers elsewhere. That is a real section, but not the content.
            note = "likely a cross-reference — read the full text" if n < 1000 else ""
            crossref |= bool(note)
            print(f"{name:<12} {n:>9,}  {note}")
        print(f"\n{'full text':<12} {len(text):>9,}")
        if crossref:
            print("\nSome items incorporate their content by reference (common for banks and "
                  "insurers).\nFor those, drop --section and read the full text, or fetch the "
                  "exhibit the item names.")
        return

    if a.section:
        if a.section not in table:
            sys.exit(f"Unknown section {a.section!r}. Choices: {', '.join(table)}")
        span = find_span(text, *table[a.section])
        if not span:
            sys.exit(f"Could not locate '{a.section}' in this {meta['form']}. "
                     f"Run --list to see what was found, or read the full text.")
        body = text[span[0]:span[1]].strip()
    else:
        body = text

    if a.chars and len(body) > a.chars:
        body = body[:a.chars] + f"\n\n[truncated at {a.chars:,} of {len(body):,} characters]"

    out = header + "\n\n" + body
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(f"wrote {len(out):,} characters to {a.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
