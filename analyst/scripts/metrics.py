#!/usr/bin/env python3
"""Compute fundamentals from cached EDGAR XBRL facts.

Every number this prints is arithmetic over values the company actually filed.
Nothing here is estimated, and nothing here is produced by a language model —
that is the entire point of keeping the math in Python.

    python3 metrics.py AAPL
    python3 metrics.py AAPL --years 7 --price 245.30
    python3 metrics.py AAPL --json
"""
import argparse, json, sys
from datetime import date

import edgar

# Companies tag the same line item differently, and change tags between years.
# Each concept is a preference chain: the first tag with usable data wins.
DURATION_CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
}

INSTANT_CONCEPTS = {
    "assets": ["Assets"],
    "assets_current": ["AssetsCurrent"],
    "liabilities": ["Liabilities"],
    "liabilities_current": ["LiabilitiesCurrent"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "short_term_investments": ["MarketableSecuritiesCurrent", "ShortTermInvestments",
                               "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "inventory": ["InventoryNet"],
    "receivables": ["AccountsReceivableNetCurrent"],
    "debt_long": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "debt_short": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings",
                   "OtherShortTermBorrowings"],
    "goodwill": ["Goodwill"],
}

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}
PERIODIC_FORMS = ANNUAL_FORMS | {"10-Q", "10-Q/A"}


def _records(facts, tags, unit="USD"):
    """Pick the best tag in the chain and return its raw fact records.

    Companies abandon one tag and adopt another mid-history, so "first tag with
    any data" is wrong: it can select a tag that went stale years ago and
    silently mix a 2018 revenue with a 2025 net income. Choose the tag with the
    most recent data, breaking ties by the chain's preference order.
    """
    ug = facts["facts"].get("us-gaap", {})
    best = None
    for rank, tag in enumerate(tags):
        node = ug.get(tag)
        if not node:
            continue
        for u in (unit, "USD/shares", "shares", "pure"):
            recs = node.get("units", {}).get(u)
            if not recs:
                continue
            latest = max((r["end"] for r in recs if r.get("form") in PERIODIC_FORMS), default="")
            if best is None or (latest, -rank) > (best[0], -best[1]):
                best = (latest, rank, tag, recs)
            break
    return (best[2], best[3]) if best else (None, [])


def _dedupe(records):
    """EDGAR restates the same period across later filings. Keep the newest filing.

    Callers must filter by form *before* calling this. An 8-K press release can
    carry the same period with a later filing date, and if it wins here it will
    then be dropped by a form filter, silently deleting that fiscal year.
    """
    best = {}
    for r in records:
        key = (r.get("start"), r["end"])
        prev = best.get(key)
        if prev is None or r.get("filed", "") > prev.get("filed", ""):
            best[key] = r
    return sorted(best.values(), key=lambda r: r["end"])


def _days(r):
    y1, m1, d1 = map(int, r["start"].split("-"))
    y2, m2, d2 = map(int, r["end"].split("-"))
    return (date(y2, m2, d2) - date(y1, m1, d1)).days


def annual_series(facts, concept, tags, years):
    """One value per fiscal year, taken from annual reports only."""
    unit = "USD/shares" if concept == "eps_diluted" else ("shares" if "shares" in concept else "USD")
    tag, recs = _records(facts, tags, unit)
    if not recs:
        return tag, {}
    annual = [r for r in recs
              if r.get("start") and r.get("form") in ANNUAL_FORMS and 330 <= _days(r) <= 400]
    fy = _dedupe(annual)
    return tag, {r["end"]: r["val"] for r in fy[-years:]}


def latest_instant(facts, tags):
    """Most recent balance-sheet value from any filing, 10-Q included."""
    tag, recs = _records(facts, tags)
    recs = [r for r in recs if not r.get("start") and r.get("form") in PERIODIC_FORMS]
    if not recs:
        return tag, None, None
    r = _dedupe(recs)[-1]
    return tag, r["val"], r["end"]


def ttm(facts, concept, tags):
    """Trailing twelve months = last full year + current YTD - prior-year same YTD.

    Companies do not file a standalone Q4, so this is the only way to get a
    current twelve-month figure out of XBRL. Returns None when the pieces do
    not line up, which is better than returning a number that is wrong.
    """
    unit = "USD/shares" if concept == "eps_diluted" else ("shares" if "shares" in concept else "USD")
    _, recs = _records(facts, tags, unit)
    recs = [r for r in recs if r.get("start") and r.get("form") in PERIODIC_FORMS]
    if not recs:
        return None, None
    annual = _dedupe([r for r in recs if r["form"] in ANNUAL_FORMS and 330 <= _days(r) <= 400])
    if not annual:
        return None, None
    fy = annual[-1]
    quarterly = _dedupe([r for r in recs if r["form"] not in ANNUAL_FORMS])
    ytd = [r for r in quarterly if r["start"] > fy["end"] and _days(r) > 60]
    if not ytd:
        return fy["val"], fy["end"]  # no interim data yet; the last full year is the TTM
    cur = max(ytd, key=lambda r: (r["end"], _days(r)))
    span = _days(cur)
    prior = [r for r in quarterly
             if r["start"] <= fy["end"] and r["end"] <= fy["end"] and abs(_days(r) - span) <= 10]
    if not prior:
        return None, None
    return fy["val"] + cur["val"] - max(prior, key=lambda r: r["end"])["val"], cur["end"]


def _date_gap(a, b):
    y1, m1, d1 = map(int, a.split("-"))
    y2, m2, d2 = map(int, b.split("-"))
    return (date(y2, m2, d2) - date(y1, m1, d1)).days


def div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def build(ticker, years=5, price=None, refresh=False, facts=None):
    """Assemble every figure for one company. Pass `facts` to skip the network."""
    if facts is None:
        facts = edgar.company_facts(ticker, refresh)
    out = {"ticker": facts["_ticker"], "company": facts["_name"], "cik": facts["_cik"],
           "source": "SEC EDGAR XBRL companyfacts", "tags_used": {},
           "annual": {}, "ttm": {}, "balance_sheet": {}, "derived": {}, "warnings": []}

    for concept, tags in DURATION_CONCEPTS.items():
        tag, series = annual_series(facts, concept, tags, years)
        if series:
            out["annual"][concept] = series
            out["tags_used"][concept] = tag
        val, asof = ttm(facts, concept, tags)
        if val is not None:
            out["ttm"][concept] = {"value": val, "through": asof}

    for concept, tags in INSTANT_CONCEPTS.items():
        tag, val, asof = latest_instant(facts, tags)
        if val is not None:
            out["balance_sheet"][concept] = {"value": val, "as_of": asof}
            out["tags_used"][concept] = tag

    # Every TTM figure must cover the same period, or the ratios are nonsense.
    if out["ttm"]:
        newest = max(v["through"] for v in out["ttm"].values())
        stale = {k: v["through"] for k, v in out["ttm"].items()
                 if _date_gap(v["through"], newest) > 120}
        for k in stale:
            del out["ttm"][k]
        if stale:
            out["warnings"].append(
                "Dropped from TTM because the company stopped reporting under the tag this "
                "script tracks, leaving data older than the rest of the period "
                f"(newest is {newest}): "
                + ", ".join(f"{k} (last seen {v})" for k, v in sorted(stale.items()))
                + ". Read these off the filing directly.")

    t = {k: v["value"] for k, v in out["ttm"].items()}
    b = {k: v["value"] for k, v in out["balance_sheet"].items()}
    d = out["derived"]

    rev = t.get("revenue")
    gp = t.get("gross_profit")
    if gp is None and rev is not None and t.get("cost_of_revenue") is not None:
        gp = rev - t["cost_of_revenue"]
        out["warnings"].append("Gross profit not tagged; derived as revenue - cost of revenue.")
    d["gross_margin"] = div(gp, rev)
    d["operating_margin"] = div(t.get("operating_income"), rev)
    d["net_margin"] = div(t.get("net_income"), rev)
    d["fcf"] = (t["ocf"] - t["capex"]) if t.get("ocf") is not None and t.get("capex") is not None else None
    d["fcf_margin"] = div(d["fcf"], rev)
    d["rnd_pct_revenue"] = div(t.get("rnd"), rev)

    total_debt = sum(b[k] for k in ("debt_long", "debt_short") if k in b) or None
    net_cash = None
    if total_debt is not None:
        liquid = sum(b[k] for k in ("cash", "short_term_investments") if k in b)
        net_cash = liquid - total_debt
    d["total_debt"] = total_debt
    d["net_cash"] = net_cash
    d["current_ratio"] = div(b.get("assets_current"), b.get("liabilities_current"))
    d["debt_to_equity"] = div(total_debt, b.get("equity"))
    d["return_on_equity"] = div(t.get("net_income"), b.get("equity"))
    d["return_on_assets"] = div(t.get("net_income"), b.get("assets"))
    d["interest_coverage"] = div(t.get("operating_income"), t.get("interest_expense"))

    rows = out["annual"].get("revenue", {})
    if len(rows) >= 2:
        ends, vals = list(rows.keys()), list(rows.values())
        if 300 <= _date_gap(ends[-2], ends[-1]) <= 430:
            d["revenue_growth_latest"] = div(vals[-1] - vals[-2], abs(vals[-2]))
        else:
            out["warnings"].append(
                f"No revenue reported for the year before FY ending {ends[-1]}; latest growth omitted.")
        n = round(_date_gap(ends[0], ends[-1]) / 365.25)
        if vals[0] > 0 and vals[-1] > 0 and n >= 1:
            d["revenue_cagr"] = (vals[-1] / vals[0]) ** (1 / n) - 1
            d["revenue_cagr_years"] = n

    shares = t.get("shares_diluted")
    if price is not None and shares:
        mcap = price * shares
        d["price"] = price
        d["market_cap"] = mcap
        d["pe_ttm"] = div(mcap, t.get("net_income"))
        d["ps_ttm"] = div(mcap, rev)
        d["fcf_yield"] = div(d["fcf"], mcap)
        d["price_to_book"] = div(mcap, b.get("equity"))
        if net_cash is not None and t.get("operating_income"):
            d["ev"] = mcap - net_cash
            d["ev_ebit"] = div(d["ev"], t["operating_income"])
    elif price is not None:
        out["warnings"].append("Diluted share count unavailable; valuation multiples skipped.")

    if not out["annual"] and out["balance_sheet"]:
        out["warnings"].append(
            f"This CIK reports a balance sheet but no income-statement history. That usually "
            f"means a recent reorganization, spin-off, or re-domicile, where the ticker now "
            f"points at a successor entity whose filings start over. Run "
            f"`python3 scripts/edgar.py filings {out['ticker']} -n 10` and check the earliest "
            f"filing for the predecessor's name, then analyze that CIK for history.")
    elif not out["ttm"]:
        out["warnings"].append(
            "No TTM figures could be assembled. The filer may use IFRS or industry tags rather "
            "than the us-gaap tags tracked here — read the statements off the filing directly.")
    return out


# ── rendering ────────────────────────────────────────────────────────────────
def usd(v):
    if v is None:
        return "Not disclosed"
    a = abs(v)
    for cut, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= cut:
            return f"${v/cut:,.2f}{suf}"
    return f"${v:,.0f}"


def pct(v):
    return "Not disclosed" if v is None else f"{v*100:.1f}%"


def mult(v):
    return "Not disclosed" if v is None else f"{v:.1f}x"


def render(m):
    L = [f"# {m['company']} ({m['ticker']})",
         f"CIK {m['cik']} · source: {m['source']}", ""]

    rev = m["annual"].get("revenue", {})
    if rev:
        L += ["## Revenue by fiscal year", "", "| FY ending | Revenue | Growth |", "|---|---:|---:|"]
        prev_end = prev = None
        for end, val in rev.items():
            # A gap in the series means the comparison would span two years.
            adjacent = prev_end is not None and 300 <= _date_gap(prev_end, end) <= 430
            g = f"{(val-prev)/abs(prev)*100:+.1f}%" if adjacent and prev else "—"
            L.append(f"| {end} | {usd(val)} | {g} |")
            prev_end, prev = end, val
        L.append("")

    t, d = m["ttm"], m["derived"]
    if t:
        through = next(iter(t.values()))["through"]
        L += [f"## Trailing twelve months (through {through})", "",
              "| Metric | Value |", "|---|---:|"]
        for label, key in [("Revenue", "revenue"), ("Gross profit", "gross_profit"),
                           ("Operating income", "operating_income"), ("Net income", "net_income"),
                           ("Operating cash flow", "ocf"), ("Capex", "capex")]:
            if key in t:
                L.append(f"| {label} | {usd(t[key]['value'])} |")
        for label, key in [("Free cash flow", "fcf")]:
            L.append(f"| {label} | {usd(d.get(key))} |")
        L += [f"| Gross margin | {pct(d.get('gross_margin'))} |",
              f"| Operating margin | {pct(d.get('operating_margin'))} |",
              f"| Net margin | {pct(d.get('net_margin'))} |",
              f"| FCF margin | {pct(d.get('fcf_margin'))} |", ""]

    b = m["balance_sheet"]
    if b:
        asof = next(iter(b.values()))["as_of"]
        L += [f"## Balance sheet (as of {asof})", "", "| Metric | Value |", "|---|---:|",
              f"| Cash & equivalents | {usd(b.get('cash', {}).get('value'))} |",
              f"| Short-term investments | {usd(b.get('short_term_investments', {}).get('value'))} |",
              f"| Total debt | {usd(d.get('total_debt'))} |",
              f"| Net cash (debt) | {usd(d.get('net_cash'))} |",
              f"| Shareholders' equity | {usd(b.get('equity', {}).get('value'))} |",
              f"| Current ratio | {mult(d.get('current_ratio'))} |",
              f"| Debt / equity | {mult(d.get('debt_to_equity'))} |",
              f"| Interest coverage | {mult(d.get('interest_coverage'))} |",
              f"| Return on equity | {pct(d.get('return_on_equity'))} |",
              f"| Return on assets | {pct(d.get('return_on_assets'))} |", ""]

    if d.get("revenue_cagr") is not None:
        L += [f"Revenue CAGR over {d['revenue_cagr_years']} years: {pct(d['revenue_cagr'])}", ""]

    if d.get("price") is not None:
        L += [f"## Valuation at ${d['price']:,.2f}", "", "| Metric | Value |", "|---|---:|",
              f"| Market cap | {usd(d.get('market_cap'))} |",
              f"| Enterprise value | {usd(d.get('ev'))} |",
              f"| P/E (TTM) | {mult(d.get('pe_ttm'))} |",
              f"| P/S (TTM) | {mult(d.get('ps_ttm'))} |",
              f"| P/B | {mult(d.get('price_to_book'))} |",
              f"| EV/EBIT | {mult(d.get('ev_ebit'))} |",
              f"| FCF yield | {pct(d.get('fcf_yield'))} |", ""]

    if m["warnings"]:
        L += ["## Warnings", ""] + [f"- {w}" for w in m["warnings"]] + [""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--price", type=float, help="share price for valuation multiples")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-download instead of using cache")
    a = ap.parse_args()
    m = build(a.ticker, a.years, a.price, a.refresh)
    print(json.dumps(m, indent=2) if a.json else render(m))


if __name__ == "__main__":
    main()
