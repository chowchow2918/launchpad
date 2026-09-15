# Equity analyst

A personal research agent for analyzing public companies from primary sources.
It pulls financial data straight from SEC filings, computes the metrics in
Python, reads the actual 10-K, compares peers, and keeps a running thesis note
per company.

Self-contained: copy this directory anywhere, or into its own repo, and it
works. Python 3.9+, no pip installs, no API keys.

## Setup

```bash
export ANALYST_UA="Your Name your@email.com"
```

SEC EDGAR is free and open but requires a User-Agent that identifies the
caller, and blocks requests without one. Put that line in your shell profile.

## Use it

Run Claude Code from inside this directory and ask:

> analyze MSFT

The `analyst` skill loads automatically and runs the workflow: pull the
financials, fetch the price, read the latest filing, compare peers, write the
analysis, update `notes/MSFT.md`.

Other things to ask for:

> compare KO and PEP
> what needs attention on my watchlist
> re-check MSFT

The last one reads your previous note first and tells you what changed against
what you concluded then.

## The tools

Five scripts. Each works standalone if you'd rather drive them yourself.

### `metrics.py` — the numbers

Computes every figure from filed XBRL data. Nothing is estimated.

```bash
python3 scripts/metrics.py AAPL                  # 5 years + TTM + balance sheet
python3 scripts/metrics.py AAPL --years 10       # longer history
python3 scripts/metrics.py AAPL --price 245.30   # add valuation multiples
python3 scripts/metrics.py AAPL --json           # full data, incl. XBRL tags used
python3 scripts/metrics.py AAPL --refresh        # bypass the 24-hour cache
```

Revenue by fiscal year with growth, TTM income statement with margins, current
balance sheet with liquidity and leverage, and multiples when given a price.

### `filing.py` — the words

Downloads a filing and extracts readable sections. A 10-K is 1.5MB of
inline-XBRL HTML; this turns it into the ~20KB you actually want.

```bash
python3 scripts/filing.py AAPL --list                   # sections and sizes
python3 scripts/filing.py AAPL --section mda            # management's discussion
python3 scripts/filing.py AAPL --section risk
python3 scripts/filing.py AAPL --section risk --index 1 # last year's, to diff
python3 scripts/filing.py AAPL --form 10-Q --section mda
```

Sections: `business`, `risk`, `properties`, `legal`, `mda`, `market-risk`,
`financials`, `controls`.

### `compare.py` — peers side by side

```bash
python3 scripts/compare.py KO PEP
python3 scripts/compare.py AAPL MSFT GOOGL --no-prices
```

Same metrics, same computation, one table. Rows nobody reports are dropped.

### `watchlist.py` — what needs attention

```bash
python3 scripts/watchlist.py add MSFT --held --tag software
python3 scripts/watchlist.py list
python3 scripts/watchlist.py check
```

`check` compares each company's newest SEC filing against the date of your last
note and tells you what has filed since you last looked. Your holdings stay in
`watchlist.json`, which is gitignored — see `watchlist.example.json` for the
format.

### `edgar.py` — the data layer

Used by the others; useful directly for filing URLs.

```bash
python3 scripts/edgar.py fetch AAPL
python3 scripts/edgar.py filings AAPL -n 5 --forms 10-K,10-Q,8-K
```

### `prices.py` — quotes

```bash
python3 scripts/prices.py AAPL MSFT KO
```

## Tests

```bash
python3 tests/test_metrics.py
```

Thirteen tests covering the extraction logic. Worth running after any change to
`metrics.py` — the bugs this code has had were all silent ones that produced
believable wrong numbers.

## Why the math is in Python

Language models are good at reading a 200-page filing and bad at arithmetic
over it. So the split is strict: `metrics.py` computes every number from filed
XBRL data and nothing else, and the model reads, explains, and argues over that
output. It is not allowed to produce a figure the scripts did not.

This is the difference between a research tool and a very confident
random-number generator.

## Data sources

| What | Source | Key | Reliability |
|---|---|---|---|
| Financial statements | SEC EDGAR XBRL `companyfacts` | No | Official, stable |
| Filing documents | SEC EDGAR `submissions` + Archives | No | Official, stable |
| Share price | Yahoo chart endpoint | No | Unofficial, may break |

If the price fetch stops working, pass `--price` by hand. Nothing else depends
on it. The fundamentals come from the SEC and will not rot.

EDGAR rate-limits around 10 requests/second. Company facts and filing HTML are
cached in `data/`, which is gitignored.

## Known limits

- **Banks, insurers, REITs** don't report gross profit, current ratio, or
  conventional operating cash flow, and often incorporate MD&A by reference to
  an exhibit. Those print as "Not disclosed" or get flagged as cross-references
  rather than being faked. Analyze them from the filing's own statements.
- **Foreign issuers** filing 20-F have thinner XBRL coverage; some have none.
- **Successor entities.** After a reorganization the ticker can point at a new
  CIK with no income-statement history. The script detects this and tells you
  how to find the predecessor.
- **TTM** is assembled as last full year + current YTD − prior-year YTD, since
  companies never file a standalone Q4. When the periods don't line up the
  script returns nothing instead of a wrong number.
- **XBRL tag drift** is the main source of surprise. If a figure looks wrong,
  run `--json` and check `tags_used`.

## Not investment advice

A tool for doing your own research. It reports what companies filed and
computes ratios from it. Every decision is yours.
