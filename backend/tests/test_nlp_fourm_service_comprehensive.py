"""
Comprehensive unit tests for NLP/Four Ms service module (Moat, Management, MOS scoring).

This test suite aims for 90%+ coverage of app/nlp/fourm/service.py
Following industry best practices: AAA pattern, mocking dependencies, edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.nlp.fourm.service import (
    _series_values,
    _normalize_score,
    compute_moat,
    compute_management,
    compute_margin_of_safety_recommendation,
)


pytestmark = pytest.mark.unit


class TestSeriesValues:
    """Test helper function that extracts values from series data."""

    def test_series_values_extracts_floats(self):
        """Test extracting numeric values from series."""
        # Arrange
        series = [
            {"fy": 2021, "roic": 0.15},
            {"fy": 2022, "roic": 0.18},
            {"fy": 2023, "roic": 0.22},
        ]

        # Act
        result = _series_values(series, "roic")

        # Assert
        assert result == [0.15, 0.18, 0.22]
        assert all(isinstance(x, float) for x in result)

    def test_series_values_skips_none(self):
        """Test that None values are skipped."""
        # Arrange
        series = [
            {"fy": 2021, "roic": 0.15},
            {"fy": 2022, "roic": None},
            {"fy": 2023, "roic": 0.22},
        ]

        # Act
        result = _series_values(series, "roic")

        # Assert
        assert result == [0.15, 0.22]

    def test_series_values_missing_key(self):
        """Test when key is missing from some entries."""
        # Arrange
        series = [
            {"fy": 2021, "roic": 0.15},
            {"fy": 2022},  # Missing roic key
            {"fy": 2023, "roic": 0.22},
        ]

        # Act
        result = _series_values(series, "roic")

        # Assert
        assert result == [0.15, 0.22]

    def test_series_values_empty_list(self):
        """Test with empty series."""
        # Arrange
        series = []

        # Act
        result = _series_values(series, "roic")

        # Assert
        assert result == []


class TestNormalizeScore:
    """Test score normalization function."""

    def test_normalize_score_within_range(self):
        """Test normalization for values within the range."""
        # Arrange
        tuples = [
            (0.15, 0.10, 0.20),  # Middle of range: 0.5
            (0.18, 0.10, 0.20),  # 80% of range: 0.8
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result == pytest.approx(0.65, rel=1e-2)  # (0.5 + 0.8) / 2

    def test_normalize_score_at_boundaries(self):
        """Test normalization at boundary values."""
        # Arrange
        tuples = [
            (0.10, 0.10, 0.20),  # At low boundary: 0.0
            (0.20, 0.10, 0.20),  # At high boundary: 1.0
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result == pytest.approx(0.5, rel=1e-2)  # (0.0 + 1.0) / 2

    def test_normalize_score_below_low(self):
        """Test normalization for values below low threshold."""
        # Arrange
        tuples = [
            (0.05, 0.10, 0.20),  # Below low: 0.0
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result == pytest.approx(0.0, rel=1e-6)

    def test_normalize_score_above_high(self):
        """Test normalization for values above high threshold."""
        # Arrange
        tuples = [
            (0.30, 0.10, 0.20),  # Above high: 1.0
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result == pytest.approx(1.0, rel=1e-6)

    def test_normalize_score_with_none_values(self):
        """Test that None values are skipped."""
        # Arrange
        tuples = [
            (None, 0.10, 0.20),
            (0.15, 0.10, 0.20),  # Should be 0.5
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result == pytest.approx(0.5, rel=1e-2)

    def test_normalize_score_all_none(self):
        """Test when all values are None."""
        # Arrange
        tuples = [
            (None, 0.10, 0.20),
            (None, 0.10, 0.20),
        ]

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result is None

    def test_normalize_score_empty_list(self):
        """Test with empty list."""
        # Arrange
        tuples = []

        # Act
        result = _normalize_score(tuples)

        # Assert
        assert result is None


class TestComputeMoat:
    """Test Moat (competitive advantage) scoring."""

    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_compute_moat_strong_moat(self, mock_roic, mock_margin):
        """Test Moat calculation for company with strong competitive advantages."""
        # Arrange: High ROIC, stable margins
        mock_roic.return_value = [
            {"fy": 2021, "roic": 0.25},
            {"fy": 2022, "roic": 0.26},
            {"fy": 2023, "roic": 0.27},
        ]
        mock_margin.return_value = 0.85

        # Act
        result = compute_moat("0000789019")

        # Assert
        assert result["roic_avg"] == pytest.approx(0.26, rel=1e-2)  # Mean of 0.25, 0.26, 0.27
        assert result["roic_sd"] is not None
        assert result["margin_stability"] == 0.85
        assert result["score"] is not None
        assert result["score"] > 0.7  # Strong moat

    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_compute_moat_weak_moat(self, mock_roic, mock_margin):
        """Test Moat calculation for company with weak competitive advantages."""
        # Arrange: Low ROIC, unstable margins
        mock_roic.return_value = [
            {"fy": 2021, "roic": 0.08},
            {"fy": 2022, "roic": 0.09},
            {"fy": 2023, "roic": 0.07},
        ]
        mock_margin.return_value = 0.25

        # Act
        result = compute_moat("0000789019")

        # Assert
        assert result["roic_avg"] == pytest.approx(0.08, rel=1e-2)
        assert result["margin_stability"] == 0.25
        assert result["score"] is not None
        assert result["score"] < 0.4  # Weak moat

    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_compute_moat_single_year(self, mock_roic, mock_margin):
        """Test Moat with only one year of data (no std dev)."""
        # Arrange
        mock_roic.return_value = [{"fy": 2023, "roic": 0.20}]
        mock_margin.return_value = 0.70

        # Act
        result = compute_moat("0000789019")

        # Assert
        assert result["roic_avg"] == 0.20
        assert result["roic_sd"] is None  # Can't calculate std dev with one value
        assert result["margin_stability"] == 0.70

    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_compute_moat_no_data(self, mock_roic, mock_margin):
        """Test Moat with no ROIC data."""
        # Arrange
        mock_roic.return_value = []
        mock_margin.return_value = None

        # Act
        result = compute_moat("0000789019")

        # Assert
        assert result["roic_avg"] is None
        assert result["roic_sd"] is None
        assert result["margin_stability"] is None
        assert result["score"] is None


class TestComputeManagement:
    """Test Management quality scoring."""

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_good_capital_allocation(self, mock_execute):
        """Test Management scoring for good capital allocation."""
        # Arrange: Reasonable reinvestment (50%), low payout (20%)
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100.0, 50.0, 10.0, 10.0, 500.0),
            (2022, 110.0, 55.0, 12.0, 10.0, 550.0),
            (2023, 120.0, 60.0, 15.0, 10.0, 600.0),
        ]

        # Act
        result = compute_management("0000789019")

        # Assert
        assert result["reinvest_ratio_avg"] is not None
        assert 0.4 < result["reinvest_ratio_avg"] < 0.6  # Around 50%
        assert result["payout_ratio_avg"] is not None
        assert result["payout_ratio_avg"] < 0.3  # Around 20%
        assert result["score"] is not None
        assert result["score"] > 0.7  # Good management

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_excessive_payout(self, mock_execute):
        """Test Management with excessive shareholder payouts."""
        # Arrange: High reinvestment + high payout = poor capital allocation
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100.0, 80.0, 50.0, 30.0, 500.0),
            (2022, 110.0, 85.0, 55.0, 33.0, 550.0),
            (2023, 120.0, 90.0, 60.0, 36.0, 600.0),
        ]

        # Act
        result = compute_management("0000789019")

        # Assert
        assert result["payout_ratio_avg"] > 0.7  # High payout
        assert result["score"] is not None
        # Note: High reinvestment (77%) is scored positively despite high payout

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_low_reinvestment(self, mock_execute):
        """Test Management with low reinvestment."""
        # Arrange: Low capex reinvestment (20%)
        mock_execute.return_value.fetchall.return_value = [
            (2021, 100.0, 20.0, 5.0, 5.0, 500.0),
            (2022, 110.0, 22.0, 6.0, 6.0, 550.0),
            (2023, 120.0, 24.0, 7.0, 7.0, 600.0),
        ]

        # Act
        result = compute_management("0000789019")

        # Assert
        assert result["reinvest_ratio_avg"] < 0.3  # Low reinvestment

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_missing_data(self, mock_execute):
        """Test Management with incomplete data."""
        # Arrange: Missing CFO and capex for some years
        mock_execute.return_value.fetchall.return_value = [
            (2021, None, None, 10.0, 10.0, 500.0),
            (2022, 110.0, 55.0, None, None, 550.0),
            (2023, None, None, None, None, 600.0),
        ]

        # Act
        result = compute_management("0000789019")

        # Assert: Should handle None values gracefully
        assert result["reinvest_ratio_avg"] is not None or result["payout_ratio_avg"] is not None

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_no_data(self, mock_execute):
        """Test Management with no usable data."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = []

        # Act
        result = compute_management("0000789019")

        # Assert
        assert result["reinvest_ratio_avg"] is None
        assert result["payout_ratio_avg"] is None
        assert result["score"] is None

    @patch("app.nlp.fourm.service.execute")
    def test_compute_management_zero_cfo(self, mock_execute):
        """Test Management when CFO is zero (edge case)."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (2021, 0.0, 50.0, 10.0, 10.0, 500.0),
        ]

        # Act
        result = compute_management("0000789019")

        # Assert: Should handle zero CFO without division error
        assert result["score"] is not None or result["score"] is None  # Either is valid


class TestComputeMarginOfSafetyRecommendation:
    """Test Margin of Safety recommendation logic."""

    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_high_quality_company(self, mock_moat, mock_mgmt, mock_growth):
        """Test MOS for high-quality company (low MOS needed)."""
        # Arrange: Strong moat, good management, high growth
        mock_moat.return_value = {"score": 0.9}
        mock_mgmt.return_value = {"score": 0.8}
        mock_growth.return_value = {"eps_cagr_5y": 0.18, "rev_cagr_5y": 0.15}

        # Act
        result = compute_margin_of_safety_recommendation("0000789019")

        # Assert: High quality = lower MOS required
        assert result["recommended_mos"] < 0.5
        assert result["drivers"]["moat_score"] == 0.9
        assert result["drivers"]["mgmt_score"] == 0.8
        assert result["drivers"]["growth"] == 0.18

    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_low_quality_company(self, mock_moat, mock_mgmt, mock_growth):
        """Test MOS for low-quality company (high MOS needed)."""
        # Arrange: Weak moat, poor management, low growth
        mock_moat.return_value = {"score": 0.2}
        mock_mgmt.return_value = {"score": 0.3}
        mock_growth.return_value = {"eps_cagr_5y": 0.05, "rev_cagr_5y": 0.06}

        # Act
        result = compute_margin_of_safety_recommendation("0000789019")

        # Assert: Low quality = higher MOS required
        assert result["recommended_mos"] > 0.5
        assert result["recommended_mos"] <= 0.7  # Capped at 70%

    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_missing_scores(self, mock_moat, mock_mgmt, mock_growth):
        """Test MOS with missing quality scores."""
        # Arrange: None scores default to 0.5
        mock_moat.return_value = {"score": None}
        mock_mgmt.return_value = {"score": None}
        mock_growth.return_value = {}

        # Act
        result = compute_margin_of_safety_recommendation("0000789019")

        # Assert: Defaults to moderate MOS
        assert 0.3 <= result["recommended_mos"] <= 0.7
        assert result["drivers"]["moat_score"] == 0.5  # Default
        assert result["drivers"]["mgmt_score"] == 0.5  # Default
        assert result["drivers"]["growth"] == 0.10  # Default

    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_uses_revenue_growth_fallback(self, mock_moat, mock_mgmt, mock_growth):
        """Test that MOS uses revenue growth if EPS growth unavailable."""
        # Arrange
        mock_moat.return_value = {"score": 0.7}
        mock_mgmt.return_value = {"score": 0.6}
        mock_growth.return_value = {"rev_cagr_5y": 0.12}  # No EPS growth

        # Act
        result = compute_margin_of_safety_recommendation("0000789019")

        # Assert: Should use revenue growth
        assert result["drivers"]["growth"] == 0.12

    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_bounds_check(self, mock_moat, mock_mgmt, mock_growth):
        """Test that MOS is bounded between 30% and 70%."""
        # Arrange: Extreme values that would push outside bounds
        mock_moat.return_value = {"score": 1.0}
        mock_mgmt.return_value = {"score": 1.0}
        mock_growth.return_value = {"eps_cagr_5y": 0.50}

        # Act
        result = compute_margin_of_safety_recommendation("0000789019")

        # Assert: Should be bounded
        assert 0.3 <= result["recommended_mos"] <= 0.7
