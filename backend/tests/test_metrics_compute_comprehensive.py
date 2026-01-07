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
