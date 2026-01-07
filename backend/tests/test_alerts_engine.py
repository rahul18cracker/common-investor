"""
Integration tests for the alerts engine module
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSnapshotPriceForTicker:
    """Tests for snapshot_price_for_ticker function"""
    
    def test_snapshot_price_success(self):
        """Test successful price snapshot"""
        from app.alerts.engine import snapshot_price_for_ticker
        
        with patch('app.alerts.engine.price_yfinance') as mock_price, \
             patch('app.alerts.engine.execute') as mock_execute:
            
            mock_price.return_value = 150.50
            mock_execute.return_value.first.return_value = [1]  # Company ID
            
            result = snapshot_price_for_ticker("AAPL")
            
            assert result == 150.50
            mock_price.assert_called_once_with("AAPL")
            assert mock_execute.call_count == 2  # SELECT + INSERT
    
    def test_snapshot_price_no_price(self):
        """Test when price_yfinance returns None"""
        from app.alerts.engine import snapshot_price_for_ticker
        
        with patch('app.alerts.engine.price_yfinance') as mock_price:
            mock_price.return_value = None
            
            result = snapshot_price_for_ticker("INVALID")
            
            assert result is None
    
    def test_snapshot_price_company_not_found(self):
        """Test when company is not found in database"""
        from app.alerts.engine import snapshot_price_for_ticker
        
        with patch('app.alerts.engine.price_yfinance') as mock_price, \
             patch('app.alerts.engine.execute') as mock_execute:
            
            mock_price.return_value = 150.50
            mock_execute.return_value.first.return_value = None  # No company
            
            result = snapshot_price_for_ticker("UNKNOWN")
            
            assert result is None


class TestEvaluateAlerts:
    """Tests for evaluate_alerts function"""
    
    def test_evaluate_alerts_no_rules(self):
        """Test when no alert rules exist"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = []
            
            result = evaluate_alerts()
            
            assert result == {"triggered": 0}
    
    def test_evaluate_alerts_price_below_threshold_triggered(self):
        """Test price_below_threshold alert is triggered"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price:
            
            # Mock alert rules
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_threshold", 160.0, True)
            ]
            mock_price.return_value = 150.0  # Below threshold
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 1
    
    def test_evaluate_alerts_price_below_threshold_not_triggered(self):
        """Test price_below_threshold alert is not triggered when price is above"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price:
            
            # Mock alert rules
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_threshold", 140.0, True)
            ]
            mock_price.return_value = 150.0  # Above threshold
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 0
    
    def test_evaluate_alerts_price_none(self):
        """Test when price_yfinance returns None"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_threshold", 160.0, True)
            ]
            mock_price.return_value = None
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 0
    
    def test_evaluate_alerts_price_below_mos_triggered(self):
        """Test price_below_mos alert is triggered"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price, \
             patch('app.alerts.engine.run_default_scenario') as mock_valuation:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_mos", None, True)
            ]
            mock_price.return_value = 100.0
            mock_valuation.return_value = {
                "results": {"mos_price": 150.0}
            }
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 1
    
    def test_evaluate_alerts_price_below_mos_not_triggered(self):
        """Test price_below_mos alert is not triggered when price is above MOS"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price, \
             patch('app.alerts.engine.run_default_scenario') as mock_valuation:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_mos", None, True)
            ]
            mock_price.return_value = 200.0  # Above MOS price
            mock_valuation.return_value = {
                "results": {"mos_price": 150.0}
            }
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 0
    
    def test_evaluate_alerts_price_below_mos_valuation_error(self):
        """Test price_below_mos alert handles valuation errors gracefully"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price, \
             patch('app.alerts.engine.run_default_scenario') as mock_valuation:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_mos", None, True)
            ]
            mock_price.return_value = 100.0
            mock_valuation.side_effect = Exception("Valuation failed")
            
            result = evaluate_alerts()
            
            assert result["triggered"] == 0
    
    def test_evaluate_alerts_multiple_rules(self):
        """Test evaluation of multiple alert rules"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_threshold", 160.0, True),
                (2, "MSFT", "price_below_threshold", 300.0, True),
                (3, "GOOG", "price_below_threshold", 100.0, True),
            ]
            
            def price_side_effect(ticker):
                prices = {"AAPL": 150.0, "MSFT": 350.0, "GOOG": 90.0}
                return prices.get(ticker)
            
            mock_price.side_effect = price_side_effect
            
            result = evaluate_alerts()
            
            # AAPL (150 < 160) and GOOG (90 < 100) should trigger
            assert result["triggered"] == 2
    
    def test_evaluate_alerts_threshold_none(self):
        """Test price_below_threshold with None threshold"""
        from app.alerts.engine import evaluate_alerts
        
        with patch('app.alerts.engine.execute') as mock_execute, \
             patch('app.alerts.engine.price_yfinance') as mock_price:
            
            mock_execute.return_value.fetchall.return_value = [
                (1, "AAPL", "price_below_threshold", None, True)
            ]
            mock_price.return_value = 150.0
            
            result = evaluate_alerts()
            
            # Should not trigger because threshold is None
            assert result["triggered"] == 0
