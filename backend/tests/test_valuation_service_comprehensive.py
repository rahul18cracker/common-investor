"""
Comprehensive unit tests for valuation/service module.

Tests the orchestration layer that combines metrics, growth data, and valuation formulas.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.valuation.service import resolve_cik_by_ticker, run_default_scenario


pytestmark = pytest.mark.unit


class TestResolveCikByTicker:
    """Test CIK resolution from ticker."""

    @patch("app.valuation.service.execute")
    def test_resolve_cik_success(self, mock_execute):
        """Test successful CIK resolution."""
        # Arrange
        mock_execute.return_value.first.return_value = ("0000789019",)
        
        # Act
        result = resolve_cik_by_ticker("MSFT")
        
        # Assert
        assert result == "0000789019"
        mock_execute.assert_called_once()

    @patch("app.valuation.service.execute")
    def test_resolve_cik_case_insensitive(self, mock_execute):
        """Test that ticker lookup is case-insensitive."""
        # Arrange
        mock_execute.return_value.first.return_value = ("0000789019",)
        
        # Act
        resolve_cik_by_ticker("msft")
        
        # Assert
        call_args = mock_execute.call_args[0][0]
        assert "upper(ticker)=upper(:t)" in call_args

    @patch("app.valuation.service.execute")
    def test_resolve_cik_not_found(self, mock_execute):
        """Test CIK resolution when ticker not found."""
        # Arrange
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = resolve_cik_by_ticker("INVALID")
        
        # Assert
        assert result is None


class TestRunDefaultScenario:
    """Test complete valuation scenario execution."""

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_success(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test successful full valuation scenario."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15, "rev_cagr_5y": 0.12}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = (350.00,)  # Current price
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["inputs"]["eps0"] == 10.00
        assert result["inputs"]["g"] == 0.15
        assert result["results"]["sticker"] > 0
        assert result["results"]["mos_price"] > 0
        assert result["results"]["ten_cap_price"] == pytest.approx(120.00, rel=1e-6)
        assert result["results"]["current_price"] == 350.00

    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_unknown_ticker(self, mock_cik):
        """Test error when ticker is unknown."""
        # Arrange
        mock_cik.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown ticker"):
            run_default_scenario("INVALID")

    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_missing_eps(self, mock_cik, mock_eps):
        """Test error when EPS data is missing."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Missing EPS"):
            run_default_scenario("MSFT")

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_uses_revenue_fallback(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test fallback to revenue growth when EPS growth unavailable."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 8.00
        mock_growth.return_value = {"rev_cagr_5y": 0.18}  # No EPS growth
        mock_oe.return_value = 9.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["inputs"]["g"] == 0.18  # Used revenue growth

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_uses_10y_fallback(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test fallback to 10-year growth when 5-year unavailable."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 8.00
        mock_growth.return_value = {"eps_cagr_10y": 0.14, "rev_cagr_10y": 0.13}
        mock_oe.return_value = 9.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["inputs"]["g"] == 0.14  # Used 10y EPS growth

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_default_growth(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test default 10% growth when no growth data available."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 8.00
        mock_growth.return_value = {}  # No growth data
        mock_oe.return_value = 9.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["inputs"]["g"] == 0.10  # Default

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_custom_mos(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test custom margin of safety percentage."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT", mos_pct=0.7)
        
        # Assert
        assert result["inputs"]["mos_pct"] == 0.7
        assert result["results"]["mos_price"] == pytest.approx(
            result["results"]["sticker"] * 0.3, rel=1e-6
        )

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_growth_override(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test manual growth rate override."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT", g_override=0.20)
        
        # Assert
        assert result["inputs"]["g"] == 0.20  # Override used

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_custom_pe_cap(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test custom PE cap."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT", pe_cap=25)
        
        # Assert
        assert result["inputs"]["pe_cap"] == 25

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_custom_discount(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test custom discount rate."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT", discount=0.20)
        
        # Assert
        assert result["inputs"]["discount"] == 0.20

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_no_price_data(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test when no current price is available."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 12.00
        mock_execute.return_value.first.return_value = None  # No price
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["results"]["current_price"] is None
        # Payback should use MOS price as fallback
        assert result["results"]["payback_years"] is not None

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_oe_falls_back_to_eps(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test that owner earnings falls back to EPS."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = None  # No OE data
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert
        assert result["results"]["owner_earnings_ps"] == 10.00  # Fell back to EPS
        assert result["results"]["ten_cap_price"] == pytest.approx(100.00, rel=1e-6)

    @patch("app.valuation.service.execute")
    @patch("app.valuation.service.latest_owner_earnings_ps")
    @patch("app.valuation.service.compute_growth_metrics")
    @patch("app.valuation.service.latest_eps")
    @patch("app.valuation.service.resolve_cik_by_ticker")
    def test_run_default_scenario_no_oe_no_payback(self, mock_cik, mock_eps, mock_growth, mock_oe, mock_execute):
        """Test that OE=0 falls back to EPS for payback calculation."""
        # Arrange
        mock_cik.return_value = "0000789019"
        mock_eps.return_value = 10.00
        mock_growth.return_value = {"eps_cagr_5y": 0.15}
        mock_oe.return_value = 0  # Falls back to EPS
        mock_execute.return_value.first.return_value = None
        
        # Act
        result = run_default_scenario("MSFT")
        
        # Assert: OE falls back to EPS, so payback is calculated
        assert result["results"]["owner_earnings_ps"] == 10.00
        assert result["results"]["payback_years"] is not None
