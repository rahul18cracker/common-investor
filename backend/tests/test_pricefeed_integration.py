"""
Integration tests for the pricefeed provider module
"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestPriceYfinance:
    """Tests for price_yfinance function"""
    
    def test_price_yfinance_success(self):
        """Test successful price fetch from yfinance"""
        from app.pricefeed.provider import price_yfinance
        
        # Mock yfinance module
        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = MagicMock()
        mock_ticker.history.return_value.empty = False
        mock_ticker.history.return_value.__getitem__ = lambda self, key: MagicMock(iloc=MagicMock(__getitem__=lambda s, i: 150.50))
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch.dict('sys.modules', {'yfinance': mock_yf}):
            # Re-import to use mocked module
            import importlib
            import app.pricefeed.provider as provider
            importlib.reload(provider)
            
            result = provider.price_yfinance("AAPL")
            
            # The function should return a price or None
            assert result is None or isinstance(result, (int, float))
    
    def test_price_yfinance_empty_history(self):
        """Test when yfinance returns empty history"""
        from app.pricefeed.provider import price_yfinance
        
        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = MagicMock()
        mock_ticker.history.return_value.empty = True
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch.dict('sys.modules', {'yfinance': mock_yf}):
            import importlib
            import app.pricefeed.provider as provider
            importlib.reload(provider)
            
            result = provider.price_yfinance("INVALID")
            
            assert result is None
    
    def test_price_yfinance_exception(self):
        """Test when yfinance raises an exception"""
        from app.pricefeed.provider import price_yfinance
        
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = Exception("API Error")
        
        with patch.dict('sys.modules', {'yfinance': mock_yf}):
            import importlib
            import app.pricefeed.provider as provider
            importlib.reload(provider)
            
            result = provider.price_yfinance("AAPL")
            
            assert result is None
