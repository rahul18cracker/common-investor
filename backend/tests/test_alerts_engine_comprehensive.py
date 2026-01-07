"""
Comprehensive unit tests for alerts/engine module.

This test suite aims for 90%+ coverage of app/alerts/engine.py
Following industry best practices: AAA pattern, mocking external dependencies, edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.alerts.engine import (
    snapshot_price_for_ticker,
    evaluate_alerts,
)


pytestmark = pytest.mark.unit


class TestSnapshotPriceForTicker:
    """Test price snapshot creation functionality."""

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_snapshot_price_success(self, mock_price, mock_execute):
        """Test successful price snapshot creation."""
        # Arrange
        mock_price.return_value = 150.50
        mock_execute.return_value.first.return_value = (123,)  # company_id

        # Act
        result = snapshot_price_for_ticker("AAPL")

        # Assert
        assert result == 150.50
        mock_price.assert_called_once_with("AAPL")
        assert mock_execute.call_count == 2  # SELECT company, INSERT snapshot

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_snapshot_price_no_price_data(self, mock_price, mock_execute):
        """Test when price data is unavailable."""
        # Arrange
        mock_price.return_value = None

        # Act
        result = snapshot_price_for_ticker("INVALID")

        # Assert
        assert result is None
        mock_execute.assert_not_called()

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_snapshot_price_company_not_found(self, mock_price, mock_execute):
        """Test when company ticker is not in database."""
        # Arrange
        mock_price.return_value = 100.00
        mock_execute.return_value.first.return_value = None  # Company not found

        # Act
        result = snapshot_price_for_ticker("UNKNOWN")

        # Assert
        assert result is None
        mock_price.assert_called_once_with("UNKNOWN")
        mock_execute.assert_called_once()  # Only SELECT, no INSERT

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_snapshot_price_case_insensitive(self, mock_price, mock_execute):
        """Test that ticker matching is case-insensitive."""
        # Arrange
        mock_price.return_value = 200.00
        mock_execute.return_value.first.return_value = (456,)

        # Act
        result = snapshot_price_for_ticker("msft")

        # Assert
        assert result == 200.00
        # Verify SQL uses upper() for case-insensitive matching
        call_args = mock_execute.call_args_list[0]
        assert "upper(ticker)=upper(:t)" in call_args[0][0]


class TestEvaluateAlerts:
    """Test alert evaluation engine."""

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_price_below_threshold(self, mock_price, mock_execute):
        """Test triggering alerts when price falls below threshold."""
        # Arrange: One alert rule with threshold $100
        mock_execute.return_value.fetchall.return_value = [
            (1, "AAPL", "price_below_threshold", 100.0, True)
        ]
        mock_price.return_value = 95.00  # Below threshold

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 1
        mock_price.assert_called_once_with("AAPL")
        # Verify INSERT into meaning_note was called
        assert mock_execute.call_count == 2  # SELECT rules, INSERT note

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_price_above_threshold(self, mock_price, mock_execute):
        """Test that alerts don't trigger when price is above threshold."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (1, "AAPL", "price_below_threshold", 100.0, True)
        ]
        mock_price.return_value = 105.00  # Above threshold

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 0
        mock_execute.assert_called_once()  # Only SELECT rules, no INSERT

    @patch("app.alerts.engine.run_default_scenario")
    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_price_below_mos(self, mock_price, mock_execute, mock_valuation):
        """Test triggering alerts when price falls below MOS price."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (2, "MSFT", "price_below_mos", None, True)
        ]
        mock_price.return_value = 250.00
        mock_valuation.return_value = {
            "results": {"mos_price": 300.00}
        }

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 1
        mock_valuation.assert_called_once_with("MSFT")

    @patch("app.alerts.engine.run_default_scenario")
    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_price_above_mos(self, mock_price, mock_execute, mock_valuation):
        """Test that MOS alerts don't trigger when price is above MOS."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (2, "MSFT", "price_below_mos", None, True)
        ]
        mock_price.return_value = 350.00
        mock_valuation.return_value = {
            "results": {"mos_price": 300.00}
        }

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 0

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_no_price_data(self, mock_price, mock_execute):
        """Test that alerts are skipped when price data unavailable."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (1, "INVALID", "price_below_threshold", 100.0, True)
        ]
        mock_price.return_value = None

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 0

    @patch("app.alerts.engine.run_default_scenario")
    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_valuation_error(self, mock_price, mock_execute, mock_valuation):
        """Test that valuation errors are handled gracefully."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (2, "BADTICKER", "price_below_mos", None, True)
        ]
        mock_price.return_value = 100.00
        mock_valuation.side_effect = Exception("Valuation failed")

        # Act
        result = evaluate_alerts()

        # Assert: Error should be caught, no alerts triggered
        assert result["triggered"] == 0

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_multiple_rules(self, mock_price, mock_execute):
        """Test evaluating multiple alert rules."""
        # Arrange: Three rules, two should trigger
        mock_execute.return_value.fetchall.return_value = [
            (1, "AAPL", "price_below_threshold", 150.0, True),
            (2, "MSFT", "price_below_threshold", 300.0, True),
            (3, "GOOGL", "price_below_threshold", 100.0, True),
        ]
        mock_price.side_effect = [140.0, 290.0, 110.0]  # AAPL & MSFT trigger

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 2

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_no_rules(self, mock_price, mock_execute):
        """Test when no alert rules are configured."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = []

        # Act
        result = evaluate_alerts()

        # Assert
        assert result["triggered"] == 0
        mock_price.assert_not_called()

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_threshold_none(self, mock_price, mock_execute):
        """Test that alerts with None threshold are skipped."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (1, "AAPL", "price_below_threshold", None, True)
        ]
        mock_price.return_value = 150.00

        # Act
        result = evaluate_alerts()

        # Assert: Should not trigger since threshold is None
        assert result["triggered"] == 0

    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_creates_meaning_note(self, mock_price, mock_execute):
        """Test that triggered alerts create meaning notes correctly."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (5, "AAPL", "price_below_threshold", 100.0, True)
        ]
        mock_price.return_value = 95.00

        # Act
        evaluate_alerts()

        # Assert: Verify meaning_note INSERT
        insert_call = mock_execute.call_args_list[1]
        assert "INSERT INTO meaning_note" in insert_call[0][0]
        assert "ALERT price_below_threshold" in insert_call[1]["text"]
        assert insert_call[1]["t"] == "AAPL"

    @patch("app.alerts.engine.run_default_scenario")
    @patch("app.alerts.engine.execute")
    @patch("app.alerts.engine.price_yfinance")
    def test_evaluate_alerts_mos_missing_results(self, mock_price, mock_execute, mock_valuation):
        """Test handling when valuation result structure is unexpected."""
        # Arrange
        mock_execute.return_value.fetchall.return_value = [
            (2, "MSFT", "price_below_mos", None, True)
        ]
        mock_price.return_value = 250.00
        mock_valuation.return_value = {}  # Missing 'results' key

        # Act
        result = evaluate_alerts()

        # Assert: Should handle KeyError gracefully
        assert result["triggered"] == 0
