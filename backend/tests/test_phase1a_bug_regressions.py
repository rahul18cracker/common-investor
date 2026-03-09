"""
Regression tests for Phase 1A data correctness bug fixes.

BUG-1: or-chain treats g=0.0 as falsy (valuation/service.py, nlp/fourm/service.py)
BUG-2: band_score division by zero when low=0 and x<0 (nlp/fourm/service.py)
BUG-3: negative equity produces meaningless ROIC and D/E (metrics/compute.py)
"""
import pytest
from unittest.mock import patch, MagicMock
from app.valuation.service import run_default_scenario
from app.nlp.fourm.service import (
    compute_management,
    compute_margin_of_safety_recommendation,
)
from app.metrics.compute import roic_series, latest_debt_to_equity


pytestmark = pytest.mark.unit


# =============================================================================
# BUG-1: or-chain treats g=0.0 as falsy
# =============================================================================


class TestBug1ZeroGrowthNotFalsy:
    """BUG-1: Growth rate of exactly 0.0 must be used, not skipped as falsy."""

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_zero_eps_growth_used_not_skipped(
        self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute
    ):
        """g=0.0 from eps_cagr_5y must be used, not fall through to rev_cagr_5y."""
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {
            "eps_cagr_5y": 0.0,
            "rev_cagr_5y": 0.12,
        }
        mock_oe.return_value = 10.00
        mock_execute.return_value.first.return_value = None

        result = run_default_scenario("MSFT")

        assert result["inputs"]["g"] == 0.0

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_zero_rev_growth_used_when_eps_none(
        self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute
    ):
        """g=0.0 from rev_cagr_5y must be used when eps_cagr_5y is None."""
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {
            "eps_cagr_5y": None,
            "rev_cagr_5y": 0.0,
            "eps_cagr_10y": 0.08,
        }
        mock_oe.return_value = 10.00
        mock_execute.return_value.first.return_value = None

        result = run_default_scenario("MSFT")

        assert result["inputs"]["g"] == 0.0

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_g_override_zero_is_respected(
        self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute
    ):
        """Explicit g_override=0.0 must be used."""
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 10.00
        mock_execute.return_value.first.return_value = None

        result = run_default_scenario("MSFT", g_override=0.0)

        assert result["inputs"]["g"] == 0.0

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_none_growth_falls_through_to_default(
        self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute
    ):
        """When all growth metrics are None, default 0.10 is used."""
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {
            "eps_cagr_5y": None,
            "rev_cagr_5y": None,
            "eps_cagr_10y": None,
            "rev_cagr_10y": None,
        }
        mock_oe.return_value = 10.00
        mock_execute.return_value.first.return_value = None

        result = run_default_scenario("MSFT")

        assert result["inputs"]["g"] == 0.10

    @patch("app.nlp.fourm.service.compute_balance_sheet_resilience")
    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_recommendation_zero_growth_not_falsy(
        self, mock_moat, mock_mgmt, mock_growth, mock_bs
    ):
        """BUG-1 in compute_margin_of_safety_recommendation: g=0.0 must not fall through."""
        mock_moat.return_value = {"score": 0.7}
        mock_mgmt.return_value = {"score": 0.6}
        mock_growth.return_value = {
            "eps_cagr_5y": 0.0,
            "rev_cagr_5y": 0.12,
        }
        mock_bs.return_value = {"score": 3.5}

        result = compute_margin_of_safety_recommendation("test_cik")

        assert result["drivers"]["growth"] == 0.0


# =============================================================================
# BUG-2: band_score division by zero
# =============================================================================


class TestBug2BandScoreDivisionByZero:
    """BUG-2: band_score(x, 0.0, high) crashes with ZeroDivisionError when x<0."""

    @patch("app.nlp.fourm.service.execute")
    def test_negative_payout_ratio_no_crash(self, mock_execute):
        """Negative payout ratio (x<0, low=0) must not cause ZeroDivisionError."""
        # Simulate company with negative buybacks/dividends (reported as negative in XBRL)
        mock_execute.return_value.fetchall.return_value = [
            (2021, 50e9, 10e9, -5e9, -2e9, 100e9),
            (2022, 55e9, 11e9, -6e9, -3e9, 110e9),
            (2023, 60e9, 12e9, -7e9, -4e9, 120e9),
        ]

        # Should not raise ZeroDivisionError
        result = compute_management("test_cik")
        assert result["score"] is not None

    @patch("app.nlp.fourm.service.execute")
    def test_zero_cfo_returns_none_ratios(self, mock_execute):
        """When CFO is zero, ratios should be None (not crash)."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 0.0, 10e9, 0.0, 0.0, 100e9),
            (2022, 0.0, 11e9, 0.0, 0.0, 110e9),
        ]

        result = compute_management("test_cik")
        assert result["reinvest_ratio_avg"] is None
        assert result["payout_ratio_avg"] is None

    @patch("app.nlp.fourm.service.execute")
    def test_none_cfo_returns_none_ratios(self, mock_execute):
        """When CFO is None, ratios should be None (not crash)."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, None, 10e9, None, None, 100e9),
            (2022, None, 11e9, None, None, 110e9),
        ]

        result = compute_management("test_cik")
        assert result["reinvest_ratio_avg"] is None
        assert result["payout_ratio_avg"] is None

    @patch("app.nlp.fourm.service.execute")
    def test_empty_data_returns_none_score(self, mock_execute):
        """Empty result set should return None score, not crash."""
        mock_execute.return_value.fetchall.return_value = []

        result = compute_management("test_cik")
        assert result["score"] is None


# =============================================================================
# BUG-3: Negative equity produces meaningless ROIC and D/E
# =============================================================================


class TestBug3NegativeEquity:
    """BUG-3: Companies like SBUX/MCD/LMT have negative shareholder equity.
    This made invested capital negative, producing extreme/meaningless ROIC values
    and garbage D/E ratios."""

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_negative_invested_capital_yields_none_roic(self, mock_fetch):
        """When equity + debt - cash < 0, ROIC should be None, not a huge number."""
        # SBUX-like: negative equity (-8B), some debt (12B), lots of cash (6B)
        # invested_capital = -8B + 12B - 6B = -2B (negative)
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 6e9,
                "capex": 2e9,
                "shares": 1.1e9,
                "ebit": 5e9,
                "taxes": 1e9,
                "debt": 12e9,
                "equity": -8e9,
                "cash": 6e9,
                "revenue": 35e9,
            }
        ]

        result = roic_series("test_cik")

        assert len(result) == 1
        assert result[0]["roic"] is None

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_zero_invested_capital_yields_none_roic(self, mock_fetch):
        """When invested capital is exactly zero, ROIC should be None."""
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 5e9,
                "capex": 1e9,
                "shares": 1e9,
                "ebit": 4e9,
                "taxes": 0.8e9,
                "debt": 10e9,
                "equity": -5e9,
                "cash": 5e9,
                "revenue": 30e9,
            }
        ]

        result = roic_series("test_cik")

        assert result[0]["roic"] is None

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_positive_invested_capital_computes_roic(self, mock_fetch):
        """Normal positive invested capital still produces valid ROIC."""
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 60e9,
                "capex": 15e9,
                "shares": 7.5e9,
                "ebit": 53e9,
                "taxes": 9e9,
                "debt": 60e9,
                "equity": 118e9,
                "cash": 14e9,
                "revenue": 143e9,
            }
        ]

        result = roic_series("test_cik")

        assert result[0]["roic"] is not None
        # MSFT-like: ROIC should be positive and reasonable
        assert 0.05 < result[0]["roic"] < 0.50

    @patch("app.metrics.compute.execute")
    def test_negative_equity_de_returns_none(self, mock_execute):
        """D/E ratio should be None when equity is negative."""
        mock_execute.return_value.first.return_value = (12e9, -8e9)

        result = latest_debt_to_equity("test_cik")

        assert result is None

    @patch("app.metrics.compute.execute")
    def test_zero_equity_de_returns_none(self, mock_execute):
        """D/E ratio should be None when equity is exactly zero."""
        mock_execute.return_value.first.return_value = (10e9, 0.0)

        result = latest_debt_to_equity("test_cik")

        assert result is None

    @patch("app.metrics.compute.execute")
    def test_positive_equity_de_computes(self, mock_execute):
        """Normal positive equity still produces valid D/E ratio."""
        mock_execute.return_value.first.return_value = (60e9, 118e9)

        result = latest_debt_to_equity("test_cik")

        assert result is not None
        assert result == pytest.approx(60e9 / 118e9, rel=1e-6)


# =============================================================================
# XBRL fix: _pick_first_units checks for 10-K data presence
# =============================================================================


class TestPickFirstUnitsAnnualFilter:
    """Regression: _pick_first_units must only return tags that have 10-K/20-F data,
    not tags that merely exist with quarterly-only data."""

    def test_skips_tag_with_only_quarterly_data(self):
        """A tag with only 10-Q data should be skipped in favor of one with 10-K."""
        from app.ingest.sec import _pick_first_units

        facts = {
            "facts": {
                "us-gaap": {
                    "CostOfRevenue": {
                        "units": {
                            "USD": [
                                {"form": "10-Q", "fy": 2023, "val": 1000, "end": "2023-03-31"},
                            ]
                        }
                    },
                    "CostOfGoodsAndServicesSold": {
                        "units": {
                            "USD": [
                                {"form": "10-K", "fy": 2023, "val": 5000, "end": "2023-12-31"},
                            ]
                        }
                    },
                }
            }
        }

        result = _pick_first_units(facts, ["CostOfRevenue", "CostOfGoodsAndServicesSold"])

        # Should skip CostOfRevenue (only 10-Q) and return CostOfGoodsAndServicesSold
        assert result is not None
        assert any(
            e.get("form") == "10-K"
            for entries in result.values()
            for e in entries
        )

    def test_returns_none_when_no_annual_data(self):
        """Returns None if no tag has 10-K/20-F entries."""
        from app.ingest.sec import _pick_first_units

        facts = {
            "facts": {
                "us-gaap": {
                    "SomeTag": {
                        "units": {
                            "USD": [
                                {"form": "10-Q", "fy": 2023, "val": 100},
                            ]
                        }
                    },
                }
            }
        }

        result = _pick_first_units(facts, ["SomeTag"])

        assert result is None

    def test_returns_first_tag_with_annual_data(self):
        """When first tag has 10-K data, return it immediately."""
        from app.ingest.sec import _pick_first_units

        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"form": "10-K", "fy": 2023, "val": 50e9, "end": "2023-12-31"},
                            ]
                        }
                    },
                    "SalesRevenueNet": {
                        "units": {
                            "USD": [
                                {"form": "10-K", "fy": 2023, "val": 50e9, "end": "2023-12-31"},
                            ]
                        }
                    },
                }
            }
        }

        result = _pick_first_units(facts, ["Revenues", "SalesRevenueNet"])

        # Should return first match (Revenues)
        assert result is not None
        assert 50e9 in [e["val"] for e in result["USD"]]

    def test_handles_20f_form(self):
        """Foreign filers using 20-F should also be matched."""
        from app.ingest.sec import _pick_first_units

        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"form": "20-F", "fy": 2023, "val": 30e9, "end": "2023-12-31"},
                            ]
                        }
                    },
                }
            }
        }

        result = _pick_first_units(facts, ["Revenues"])

        assert result is not None
