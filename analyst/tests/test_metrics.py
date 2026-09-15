#!/usr/bin/env python3
"""Regression tests for the metric extraction logic.

These lock in three bugs that produced plausible-looking wrong numbers. All of
them are silent failures -- the output looked fine and was wrong -- so they are
worth a test each. Run with:  python3 tests/test_metrics.py
"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import metrics


def facts(tags):
    """Build a minimal companyfacts structure: {tag: [records]}."""
    return {"facts": {"us-gaap": {t: {"units": {"USD": r}} for t, r in tags.items()}},
            "_ticker": "TEST", "_cik": 1, "_name": "Test Corp"}


def fy(start, end, val, form="10-K", filed=None):
    return {"start": start, "end": end, "val": val, "form": form,
            "filed": filed or end, "fp": "FY"}


class FormFilteringBeforeDedupe(unittest.TestCase):
    """An 8-K restating a period must not evict the 10-K and delete that year.

    Deduplication keeps the newest filing for a period. If it runs before the
    form filter, a later 8-K press release wins and is then dropped, silently
    removing a fiscal year and making the next year's growth compare across a
    two-year gap.
    """

    def test_8k_restatement_does_not_delete_a_year(self):
        f = facts({"Revenues": [
            fy("2023-01-01", "2023-12-31", 100, "10-K", filed="2024-02-01"),
            fy("2023-01-01", "2023-12-31", 100, "8-K", filed="2025-06-01"),
            fy("2024-01-01", "2024-12-31", 120, "10-K", filed="2025-02-01"),
        ]})
        _, series = metrics.annual_series(f, "revenue", ["Revenues"], 5)
        self.assertEqual(list(series.values()), [100, 120])

    def test_later_10k_restatement_still_wins(self):
        f = facts({"Revenues": [
            fy("2023-01-01", "2023-12-31", 100, "10-K", filed="2024-02-01"),
            fy("2023-01-01", "2023-12-31", 105, "10-K", filed="2025-02-01"),
        ]})
        _, series = metrics.annual_series(f, "revenue", ["Revenues"], 5)
        self.assertEqual(list(series.values()), [105])


class TagSelection(unittest.TestCase):
    """Pick the tag with current data, not merely the first tag with any data.

    Filers abandon one tag and adopt another mid-history. Taking the first
    match in the preference chain can select a tag that went stale years ago,
    pairing an old revenue with a current net income.
    """

    def test_prefers_the_tag_with_recent_data(self):
        f = facts({
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                fy("2017-01-01", "2017-12-31", 50)],
            "Revenues": [
                fy("2024-01-01", "2024-12-31", 900),
                fy("2025-01-01", "2025-12-31", 1000)],
        })
        tag, series = metrics.annual_series(f, "revenue", metrics.DURATION_CONCEPTS["revenue"], 5)
        self.assertEqual(tag, "Revenues")
        self.assertEqual(list(series.values()), [900, 1000])

    def test_chain_order_breaks_ties_at_equal_recency(self):
        f = facts({
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                fy("2025-01-01", "2025-12-31", 1000)],
            "Revenues": [fy("2025-01-01", "2025-12-31", 999)],
        })
        tag, _ = metrics.annual_series(f, "revenue", metrics.DURATION_CONCEPTS["revenue"], 5)
        self.assertEqual(tag, "RevenueFromContractWithCustomerExcludingAssessedTax")


class PeriodConsistency(unittest.TestCase):
    """Never divide figures that cover different periods."""

    def test_stale_concept_is_dropped_from_ttm_with_a_warning(self):
        # Net income reported seven years before revenue. Dividing one by the
        # other would yield an authoritative-looking and meaningless margin.
        out = metrics.build("TEST", facts=facts({
            "Revenues": [fy("2025-01-01", "2025-12-31", 1000)],
            "NetIncomeLoss": [fy("2018-01-01", "2018-12-31", 800)],
        }))
        self.assertIn("revenue", out["ttm"])
        self.assertNotIn("net_income", out["ttm"])
        self.assertIsNone(out["derived"]["net_margin"])
        self.assertTrue(any("net_income" in w for w in out["warnings"]))

    def test_matching_periods_are_kept_and_divided(self):
        out = metrics.build("TEST", facts=facts({
            "Revenues": [fy("2025-01-01", "2025-12-31", 1000)],
            "NetIncomeLoss": [fy("2025-01-01", "2025-12-31", 250)],
        }))
        self.assertAlmostEqual(out["derived"]["net_margin"], 0.25)

    def test_growth_not_computed_across_a_missing_year(self):
        f = facts({"Revenues": [
            fy("2022-01-01", "2022-12-31", 100),
            fy("2024-01-01", "2024-12-31", 200),
        ]})
        _, series = metrics.annual_series(f, "revenue", ["Revenues"], 5)
        ends = list(series)
        self.assertGreater(metrics._date_gap(ends[0], ends[1]), 430)


class TTMAssembly(unittest.TestCase):
    """TTM = last full year + current YTD - prior-year same YTD."""

    def test_assembles_from_ytd_periods(self):
        f = facts({"Revenues": [
            fy("2024-01-01", "2024-12-31", 1000, "10-K"),
            fy("2024-01-01", "2024-06-30", 400, "10-Q"),
            fy("2025-01-01", "2025-06-30", 500, "10-Q"),
        ]})
        val, through = metrics.ttm(f, "revenue", ["Revenues"])
        self.assertEqual(val, 1100)          # 1000 + 500 - 400
        self.assertEqual(through, "2025-06-30")

    def test_falls_back_to_the_full_year_when_no_interim_data(self):
        f = facts({"Revenues": [fy("2024-01-01", "2024-12-31", 1000, "10-K")]})
        val, through = metrics.ttm(f, "revenue", ["Revenues"])
        self.assertEqual((val, through), (1000, "2024-12-31"))

    def test_returns_nothing_when_the_prior_period_is_missing(self):
        f = facts({"Revenues": [
            fy("2024-01-01", "2024-12-31", 1000, "10-K"),
            fy("2025-01-01", "2025-06-30", 500, "10-Q"),
        ]})
        self.assertEqual(metrics.ttm(f, "revenue", ["Revenues"]), (None, None))


class Formatting(unittest.TestCase):
    def test_missing_values_are_labelled_not_zeroed(self):
        self.assertEqual(metrics.usd(None), "Not disclosed")
        self.assertEqual(metrics.pct(None), "Not disclosed")
        self.assertEqual(metrics.mult(None), "Not disclosed")

    def test_division_guards_against_zero_and_none(self):
        self.assertIsNone(metrics.div(1, 0))
        self.assertIsNone(metrics.div(None, 1))
        self.assertEqual(metrics.div(1, 4), 0.25)

    def test_scales_large_numbers(self):
        self.assertEqual(metrics.usd(4_840_000_000_000), "$4.84T")
        self.assertEqual(metrics.usd(-19_950_000_000), "$-19.95B")


if __name__ == "__main__":
    unittest.main(verbosity=2)
