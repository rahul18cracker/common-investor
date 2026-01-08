"""
Comprehensive unit tests for metrics computation module.

This test suite aims for 90%+ coverage of app/metrics/compute.py
Following industry best practices: AAA pattern, parameterization, clear assertions.
"""
import pytest
from unittest.mock import Mock, patch
from app.metrics.compute import (
    cagr,
    compute_growth_metrics,
    owner_earnings_series,
    latest_owner_earnings_ps,
    roic_series,
    coverage_series,
    margin_stability,
    latest_eps,
    revenue_eps_series,
    roic_average,
    latest_debt_to_equity,
    latest_owner_earnings_growth,
    timeseries_all,
    gross_margin_series,
    revenue_volatility,
    compute_growth_metrics_extended,
    net_debt_series,
    share_count_trend,
    roic_persistence_score,
    quality_scores,
)


# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


class TestCAGRCalculation:
    """Test Compound Annual Growth Rate calculations."""

    def test_cagr_typical_growth(self):
        """Test CAGR with typical positive growth scenario."""
        # Arrange: $100M to $200M over 5 years
        first, last, years = 100_000_000, 200_000_000, 5

        # Act
        result = cagr(first, last, years)

        # Assert: Should be approximately 14.87%
        assert result == pytest.approx(0.1487, rel=1e-2)

    def test_cagr_decline(self):
        """Test CAGR with negative growth (decline)."""
        # Arrange: $200M to $100M over 5 years
        first, last, years = 200_000_000, 100_000_000, 5

        # Act
        result = cagr(first, last, years)

        # Assert: Should be approximately -12.94%
        assert result == pytest.approx(-0.1294, rel=1e-2)

    def test_cagr_no_growth(self):
        """Test CAGR with zero growth."""
        # Arrange: Same value
        first, last, years = 100_000_000, 100_000_000, 5

        # Act
        result = cagr(first, last, years)

        # Assert: Should be 0%
        assert result == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.parametrize(
        "first,last,years,expected",
        [
            (None, 100, 5, None),  # first is None
            (100, None, 5, None),  # last is None
            (100, 200, 0, None),  # zero years
            (100, 200, -1, None),  # negative years
            (0, 100, 5, None),  # first is zero
            (-100, 100, 5, None),  # first is negative
            (100, 0, 5, None),  # last is zero
            (100, -100, 5, None),  # last is negative
        ],
    )
    def test_cagr_edge_cases(self, first, last, years, expected):
        """Test CAGR with various edge cases that should return None."""
        # Act
        result = cagr(first, last, years)

        # Assert
        assert result == expected

    def test_cagr_single_year(self):
        """Test CAGR over single year."""
        # Arrange
        first, last, years = 100, 120, 1

        # Act
        result = cagr(first, last, years)

        # Assert: 20% growth
        assert result == pytest.approx(0.20, rel=1e-2)

    def test_cagr_long_period(self):
        """Test CAGR over long time period (20 years)."""
        # Arrange: Microsoft-like growth
        first, last, years = 10_000_000_000, 200_000_000_000, 20

        # Act
        result = cagr(first, last, years)

        # Assert: Should be approximately 16.16%
        assert result == pytest.approx(0.1616, rel=1e-2)
        assert 0 <= result <= 1  # Sanity check


class TestComputeGrowthMetrics:
    """Test growth metrics computation (revenue and EPS CAGR)."""

    @patch("app.metrics.compute._fetch_is_series")
    def test_compute_growth_metrics_typical_case(self, mock_fetch):
        """Test growth metrics with typical financial data."""
        # Arrange: 10 years of data with steady growth
        mock_fetch.return_value = [
            (2014, 100_000_000_000, 1.50, None),
            (2015, 110_000_000_000, 1.65, None),
            (2016, 121_000_000_000, 1.82, None),
            (2017, 133_000_000_000, 2.00, None),
            (2018, 146_000_000_000, 2.20, None),
            (2019, 161_000_000_000, 2.42, None),
            (2020, 177_000_000_000, 2.66, None),
            (2021, 195_000_000_000, 2.93, None),
            (2022, 214_000_000_000, 3.22, None),
            (2023, 236_000_000_000, 3.54, None),
        ]

        # Act
        result = compute_growth_metrics("0000789019")

        # Assert: Should have all four metrics
        assert "rev_cagr_5y" in result
        assert "rev_cagr_10y" in result
        assert "eps_cagr_5y" in result
        assert "eps_cagr_10y" in result

        # Revenue CAGR should be around 10%
        assert result["rev_cagr_10y"] == pytest.approx(0.09, abs=0.02)

        # EPS CAGR should be around 9% (slightly less due to dilution)
        assert result["eps_cagr_10y"] == pytest.approx(0.09, abs=0.02)

    @patch("app.metrics.compute._fetch_is_series")
    def test_compute_growth_metrics_insufficient_data(self, mock_fetch):
        """Test with insufficient data points."""
        # Arrange: Only 1 year of data
        mock_fetch.return_value = [(2023, 100_000_000_000, 1.50, None)]

        # Act
        result = compute_growth_metrics("0000789019")

        # Assert: All metrics should be None
        assert result["rev_cagr_5y"] is None
        assert result["rev_cagr_10y"] is None
        assert result["eps_cagr_5y"] is None
        assert result["eps_cagr_10y"] is None

    @patch("app.metrics.compute._fetch_is_series")
    def test_compute_growth_metrics_no_data(self, mock_fetch):
        """Test with no financial data."""
        # Arrange
        mock_fetch.return_value = []

        # Act
        result = compute_growth_metrics("0000789019")

        # Assert
        assert result["rev_cagr_5y"] is None
        assert result["rev_cagr_10y"] is None
        assert result["eps_cagr_5y"] is None
        assert result["eps_cagr_10y"] is None

    @patch("app.metrics.compute._fetch_is_series")
    def test_compute_growth_metrics_sparse_data(self, mock_fetch):
        """Test with missing data points in series."""
        # Arrange: Some years have None values
        mock_fetch.return_value = [
            (2014, 100_000_000_000, 1.50, None),
            (2015, None, None, None),  # Missing data
            (2016, 121_000_000_000, 1.82, None),
            (2017, None, None, None),  # Missing data
            (2018, 146_000_000_000, 2.20, None),
            (2019, 161_000_000_000, 2.42, None),
            (2020, 177_000_000_000, 2.66, None),
            (2021, 195_000_000_000, 2.93, None),
            (2022, 214_000_000_000, 3.22, None),
            (2023, 236_000_000_000, 3.54, None),
        ]

        # Act
        result = compute_growth_metrics("0000789019")

        # Assert: Should still calculate metrics using available data
        assert result["rev_cagr_10y"] is not None
        assert result["eps_cagr_10y"] is not None


class TestOwnerEarningsSeries:
    """Test owner earnings (Free Cash Flow) calculations."""

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_owner_earnings_typical_case(self, mock_fetch):
        """Test owner earnings calculation with typical data."""
        # Arrange: CFO - CapEx = Owner Earnings
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 100_000_000_000,
                "capex": 15_000_000_000,
                "shares": 15_000_000_000,
                "ebit": None,
                "taxes": None,
                "debt": None,
                "equity": None,
                "cash": None,
                "revenue": None,
            }
        ]

        # Act
        result = owner_earnings_series("0000789019")

        # Assert
        assert len(result) == 1
        assert result[0]["fy"] == 2023
        assert result[0]["owner_earnings"] == 85_000_000_000
        assert result[0]["owner_earnings_ps"] == pytest.approx(5.67, rel=1e-2)

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_owner_earnings_negative_fcf(self, mock_fetch):
        """Test with negative free cash flow (CapEx > CFO)."""
        # Arrange
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 50_000_000_000,
                "capex": 80_000_000_000,
                "shares": 15_000_000_000,
                "ebit": None,
                "taxes": None,
                "debt": None,
                "equity": None,
                "cash": None,
                "revenue": None,
            }
        ]

        # Act
        result = owner_earnings_series("0000789019")

        # Assert: Should handle negative OE
        assert result[0]["owner_earnings"] == -30_000_000_000
        assert result[0]["owner_earnings_ps"] < 0

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_owner_earnings_missing_data(self, mock_fetch):
        """Test with missing CFO or CapEx data."""
        # Arrange
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": None,
                "capex": 15_000_000_000,
                "shares": 15_000_000_000,
                "ebit": None,
                "taxes": None,
                "debt": None,
                "equity": None,
                "cash": None,
                "revenue": None,
            }
        ]

        # Act
        result = owner_earnings_series("0000789019")

        # Assert: Should return None for OE
        assert result[0]["owner_earnings"] is None
        assert result[0]["owner_earnings_ps"] is None

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_owner_earnings_zero_shares(self, mock_fetch):
        """Test with zero shares outstanding."""
        # Arrange
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "cfo": 100_000_000_000,
                "capex": 15_000_000_000,
                "shares": 0,
                "ebit": None,
                "taxes": None,
                "debt": None,
                "equity": None,
                "cash": None,
                "revenue": None,
            }
        ]

        # Act
        result = owner_earnings_series("0000789019")

        # Assert: Should handle division by zero
        assert result[0]["owner_earnings_ps"] is None


class TestLatestOwnerEarningsPS:
    """Test latest owner earnings per share retrieval."""

    @patch("app.metrics.compute.owner_earnings_series")
    def test_latest_owner_earnings_ps_available(self, mock_series):
        """Test retrieving latest OE/PS when data exists."""
        # Arrange
        mock_series.return_value = [
            {"fy": 2021, "owner_earnings_ps": 4.50},
            {"fy": 2022, "owner_earnings_ps": 5.20},
            {"fy": 2023, "owner_earnings_ps": 5.67},
        ]

        # Act
        result = latest_owner_earnings_ps("0000789019")

        # Assert: Should return most recent value
        assert result == pytest.approx(5.67, rel=1e-6)

    @patch("app.metrics.compute.owner_earnings_series")
    def test_latest_owner_earnings_ps_none_at_end(self, mock_series):
        """Test when latest year has None value."""
        # Arrange
        mock_series.return_value = [
            {"fy": 2021, "owner_earnings_ps": 4.50},
            {"fy": 2022, "owner_earnings_ps": 5.20},
            {"fy": 2023, "owner_earnings_ps": None},
        ]

        # Act
        result = latest_owner_earnings_ps("0000789019")

        # Assert: Should skip None and return 2022 value
        assert result == pytest.approx(5.20, rel=1e-6)

    @patch("app.metrics.compute.owner_earnings_series")
    def test_latest_owner_earnings_ps_no_data(self, mock_series):
        """Test with no data available."""
        # Arrange
        mock_series.return_value = []

        # Act
        result = latest_owner_earnings_ps("0000789019")

        # Assert
        assert result is None


class TestROICSeries:
    """Test Return on Invested Capital calculations."""

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_roic_typical_case(self, mock_fetch):
        """Test ROIC calculation with typical financial data."""
        # Arrange: Strong ROIC company
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "ebit": 100_000_000_000,
                "taxes": 21_000_000_000,
                "debt": 50_000_000_000,
                "equity": 150_000_000_000,
                "cash": 30_000_000_000,
                "cfo": None,
                "capex": None,
                "shares": None,
                "revenue": None,
            }
        ]

        # Act
        result = roic_series("0000789019")

        # Assert
        # NOPAT = 100B * (1 - 0.21) = 79B
        # Invested Capital = 150B + 50B - 30B = 170B
        # ROIC = 79B / 170B = 0.465 (46.5%)
        assert len(result) == 1
        assert result[0]["fy"] == 2023
        assert result[0]["roic"] == pytest.approx(0.465, rel=1e-2)

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_roic_with_calculated_tax_rate(self, mock_fetch):
        """Test ROIC when tax rate needs to be calculated from data."""
        # Arrange
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "ebit": 100_000_000_000,
                "taxes": 25_000_000_000,  # 25% effective tax rate
                "debt": 50_000_000_000,
                "equity": 150_000_000_000,
                "cash": 30_000_000_000,
                "cfo": None,
                "capex": None,
                "shares": None,
                "revenue": None,
            }
        ]

        # Act
        result = roic_series("0000789019")

        # Assert: Should use 25% tax rate (capped at 35%)
        # NOPAT = 100B * (1 - 0.25) = 75B
        # ROIC = 75B / 170B = 0.441
        assert result[0]["roic"] == pytest.approx(0.441, rel=1e-2)

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_roic_missing_data(self, mock_fetch):
        """Test ROIC when required fields are missing."""
        # Arrange
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "ebit": None,
                "taxes": None,
                "debt": 50_000_000_000,
                "equity": 150_000_000_000,
                "cash": 30_000_000_000,
                "cfo": None,
                "capex": None,
                "shares": None,
                "revenue": None,
            }
        ]

        # Act
        result = roic_series("0000789019")

        # Assert: ROIC should be None
        assert result[0]["roic"] is None

    @patch("app.metrics.compute._fetch_cf_bs_for_roic")
    def test_roic_zero_invested_capital(self, mock_fetch):
        """Test ROIC when invested capital would be zero."""
        # Arrange: Equity + Debt = Cash (weird edge case)
        mock_fetch.return_value = [
            {
                "fy": 2023,
                "ebit": 100_000_000_000,
                "taxes": 21_000_000_000,
                "debt": 30_000_000_000,
                "equity": 70_000_000_000,
                "cash": 100_000_000_000,
                "cfo": None,
                "capex": None,
                "shares": None,
                "revenue": None,
            }
        ]

        # Act
        result = roic_series("0000789019")

        # Assert: Should handle zero invested capital
        assert result[0]["roic"] is None


class TestROICAverage:
    """Test average ROIC calculation."""

    @patch("app.metrics.compute.roic_series")
    def test_roic_average_10_years(self, mock_series):
        """Test 10-year average ROIC calculation."""
        # Arrange: Consistent 25% ROIC
        mock_series.return_value = [
            {"fy": y, "roic": 0.25} for y in range(2014, 2024)
        ]

        # Act
        result = roic_average("0000789019", years=10)

        # Assert
        assert result == pytest.approx(0.25, rel=1e-6)

    @patch("app.metrics.compute.roic_series")
    def test_roic_average_less_than_requested_years(self, mock_series):
        """Test when fewer years are available than requested."""
        # Arrange: Only 5 years of data
        mock_series.return_value = [
            {"fy": y, "roic": 0.20} for y in range(2019, 2024)
        ]

        # Act
        result = roic_average("0000789019", years=10)

        # Assert: Should use all available years
        assert result == pytest.approx(0.20, rel=1e-6)

    @patch("app.metrics.compute.roic_series")
    def test_roic_average_with_none_values(self, mock_series):
        """Test average calculation excluding None values."""
        # Arrange
        mock_series.return_value = [
            {"fy": 2019, "roic": 0.20},
            {"fy": 2020, "roic": None},
            {"fy": 2021, "roic": 0.25},
            {"fy": 2022, "roic": None},
            {"fy": 2023, "roic": 0.30},
        ]

        # Act
        result = roic_average("0000789019", years=10)

        # Assert: Should average only non-None values (0.20, 0.25, 0.30)
        assert result == pytest.approx(0.25, rel=1e-2)

    @patch("app.metrics.compute.roic_series")
    def test_roic_average_no_valid_data(self, mock_series):
        """Test when no valid ROIC data exists."""
        # Arrange
        mock_series.return_value = [
            {"fy": 2023, "roic": None}
        ]

        # Act
        result = roic_average("0000789019", years=10)

        # Assert
        assert result is None


class TestLatestDebtToEquity:
    """Test debt-to-equity ratio calculation."""

    @patch("app.metrics.compute.execute")
    def test_latest_debt_to_equity_typical(self, mock_execute):
        """Test D/E calculation with typical balance sheet data."""
        # Arrange
        mock_result = Mock()
        mock_result.first.return_value = (50_000_000_000, 100_000_000_000)
        mock_execute.return_value = mock_result

        # Act
        result = latest_debt_to_equity("0000789019")

        # Assert: 50B / 100B = 0.5
        assert result == pytest.approx(0.5, rel=1e-6)

    @patch("app.metrics.compute.execute")
    def test_latest_debt_to_equity_zero_equity(self, mock_execute):
        """Test with zero equity (edge case)."""
        # Arrange
        mock_result = Mock()
        mock_result.first.return_value = (50_000_000_000, 0)
        mock_execute.return_value = mock_result

        # Act
        result = latest_debt_to_equity("0000789019")

        # Assert: Should handle division by zero
        assert result is None

    @patch("app.metrics.compute.execute")
    def test_latest_debt_to_equity_no_data(self, mock_execute):
        """Test when no balance sheet data exists."""
        # Arrange
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_execute.return_value = mock_result

        # Act
        result = latest_debt_to_equity("0000789019")

        # Assert
        assert result is None


class TestLatestOwnerEarningsGrowth:
    """Test owner earnings CAGR calculation."""

    @patch("app.metrics.compute.owner_earnings_series")
    def test_owner_earnings_growth_5_year(self, mock_series):
        """Test 5-year owner earnings growth calculation."""
        # Arrange: 10% annual growth
        mock_series.return_value = [
            {"fy": 2019, "owner_earnings": 50_000_000_000},
            {"fy": 2020, "owner_earnings": 55_000_000_000},
            {"fy": 2021, "owner_earnings": 60_500_000_000},
            {"fy": 2022, "owner_earnings": 66_550_000_000},
            {"fy": 2023, "owner_earnings": 73_205_000_000},
        ]

        # Act
        result = latest_owner_earnings_growth("0000789019")

        # Assert: Should be approximately 10%
        assert result == pytest.approx(0.10, abs=0.01)

    @patch("app.metrics.compute.owner_earnings_series")
    def test_owner_earnings_growth_insufficient_data(self, mock_series):
        """Test with only 1 data point."""
        # Arrange
        mock_series.return_value = [
            {"fy": 2023, "owner_earnings": 50_000_000_000}
        ]

        # Act
        result = latest_owner_earnings_growth("0000789019")

        # Assert
        assert result is None


class TestMarginStability:
    """Test EBIT margin stability calculation."""

    @patch("app.metrics.compute._fetch_is_series")
    def test_margin_stability_consistent(self, mock_fetch):
        """Test with very consistent margins."""
        # Arrange: Consistent 20% EBIT margin
        mock_fetch.return_value = [
            (2019, 100_000_000_000, None, 20_000_000_000),
            (2020, 110_000_000_000, None, 22_000_000_000),
            (2021, 121_000_000_000, None, 24_200_000_000),
            (2022, 133_000_000_000, None, 26_600_000_000),
            (2023, 146_000_000_000, None, 29_200_000_000),
        ]

        # Act
        result = margin_stability("0000789019")

        # Assert: Should be close to 1.0 (very stable)
        assert result == pytest.approx(1.0, abs=0.05)

    @patch("app.metrics.compute._fetch_is_series")
    def test_margin_stability_volatile(self, mock_fetch):
        """Test with volatile margins."""
        # Arrange: Margins vary significantly
        mock_fetch.return_value = [
            (2019, 100_000_000_000, None, 10_000_000_000),  # 10%
            (2020, 110_000_000_000, None, 33_000_000_000),  # 30%
            (2021, 121_000_000_000, None, 12_100_000_000),  # 10%
            (2022, 133_000_000_000, None, 39_900_000_000),  # 30%
            (2023, 146_000_000_000, None, 14_600_000_000),  # 10%
        ]

        # Act
        result = margin_stability("0000789019")

        # Assert: Should be lower (less stable)
        assert 0 <= result < 0.8

    @patch("app.metrics.compute._fetch_is_series")
    def test_margin_stability_insufficient_data(self, mock_fetch):
        """Test with fewer than 3 data points."""
        # Arrange
        mock_fetch.return_value = [
            (2022, 100_000_000_000, None, 20_000_000_000),
            (2023, 110_000_000_000, None, 22_000_000_000),
        ]

        # Act
        result = margin_stability("0000789019")

        # Assert
        assert result is None


class TestTimeseriesAll:
    """Test aggregated timeseries data retrieval."""

    @patch("app.metrics.compute.revenue_eps_series")
    @patch("app.metrics.compute.owner_earnings_series")
    @patch("app.metrics.compute.roic_series")
    @patch("app.metrics.compute.coverage_series")
    def test_timeseries_all_aggregation(
        self, mock_cov, mock_roic, mock_oe, mock_is
    ):
        """Test that all timeseries data is properly aggregated."""
        # Arrange
        mock_is.return_value = [{"fy": 2023, "revenue": 1000, "eps": 5.0}]
        mock_oe.return_value = [{"fy": 2023, "owner_earnings": 800}]
        mock_roic.return_value = [{"fy": 2023, "roic": 0.25}]
        mock_cov.return_value = [{"fy": 2023, "coverage": 10.5}]

        # Act
        result = timeseries_all("0000789019")

        # Assert: Should have all four series
        assert "is" in result
        assert "owner_earnings" in result
        assert "roic" in result
        assert "coverage" in result
        assert len(result["is"]) == 1
        assert result["is"][0]["fy"] == 2023


# =============================================================================
# Phase B: New Metrics Functions Tests
# =============================================================================

class TestGrossMarginSeries:
    """Test B1: gross_margin_series function."""

    @patch("app.metrics.compute.execute")
    def test_gross_margin_from_gross_profit(self, mock_execute):
        """Test gross margin calculation using gross_profit directly."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100000000, 40000000, None),  # fy, revenue, gross_profit, cogs
            (2022, 120000000, 50000000, None),
            (2023, 150000000, 65000000, None),
        ]

        result = gross_margin_series("0000789019")

        assert len(result) == 3
        assert result[0]["fy"] == 2021
        assert result[0]["gross_margin"] == pytest.approx(0.40, rel=1e-2)
        assert result[2]["gross_margin"] == pytest.approx(0.4333, rel=1e-2)

    @patch("app.metrics.compute.execute")
    def test_gross_margin_from_cogs(self, mock_execute):
        """Test gross margin calculation using revenue - cogs when gross_profit is None."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100000000, None, 60000000),  # fy, revenue, gross_profit, cogs
            (2022, 120000000, None, 70000000),
        ]

        result = gross_margin_series("0000789019")

        assert len(result) == 2
        assert result[0]["gross_margin"] == pytest.approx(0.40, rel=1e-2)  # (100-60)/100
        assert result[1]["gross_margin"] == pytest.approx(0.4167, rel=1e-2)  # (120-70)/120

    @patch("app.metrics.compute.execute")
    def test_gross_margin_missing_data(self, mock_execute):
        """Test gross margin returns None when both gross_profit and cogs are missing."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100000000, None, None),
        ]

        result = gross_margin_series("0000789019")

        assert len(result) == 1
        assert result[0]["gross_margin"] is None

    @patch("app.metrics.compute.execute")
    def test_gross_margin_zero_revenue(self, mock_execute):
        """Test gross margin returns None when revenue is zero."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 0, 40000000, None),
        ]

        result = gross_margin_series("0000789019")

        assert result[0]["gross_margin"] is None


class TestRevenueVolatility:
    """Test B2: revenue_volatility function."""

    @patch("app.metrics.compute._fetch_is_series")
    def test_revenue_volatility_stable_growth(self, mock_fetch):
        """Test volatility with stable growth rates."""
        # 10% growth each year - very stable
        mock_fetch.return_value = [
            (2019, 100000000, 5.0, 20000000),
            (2020, 110000000, 5.5, 22000000),
            (2021, 121000000, 6.0, 24000000),
            (2022, 133100000, 6.5, 26000000),
            (2023, 146410000, 7.0, 28000000),
        ]

        result = revenue_volatility("0000789019")

        # All growth rates are 10%, so std dev should be ~0
        assert result == pytest.approx(0.0, abs=1e-6)

    @patch("app.metrics.compute._fetch_is_series")
    def test_revenue_volatility_variable_growth(self, mock_fetch):
        """Test volatility with variable growth rates."""
        mock_fetch.return_value = [
            (2019, 100000000, 5.0, 20000000),
            (2020, 120000000, 5.5, 22000000),  # 20% growth
            (2021, 108000000, 6.0, 24000000),  # -10% growth
            (2022, 140400000, 6.5, 26000000),  # 30% growth
            (2023, 147420000, 7.0, 28000000),  # 5% growth
        ]

        result = revenue_volatility("0000789019")

        # Growth rates: 20%, -10%, 30%, 5% - high volatility
        assert result is not None
        assert result > 0.1  # Should be significant volatility

    @patch("app.metrics.compute._fetch_is_series")
    def test_revenue_volatility_insufficient_data(self, mock_fetch):
        """Test volatility returns None with insufficient data."""
        mock_fetch.return_value = [
            (2022, 100000000, 5.0, 20000000),
            (2023, 110000000, 5.5, 22000000),
        ]

        result = revenue_volatility("0000789019")

        assert result is None  # Need at least 3 years


class TestComputeGrowthMetricsExtended:
    """Test B3: compute_growth_metrics_extended function."""

    @patch("app.metrics.compute._fetch_is_series")
    def test_extended_growth_metrics_all_windows(self, mock_fetch):
        """Test that all CAGR windows are calculated."""
        mock_fetch.return_value = [
            (2014, 50000000, 2.0, 10000000),
            (2015, 55000000, 2.2, 11000000),
            (2016, 60000000, 2.4, 12000000),
            (2017, 66000000, 2.6, 13000000),
            (2018, 72000000, 2.9, 14000000),
            (2019, 80000000, 3.2, 16000000),
            (2020, 88000000, 3.5, 17000000),
            (2021, 97000000, 3.9, 19000000),
            (2022, 107000000, 4.3, 21000000),
            (2023, 118000000, 4.7, 23000000),
        ]

        result = compute_growth_metrics_extended("0000789019")

        # Should have all 8 metrics
        assert "rev_cagr_1y" in result
        assert "rev_cagr_3y" in result
        assert "rev_cagr_5y" in result
        assert "rev_cagr_10y" in result
        assert "eps_cagr_1y" in result
        assert "eps_cagr_3y" in result
        assert "eps_cagr_5y" in result
        assert "eps_cagr_10y" in result

        # All should be positive growth
        for key, value in result.items():
            if value is not None:
                assert value > 0, f"{key} should show positive growth"

    @patch("app.metrics.compute._fetch_is_series")
    def test_extended_growth_metrics_insufficient_data(self, mock_fetch):
        """Test returns None values with insufficient data."""
        mock_fetch.return_value = [(2023, 100000000, 5.0, 20000000)]

        result = compute_growth_metrics_extended("0000789019")

        # All should be None with only 1 year of data
        for value in result.values():
            assert value is None


class TestNetDebtSeries:
    """Test B4: net_debt_series function."""

    @patch("app.metrics.compute.execute")
    def test_net_debt_positive(self, mock_execute):
        """Test net debt when company has more debt than cash."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 50000000000, 10000000000),  # fy, total_debt, cash
            (2022, 45000000000, 12000000000),
            (2023, 42000000000, 15000000000),
        ]

        result = net_debt_series("0000789019")

        assert len(result) == 3
        assert result[0]["net_debt"] == 40000000000  # 50B - 10B
        assert result[2]["net_debt"] == 27000000000  # 42B - 15B

    @patch("app.metrics.compute.execute")
    def test_net_debt_negative(self, mock_execute):
        """Test net debt when company has more cash than debt (net cash position)."""
        mock_execute.return_value.fetchall.return_value = [
            (2023, 10000000000, 50000000000),  # More cash than debt
        ]

        result = net_debt_series("0000789019")

        assert result[0]["net_debt"] == -40000000000  # Negative = net cash

    @patch("app.metrics.compute.execute")
    def test_net_debt_missing_data(self, mock_execute):
        """Test net debt returns None when data is missing."""
        mock_execute.return_value.fetchall.return_value = [
            (2023, None, 50000000000),
        ]

        result = net_debt_series("0000789019")

        assert result[0]["net_debt"] is None


class TestShareCountTrend:
    """Test B5: share_count_trend function."""

    @patch("app.metrics.compute.execute")
    def test_share_count_buybacks(self, mock_execute):
        """Test share count trend with buybacks (decreasing shares)."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 8000000000),
            (2022, 7600000000),  # -5% buyback
            (2023, 7220000000),  # -5% buyback
        ]

        result = share_count_trend("0000789019")

        assert len(result) == 3
        assert result[0]["yoy_change"] is None  # First year has no prior
        assert result[1]["yoy_change"] == pytest.approx(-0.05, rel=1e-2)
        assert result[2]["yoy_change"] == pytest.approx(-0.05, rel=1e-2)

    @patch("app.metrics.compute.execute")
    def test_share_count_dilution(self, mock_execute):
        """Test share count trend with dilution (increasing shares)."""
        mock_execute.return_value.fetchall.return_value = [
            (2021, 1000000000),
            (2022, 1100000000),  # +10% dilution
            (2023, 1210000000),  # +10% dilution
        ]

        result = share_count_trend("0000789019")

        assert result[1]["yoy_change"] == pytest.approx(0.10, rel=1e-2)
        assert result[2]["yoy_change"] == pytest.approx(0.10, rel=1e-2)


class TestRoicPersistenceScore:
    """Test B6: roic_persistence_score function (Option C: >=15% AND stable)."""

    @patch("app.metrics.compute.roic_series")
    def test_roic_persistence_excellent(self, mock_roic):
        """Test score 5 for excellent ROIC (all years >=15%, very stable)."""
        # All years above 15%, very low variance
        mock_roic.return_value = [
            {"fy": 2019, "roic": 0.20},
            {"fy": 2020, "roic": 0.21},
            {"fy": 2021, "roic": 0.20},
            {"fy": 2022, "roic": 0.21},
            {"fy": 2023, "roic": 0.20},
        ]

        result = roic_persistence_score("0000789019")

        assert result == 5  # All above threshold + bonus for stability

    @patch("app.metrics.compute.roic_series")
    def test_roic_persistence_good(self, mock_roic):
        """Test score 4 for good ROIC (4 years >=15%)."""
        mock_roic.return_value = [
            {"fy": 2019, "roic": 0.20},
            {"fy": 2020, "roic": 0.18},
            {"fy": 2021, "roic": 0.12},  # Below threshold
            {"fy": 2022, "roic": 0.17},
            {"fy": 2023, "roic": 0.19},
        ]

        result = roic_persistence_score("0000789019")

        assert result == 4  # 4 years above threshold

    @patch("app.metrics.compute.roic_series")
    def test_roic_persistence_penalized_for_volatility(self, mock_roic):
        """Test score penalized for high ROIC variance."""
        # All above 15% but very volatile (CV > 0.3)
        mock_roic.return_value = [
            {"fy": 2019, "roic": 0.15},
            {"fy": 2020, "roic": 0.35},
            {"fy": 2021, "roic": 0.16},
            {"fy": 2022, "roic": 0.40},
            {"fy": 2023, "roic": 0.18},
        ]

        result = roic_persistence_score("0000789019")

        # All 5 above threshold but penalized for volatility
        assert result == 4  # 5 - 1 penalty

    @patch("app.metrics.compute.roic_series")
    def test_roic_persistence_poor(self, mock_roic):
        """Test low score for poor ROIC performance."""
        mock_roic.return_value = [
            {"fy": 2019, "roic": 0.08},
            {"fy": 2020, "roic": 0.10},
            {"fy": 2021, "roic": 0.09},
            {"fy": 2022, "roic": 0.11},
            {"fy": 2023, "roic": 0.12},
        ]

        result = roic_persistence_score("0000789019")

        assert result == 0  # No years above 15%

    @patch("app.metrics.compute.roic_series")
    def test_roic_persistence_insufficient_data(self, mock_roic):
        """Test returns None with insufficient data."""
        mock_roic.return_value = [{"fy": 2023, "roic": 0.20}]

        result = roic_persistence_score("0000789019")

        assert result is None


class TestQualityScores:
    """Test quality_scores aggregator function."""

    @patch("app.metrics.compute.gross_margin_series")
    @patch("app.metrics.compute.revenue_volatility")
    @patch("app.metrics.compute.compute_growth_metrics_extended")
    @patch("app.metrics.compute.net_debt_series")
    @patch("app.metrics.compute.share_count_trend")
    @patch("app.metrics.compute.roic_persistence_score")
    def test_quality_scores_aggregation(
        self,
        mock_roic_score,
        mock_shares,
        mock_net_debt,
        mock_growth,
        mock_vol,
        mock_gm,
    ):
        """Test that quality_scores aggregates all metrics correctly."""
        # Need 6+ years of data for gross_margin_trend calculation
        # (compares avg of first 3 vs avg of last 3)
        mock_gm.return_value = [
            {"fy": 2018, "gross_margin": 0.38},
            {"fy": 2019, "gross_margin": 0.39},
            {"fy": 2020, "gross_margin": 0.40},
            {"fy": 2021, "gross_margin": 0.42},
            {"fy": 2022, "gross_margin": 0.44},
            {"fy": 2023, "gross_margin": 0.45},
        ]
        mock_vol.return_value = 0.05
        mock_growth.return_value = {
            "rev_cagr_1y": 0.10,
            "rev_cagr_3y": 0.12,
            "rev_cagr_5y": 0.15,
            "rev_cagr_10y": 0.18,
            "eps_cagr_1y": 0.08,
            "eps_cagr_3y": 0.10,
            "eps_cagr_5y": 0.12,
            "eps_cagr_10y": 0.14,
        }
        mock_net_debt.return_value = [
            {"fy": 2021, "net_debt": 10000000000},
            {"fy": 2022, "net_debt": 8000000000},
            {"fy": 2023, "net_debt": 5000000000},
        ]
        mock_shares.return_value = [
            {"fy": 2021, "shares": 8000000000, "yoy_change": None},
            {"fy": 2022, "shares": 7600000000, "yoy_change": -0.05},
            {"fy": 2023, "shares": 7220000000, "yoy_change": -0.05},
        ]
        mock_roic_score.return_value = 5

        result = quality_scores("0000789019")

        # Verify all expected keys are present
        assert "gross_margin_series" in result
        assert "latest_gross_margin" in result
        assert "gross_margin_trend" in result
        assert "revenue_volatility" in result
        assert "growth_metrics" in result
        assert "net_debt_series" in result
        assert "latest_net_debt" in result
        assert "share_count_trend" in result
        assert "avg_share_dilution_3y" in result
        assert "roic_persistence_score" in result

        # Verify computed values
        assert result["latest_gross_margin"] == 0.45
        # Trend: avg(0.42, 0.44, 0.45) - avg(0.38, 0.39, 0.40) = 0.4367 - 0.39 = 0.0467
        assert result["gross_margin_trend"] == pytest.approx(0.0467, rel=1e-2)
        assert result["revenue_volatility"] == 0.05
        assert result["latest_net_debt"] == 5000000000
        assert result["avg_share_dilution_3y"] == pytest.approx(-0.05, rel=1e-2)
        assert result["roic_persistence_score"] == 5
