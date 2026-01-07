"""
Comprehensive unit tests for app/pricefeed/provider.py

Tests cover:
- Successful price retrieval from yfinance
- Handling of empty/None data
- Exception handling for various failure modes
- Edge cases with different ticker formats
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from app.pricefeed.provider import price_yfinance


class TestPriceYfinance:
    """Tests for the price_yfinance function."""

    def test_price_yfinance_success(self):
        """Test successful price retrieval returns float."""
        mock_history = pd.DataFrame({
            "Close": [150.25, 151.50, 152.75]
        })
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}) as mock_modules:
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("AAPL")
            
            assert result == 152.75
            mock_yf.Ticker.assert_called_once_with("AAPL")
            mock_ticker.history.assert_called_once_with(period="1d", interval="1d")

    def test_price_yfinance_returns_float_type(self):
        """Test that result is always a float when successful."""
        mock_history = pd.DataFrame({
            "Close": [100]
        })
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("MSFT")
            
            assert isinstance(result, float)

    def test_price_yfinance_none_data(self):
        """Test returns None when history returns None."""
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = None
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("INVALID")
            
            assert result is None

    def test_price_yfinance_empty_dataframe(self):
        """Test returns None when history returns empty DataFrame."""
        empty_df = pd.DataFrame()
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = empty_df
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("UNKNOWN")
            
            assert result is None

    def test_price_yfinance_empty_close_column(self):
        """Test returns None when Close column is empty."""
        empty_close_df = pd.DataFrame({"Close": []})
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = empty_close_df
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("TEST")
            
            assert result is None

    def test_price_yfinance_exception_handling(self):
        """Test returns None when yfinance raises an exception."""
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_yf.Ticker.side_effect = Exception("Network error")
            
            result = price_yfinance("AAPL")
            
            assert result is None

    def test_price_yfinance_ticker_history_exception(self):
        """Test returns None when history() raises an exception."""
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.side_effect = Exception("API rate limit")
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("GOOGL")
            
            assert result is None

    def test_price_yfinance_index_error(self):
        """Test returns None when iloc raises IndexError."""
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.__getitem__ = MagicMock(side_effect=KeyError("Close"))
            mock_ticker.history.return_value = mock_df
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("TEST")
            
            assert result is None

    def test_price_yfinance_various_tickers(self):
        """Test with various ticker formats."""
        mock_history = pd.DataFrame({"Close": [100.0]})
        
        tickers = ["AAPL", "BRK-B", "BRK.B", "GOOGL", "META"]
        
        for ticker in tickers:
            with patch.dict("sys.modules", {"yfinance": MagicMock()}):
                import sys
                mock_yf = sys.modules["yfinance"]
                mock_ticker_obj = MagicMock()
                mock_ticker_obj.history.return_value = mock_history
                mock_yf.Ticker.return_value = mock_ticker_obj
                
                result = price_yfinance(ticker)
                assert result == 100.0

    def test_price_yfinance_negative_price(self):
        """Test handling of negative prices (edge case)."""
        mock_history = pd.DataFrame({"Close": [-5.0]})
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("TEST")
            
            assert result == -5.0

    def test_price_yfinance_zero_price(self):
        """Test handling of zero price."""
        mock_history = pd.DataFrame({"Close": [0.0]})
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("PENNY")
            
            assert result == 0.0

    def test_price_yfinance_large_price(self):
        """Test handling of very large prices."""
        mock_history = pd.DataFrame({"Close": [500000.0]})
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("BRK-A")
            
            assert result == 500000.0

    def test_price_yfinance_decimal_precision(self):
        """Test decimal precision is preserved."""
        mock_history = pd.DataFrame({"Close": [123.456789]})
        
        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = mock_history
            mock_yf.Ticker.return_value = mock_ticker
            
            result = price_yfinance("TEST")
            
            assert abs(result - 123.456789) < 0.0001
