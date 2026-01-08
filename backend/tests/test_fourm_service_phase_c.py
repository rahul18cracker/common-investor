"""
Phase C Unit Tests: Four Ms Service Enhancements

Tests for:
- C1: Gross margin trajectory in compute_moat()
- C2: ROIC persistence score in compute_moat()
- C3: compute_balance_sheet_resilience()
- C4: Pricing power indicator
"""
import pytest
from unittest.mock import patch, MagicMock
from app.nlp.fourm.service import (
    compute_moat,
    compute_balance_sheet_resilience,
    compute_margin_of_safety_recommendation,
    _compute_pricing_power,
)


pytestmark = [pytest.mark.unit]


# =============================================================================
# C4: Pricing Power Tests
# =============================================================================

class TestComputePricingPower:
    """Test the pricing power calculation helper function."""

    def test_pricing_power_high_margin_stable_improving(self):
        """Test pricing power with excellent metrics."""
        # High margin (60%), stable (0.9), improving trend (+3%)
        result = _compute_pricing_power(0.60, 0.9, 0.03)
        
        assert result is not None
        assert result > 0.8  # Should be high score

    def test_pricing_power_low_margin(self):
        """Test pricing power with low gross margin."""
        # Low margin (15%), stable, flat trend
        result = _compute_pricing_power(0.15, 0.8, 0.0)
        
        assert result is not None
        assert result < 0.5  # Should be lower score due to low margin

    def test_pricing_power_declining_trend(self):
        """Test pricing power with declining gross margin trend."""
        # Good margin (40%), stable, but declining (-6%)
        result = _compute_pricing_power(0.40, 0.8, -0.06)
        
        assert result is not None
        # Declining trend should hurt score
        assert result < 0.7

    def test_pricing_power_unstable(self):
        """Test pricing power with unstable gross margins."""
        # Good margin (40%), unstable (0.3), flat trend
        result = _compute_pricing_power(0.40, 0.3, 0.0)
        
        assert result is not None
        # Instability should hurt score
        assert result < 0.7

    def test_pricing_power_all_none(self):
        """Test pricing power with no data."""
        result = _compute_pricing_power(None, None, None)
        assert result is None

    def test_pricing_power_partial_data(self):
        """Test pricing power with only margin available."""
        result = _compute_pricing_power(0.45, None, None)
        
        assert result is not None
        # Should still calculate based on available data
        assert 0.0 <= result <= 1.0

    def test_pricing_power_boundary_values(self):
        """Test pricing power at boundary values."""
        # At 20% margin boundary
        result_low = _compute_pricing_power(0.20, 0.5, 0.0)
        assert result_low is not None
        
        # At 50% margin boundary
        result_high = _compute_pricing_power(0.50, 0.5, 0.0)
        assert result_high is not None
        assert result_high > result_low


# =============================================================================
# C1 & C2: Enhanced compute_moat() Tests
# =============================================================================

class TestComputeMoatPhaseC:
    """Test Phase C enhancements to compute_moat()."""

    @patch("app.nlp.fourm.service.roic_persistence_score")
    @patch("app.nlp.fourm.service.gross_margin_series")
    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_moat_includes_gross_margin_trend(
        self, mock_roic, mock_margin, mock_gm, mock_persist
    ):
        """Test that moat includes gross margin trajectory (C1)."""
        # Arrange
        mock_roic.return_value = [
            {"fy": 2019, "roic": 0.18},
            {"fy": 2020, "roic": 0.20},
            {"fy": 2021, "roic": 0.22},
        ]
        mock_margin.return_value = 0.7
        mock_gm.return_value = [
            {"fy": 2018, "gross_margin": 0.38},
            {"fy": 2019, "gross_margin": 0.39},
            {"fy": 2020, "gross_margin": 0.40},
            {"fy": 2021, "gross_margin": 0.42},
            {"fy": 2022, "gross_margin": 0.44},
            {"fy": 2023, "gross_margin": 0.45},
        ]
        mock_persist.return_value = 4

        # Act
        result = compute_moat("test_cik")

        # Assert
        assert "gross_margin_trend" in result
        assert result["gross_margin_trend"] is not None
        # Trend should be positive (improving)
        assert result["gross_margin_trend"] > 0

    @patch("app.nlp.fourm.service.roic_persistence_score")
    @patch("app.nlp.fourm.service.gross_margin_series")
    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_moat_includes_roic_persistence_score(
        self, mock_roic, mock_margin, mock_gm, mock_persist
    ):
        """Test that moat includes ROIC persistence score (C2)."""
        # Arrange
        mock_roic.return_value = [{"fy": 2021, "roic": 0.20}]
        mock_margin.return_value = 0.7
        mock_gm.return_value = []
        mock_persist.return_value = 5

        # Act
        result = compute_moat("test_cik")

        # Assert
        assert "roic_persistence_score" in result
        assert result["roic_persistence_score"] == 5

    @patch("app.nlp.fourm.service.roic_persistence_score")
    @patch("app.nlp.fourm.service.gross_margin_series")
    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_moat_includes_pricing_power(
        self, mock_roic, mock_margin, mock_gm, mock_persist
    ):
        """Test that moat includes pricing power score (C4)."""
        # Arrange
        mock_roic.return_value = [{"fy": 2021, "roic": 0.20}]
        mock_margin.return_value = 0.7
        mock_gm.return_value = [
            {"fy": 2021, "gross_margin": 0.45},
            {"fy": 2022, "gross_margin": 0.46},
            {"fy": 2023, "gross_margin": 0.47},
        ]
        mock_persist.return_value = 4

        # Act
        result = compute_moat("test_cik")

        # Assert
        assert "pricing_power_score" in result
        assert result["pricing_power_score"] is not None
        assert 0.0 <= result["pricing_power_score"] <= 1.0

    @patch("app.nlp.fourm.service.roic_persistence_score")
    @patch("app.nlp.fourm.service.gross_margin_series")
    @patch("app.nlp.fourm.service.margin_stability")
    @patch("app.nlp.fourm.service.roic_series")
    def test_moat_handles_missing_gross_margin_data(
        self, mock_roic, mock_margin, mock_gm, mock_persist
    ):
        """Test moat calculation when gross margin data is missing."""
        # Arrange
        mock_roic.return_value = [{"fy": 2021, "roic": 0.20}]
        mock_margin.return_value = 0.7
        mock_gm.return_value = []  # No gross margin data
        mock_persist.return_value = 3

        # Act
        result = compute_moat("test_cik")

        # Assert
        assert result["latest_gross_margin"] is None
        assert result["gross_margin_trend"] is None
        assert result["pricing_power_score"] is None
        # Score should still be calculated from other metrics
        assert result["score"] is not None


# =============================================================================
# C3: Balance Sheet Resilience Tests
# =============================================================================

class TestComputeBalanceSheetResilience:
    """Test the balance sheet resilience calculation (C3)."""

    @patch("app.nlp.fourm.service.latest_debt_to_equity")
    @patch("app.nlp.fourm.service.net_debt_series")
    @patch("app.nlp.fourm.service.coverage_series")
    def test_balance_sheet_excellent(
        self, mock_coverage, mock_net_debt, mock_de
    ):
        """Test balance sheet with excellent metrics."""
        # Arrange
        mock_coverage.return_value = [
            {"fy": 2021, "coverage": 15.0},
            {"fy": 2022, "coverage": 18.0},
            {"fy": 2023, "coverage": 20.0},
        ]
        mock_de.return_value = 0.2  # Low debt/equity
        mock_net_debt.return_value = [
            {"fy": 2021, "net_debt": 10e9},
            {"fy": 2022, "net_debt": 8e9},
            {"fy": 2023, "net_debt": 5e9},  # Decreasing
        ]

        # Act
        result = compute_balance_sheet_resilience("test_cik")

        # Assert
        assert result["score"] is not None
        assert result["score"] >= 4.0  # Should be high score
        assert result["coverage_score"] == 5.0  # Coverage >10x
        assert result["debt_equity_score"] == 5.0  # D/E < 0.3

    @patch("app.nlp.fourm.service.latest_debt_to_equity")
    @patch("app.nlp.fourm.service.net_debt_series")
    @patch("app.nlp.fourm.service.coverage_series")
    def test_balance_sheet_poor(
        self, mock_coverage, mock_net_debt, mock_de
    ):
        """Test balance sheet with poor metrics."""
        # Arrange
        mock_coverage.return_value = [
            {"fy": 2021, "coverage": 1.5},
            {"fy": 2022, "coverage": 1.2},
            {"fy": 2023, "coverage": 1.0},
        ]
        mock_de.return_value = 2.0  # High debt/equity
        mock_net_debt.return_value = [
            {"fy": 2021, "net_debt": 10e9},
            {"fy": 2022, "net_debt": 15e9},
            {"fy": 2023, "net_debt": 20e9},  # Increasing
        ]

        # Act
        result = compute_balance_sheet_resilience("test_cik")

        # Assert
        assert result["score"] is not None
        assert result["score"] < 2.0  # Should be low score
        assert result["coverage_score"] < 1.0  # Coverage <2x
        assert result["debt_equity_score"] < 1.0  # D/E > 1.5

    @patch("app.nlp.fourm.service.latest_debt_to_equity")
    @patch("app.nlp.fourm.service.net_debt_series")
    @patch("app.nlp.fourm.service.coverage_series")
    def test_balance_sheet_moderate(
        self, mock_coverage, mock_net_debt, mock_de
    ):
        """Test balance sheet with moderate metrics."""
        # Arrange
        mock_coverage.return_value = [
            {"fy": 2021, "coverage": 6.0},
            {"fy": 2022, "coverage": 7.0},
            {"fy": 2023, "coverage": 7.5},
        ]
        mock_de.return_value = 0.5  # Moderate debt/equity
        mock_net_debt.return_value = [
            {"fy": 2021, "net_debt": 10e9},
            {"fy": 2022, "net_debt": 10e9},
            {"fy": 2023, "net_debt": 10e9},  # Flat
        ]

        # Act
        result = compute_balance_sheet_resilience("test_cik")

        # Assert
        assert result["score"] is not None
        assert 2.5 <= result["score"] <= 4.5  # Should be moderate score

    @patch("app.nlp.fourm.service.latest_debt_to_equity")
    @patch("app.nlp.fourm.service.net_debt_series")
    @patch("app.nlp.fourm.service.coverage_series")
    def test_balance_sheet_missing_data(
        self, mock_coverage, mock_net_debt, mock_de
    ):
        """Test balance sheet with missing data."""
        # Arrange
        mock_coverage.return_value = []
        mock_de.return_value = None
        mock_net_debt.return_value = []

        # Act
        result = compute_balance_sheet_resilience("test_cik")

        # Assert
        assert result["latest_coverage"] is None
        assert result["debt_to_equity"] is None
        assert result["latest_net_debt"] is None
        assert result["score"] is None

    @patch("app.nlp.fourm.service.latest_debt_to_equity")
    @patch("app.nlp.fourm.service.net_debt_series")
    @patch("app.nlp.fourm.service.coverage_series")
    def test_balance_sheet_partial_data(
        self, mock_coverage, mock_net_debt, mock_de
    ):
        """Test balance sheet with partial data available."""
        # Arrange
        mock_coverage.return_value = [{"fy": 2023, "coverage": 8.0}]
        mock_de.return_value = 0.4
        mock_net_debt.return_value = []  # No net debt data

        # Act
        result = compute_balance_sheet_resilience("test_cik")

        # Assert
        assert result["latest_coverage"] == 8.0
        assert result["debt_to_equity"] == 0.4
        assert result["score"] is not None  # Should still calculate with available data


# =============================================================================
# Enhanced MOS Recommendation Tests
# =============================================================================

class TestMOSRecommendationPhaseC:
    """Test Phase C enhancements to MOS recommendation."""

    @patch("app.nlp.fourm.service.compute_balance_sheet_resilience")
    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_includes_balance_sheet_score(
        self, mock_moat, mock_mgmt, mock_growth, mock_bs
    ):
        """Test that MOS recommendation includes balance sheet score."""
        # Arrange
        mock_moat.return_value = {"score": 0.7}
        mock_mgmt.return_value = {"score": 0.6}
        mock_growth.return_value = {"eps_cagr_5y": 0.12, "rev_cagr_5y": 0.10}
        mock_bs.return_value = {"score": 4.0}

        # Act
        result = compute_margin_of_safety_recommendation("test_cik")

        # Assert
        assert "balance_sheet_score" in result["drivers"]
        assert result["drivers"]["balance_sheet_score"] == 4.0

    @patch("app.nlp.fourm.service.compute_balance_sheet_resilience")
    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_adjusts_for_weak_balance_sheet(
        self, mock_moat, mock_mgmt, mock_growth, mock_bs
    ):
        """Test that weak balance sheet increases recommended MOS."""
        # Arrange - same moat/mgmt/growth, different balance sheet
        mock_moat.return_value = {"score": 0.7}
        mock_mgmt.return_value = {"score": 0.6}
        mock_growth.return_value = {"eps_cagr_5y": 0.12}
        
        # Strong balance sheet
        mock_bs.return_value = {"score": 5.0}
        result_strong = compute_margin_of_safety_recommendation("test_cik")
        
        # Weak balance sheet
        mock_bs.return_value = {"score": 1.0}
        result_weak = compute_margin_of_safety_recommendation("test_cik")

        # Assert - weak balance sheet should require higher MOS
        assert result_weak["recommended_mos"] > result_strong["recommended_mos"]

    @patch("app.nlp.fourm.service.compute_balance_sheet_resilience")
    @patch("app.nlp.fourm.service.compute_growth_metrics")
    @patch("app.nlp.fourm.service.compute_management")
    @patch("app.nlp.fourm.service.compute_moat")
    def test_mos_handles_missing_balance_sheet(
        self, mock_moat, mock_mgmt, mock_growth, mock_bs
    ):
        """Test MOS calculation when balance sheet data is missing."""
        # Arrange
        mock_moat.return_value = {"score": 0.7}
        mock_mgmt.return_value = {"score": 0.6}
        mock_growth.return_value = {"eps_cagr_5y": 0.12}
        mock_bs.return_value = {"score": None}

        # Act
        result = compute_margin_of_safety_recommendation("test_cik")

        # Assert
        assert result["recommended_mos"] is not None
        assert 0.3 <= result["recommended_mos"] <= 0.7
        assert result["drivers"]["balance_sheet_score"] is None
