# Equity analyst

A personal research agent for analyzing public companies from primary sources.
It pulls financial data straight from SEC filings, computes the metrics in
Python, reads the actual 10-K, and keeps a running thesis note per company.

Built to be self-contained: copy this directory anywhere, or into its own repo,
and it works.

## Setup

Python 3.9+ and nothing else — no pip installs, no API keys.

```bash
export ANALYST_UA="Your Name your@email.com"
```

SEC EDGAR is free and open but requires a User-Agent that identifies the
caller, and blocks requests without one. Put that line in your shell profile.

## Use it

Run Claude Code from inside this directory and ask:

> analyze MSFT

The `analyst` skill loads automatically and runs the whole workflow: pull the
financials, fetch the current price, read the latest filing, write the analysis,
update `notes/MSFT.md`.

Months later, `re-check MSFT` reads that note first and tells you what changed
against what you previously concluded.

## The scripts on their own

They work standalone if you'd rather drive them yourself.

```bash
python3 scripts/metrics.py AAPL                  # 5 years + TTM + balance sheet
python3 scripts/metrics.py AAPL --years 10       # longer history
python3 scripts/metrics.py AAPL --price 245.30   # add valuation multiples
python3 scripts/metrics.py AAPL --json           # full data, incl. XBRL tags used
python3 scripts/metrics.py AAPL --refresh        # bypass the cache

python3 scripts/prices.py AAPL MSFT KO           # current quotes
python3 scripts/edgar.py filings AAPL -n 5       # recent filings with URLs
```

## Why the math is in Python

Language models are good at reading a 200-page filing and bad at arithmetic
over it. So the split is strict: `metrics.py` computes every number from filed
XBRL data and nothing else, and the model reads, explains, and argues over that
output. It is not allowed to produce a figure the scripts did not.

This is the difference between a research tool and a very confident
random-number generator.

## Data sources

| What | Source | Key needed | Reliability |
|---|---|---|---|
| Financial statements | SEC EDGAR XBRL `companyfacts` | No | Official, stable |
| Filing documents | SEC EDGAR `submissions` | No | Official, stable |
| Share price | Yahoo chart endpoint | No | Unofficial, may break |

If the price fetch stops working, pass `--price` by hand. Nothing else depends
on it. Fundamentals — the part that matters — come from the SEC and will not
rot.

EDGAR rate-limits around 10 requests/second; the scripts cache company facts for
24 hours in `data/`, which is gitignored.

## Known limits

- **Banks, insurers, REITs** don't report gross profit, current ratio, or
  conventional operating cash flow. Those print as "Not disclosed" rather than
  being faked. Analyze them from the filing's own statements.
- **Foreign issuers** filing 20-F have thinner XBRL coverage; some have none.
- **TTM** is assembled as last full year + current YTD − prior-year YTD, since
  companies never file a standalone Q4. When the periods don't line up the
  script returns nothing instead of a wrong number.
- **XBRL tag drift** is the main source of surprise. If a figure looks wrong,
  run `--json` and check `tags_used`.

## Not investment advice

This is a tool for doing your own research. It reports what companies filed and
computes ratios from it. Every decision is yours.
