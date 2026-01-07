"""
Comprehensive unit tests for app/cli/seed.py

Tests cover:
- check_db_has_companies: database count queries
- ingest_ticker: single ticker ingestion with success/failure
- seed_tickers: batch seeding with rate limiting
- main: CLI argument parsing and execution flow
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys
from io import StringIO

from app.cli.seed import (
    DEFAULT_TICKERS,
    check_db_has_companies,
    ingest_ticker,
    seed_tickers,
    main,
)


class TestDefaultTickers:
    """Tests for default ticker configuration."""

    def test_default_tickers_not_empty(self):
        """Test that DEFAULT_TICKERS contains tickers."""
        assert len(DEFAULT_TICKERS) > 0

    def test_default_tickers_are_strings(self):
        """Test that all default tickers are strings."""
        for ticker in DEFAULT_TICKERS:
            assert isinstance(ticker, str)

    def test_default_tickers_are_uppercase(self):
        """Test that all default tickers are uppercase."""
        for ticker in DEFAULT_TICKERS:
            assert ticker == ticker.upper()

    def test_default_tickers_contains_expected(self):
        """Test that expected tickers are in the list."""
        expected = ["MSFT", "AAPL", "GOOGL"]
        for ticker in expected:
            assert ticker in DEFAULT_TICKERS


class TestCheckDbHasCompanies:
    """Tests for check_db_has_companies function."""

    def test_check_db_returns_count(self):
        """Test returns company count from database."""
        mock_result = MagicMock()
        mock_result.first.return_value = [5]
        
        with patch("app.db.session.execute", return_value=mock_result) as mock_execute:
            result = check_db_has_companies()
            
            assert result == 5
            mock_execute.assert_called_once_with("SELECT COUNT(*) FROM company")

    def test_check_db_returns_zero_when_empty(self):
        """Test returns 0 when database is empty."""
        mock_result = MagicMock()
        mock_result.first.return_value = [0]
        
        with patch("app.db.session.execute", return_value=mock_result):
            result = check_db_has_companies()
            
            assert result == 0

    def test_check_db_returns_zero_on_none_row(self):
        """Test returns 0 when query returns None."""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        
        with patch("app.db.session.execute", return_value=mock_result):
            result = check_db_has_companies()
            
            assert result == 0

    def test_check_db_returns_zero_on_exception(self):
        """Test returns 0 when database query fails."""
        with patch("app.db.session.execute", side_effect=Exception("DB connection failed")):
            result = check_db_has_companies()
            
            assert result == 0

    def test_check_db_handles_large_count(self):
        """Test handles large company counts."""
        mock_result = MagicMock()
        mock_result.first.return_value = [1000000]
        
        with patch("app.db.session.execute", return_value=mock_result):
            result = check_db_has_companies()
            
            assert result == 1000000


class TestIngestTicker:
    """Tests for ingest_ticker function."""

    def test_ingest_ticker_success(self):
        """Test successful ticker ingestion."""
        mock_ingest_result = {"years": [2020, 2021, 2022], "company_id": 1}
        
        with patch("app.ingest.sec.ingest_companyfacts_richer_by_ticker", return_value=mock_ingest_result):
            result = ingest_ticker("AAPL")
            
            assert result["ticker"] == "AAPL"
            assert result["status"] == "success"
            assert result["result"] == mock_ingest_result

    def test_ingest_ticker_error(self):
        """Test ticker ingestion failure."""
        with patch("app.ingest.sec.ingest_companyfacts_richer_by_ticker", 
                   side_effect=Exception("API error")):
            result = ingest_ticker("INVALID")
            
            assert result["ticker"] == "INVALID"
            assert result["status"] == "error"
            assert "API error" in result["error"]

    def test_ingest_ticker_preserves_ticker_case(self):
        """Test ticker case is preserved in result."""
        mock_ingest_result = {"years": []}
        
        with patch("app.ingest.sec.ingest_companyfacts_richer_by_ticker", return_value=mock_ingest_result):
            result = ingest_ticker("msft")
            
            assert result["ticker"] == "msft"

    def test_ingest_ticker_with_special_characters(self):
        """Test ticker with special characters like BRK-B."""
        mock_ingest_result = {"years": [2020]}
        
        with patch("app.ingest.sec.ingest_companyfacts_richer_by_ticker", return_value=mock_ingest_result):
            result = ingest_ticker("BRK-B")
            
            assert result["ticker"] == "BRK-B"
            assert result["status"] == "success"


class TestSeedTickers:
    """Tests for seed_tickers function."""

    def test_seed_tickers_all_success(self):
        """Test seeding multiple tickers successfully."""
        mock_ingest_result = {"years": [2020, 2021]}
        
        with patch("app.cli.seed.ingest_ticker") as mock_ingest:
            mock_ingest.return_value = {"ticker": "TEST", "status": "success", "result": mock_ingest_result}
            with patch("time.sleep"):  # Skip delays
                results = seed_tickers(["AAPL", "MSFT"], delay_seconds=0)
        
        assert len(results["success"]) == 2
        assert len(results["failed"]) == 0

    def test_seed_tickers_with_failures(self):
        """Test seeding with some failures."""
        def mock_ingest_side_effect(ticker):
            if ticker == "INVALID":
                return {"ticker": ticker, "status": "error", "error": "Not found"}
            return {"ticker": ticker, "status": "success", "result": {"years": []}}
        
        with patch("app.cli.seed.ingest_ticker", side_effect=mock_ingest_side_effect):
            with patch("time.sleep"):
                results = seed_tickers(["AAPL", "INVALID", "MSFT"], delay_seconds=0)
        
        assert len(results["success"]) == 2
        assert len(results["failed"]) == 1
        assert results["failed"][0]["ticker"] == "INVALID"

    def test_seed_tickers_all_failures(self):
        """Test seeding when all tickers fail."""
        with patch("app.cli.seed.ingest_ticker") as mock_ingest:
            mock_ingest.return_value = {"ticker": "TEST", "status": "error", "error": "Failed"}
            with patch("time.sleep"):
                results = seed_tickers(["BAD1", "BAD2"], delay_seconds=0)
        
        assert len(results["success"]) == 0
        assert len(results["failed"]) == 2

    def test_seed_tickers_empty_list(self):
        """Test seeding with empty ticker list."""
        with patch("time.sleep"):
            results = seed_tickers([], delay_seconds=0)
        
        assert len(results["success"]) == 0
        assert len(results["failed"]) == 0

    def test_seed_tickers_respects_delay(self):
        """Test that delay is applied between tickers."""
        mock_ingest_result = {"years": []}
        
        with patch("app.cli.seed.ingest_ticker") as mock_ingest:
            mock_ingest.return_value = {"ticker": "TEST", "status": "success", "result": mock_ingest_result}
            with patch("time.sleep") as mock_sleep:
                seed_tickers(["A", "B", "C"], delay_seconds=1.0)
        
        # Sleep should be called n-1 times (between tickers, not after last)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(1.0)

    def test_seed_tickers_no_delay_for_single_ticker(self):
        """Test no delay when only one ticker."""
        mock_ingest_result = {"years": []}
        
        with patch("app.cli.seed.ingest_ticker") as mock_ingest:
            mock_ingest.return_value = {"ticker": "TEST", "status": "success", "result": mock_ingest_result}
            with patch("time.sleep") as mock_sleep:
                seed_tickers(["AAPL"], delay_seconds=1.0)
        
        mock_sleep.assert_not_called()

    def test_seed_tickers_output_format(self, capsys):
        """Test output formatting during seeding."""
        mock_ingest_result = {"years": [2020, 2021, 2022]}
        
        with patch("app.cli.seed.ingest_ticker") as mock_ingest:
            mock_ingest.return_value = {"ticker": "AAPL", "status": "success", "result": mock_ingest_result}
            with patch("time.sleep"):
                seed_tickers(["AAPL"], delay_seconds=0)
        
        captured = capsys.readouterr()
        assert "Seeding" in captured.out
        assert "AAPL" in captured.out
        assert "OK" in captured.out


class TestMain:
    """Tests for main CLI function."""

    def test_main_check_mode_empty_db(self):
        """Test --check mode with empty database."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("sys.argv", ["seed.py", "--check"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_main_check_mode_has_data(self):
        """Test --check mode with existing data."""
        with patch("app.cli.seed.check_db_has_companies", return_value=5):
            with patch("sys.argv", ["seed.py", "--check"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_main_skips_seeding_when_data_exists(self):
        """Test skips seeding when data exists without --force."""
        with patch("app.cli.seed.check_db_has_companies", return_value=5):
            with patch("app.cli.seed.seed_tickers") as mock_seed:
                with patch("sys.argv", ["seed.py"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                mock_seed.assert_not_called()

    def test_main_force_reseeds(self):
        """Test --force flag triggers seeding even with existing data."""
        with patch("app.cli.seed.check_db_has_companies", return_value=5):
            with patch("app.cli.seed.seed_tickers", return_value={"success": ["AAPL"], "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py", "--force"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                mock_seed.assert_called_once()

    def test_main_custom_tickers(self):
        """Test --tickers argument with custom list."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": ["AAPL", "MSFT"], "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py", "--tickers", "AAPL,MSFT"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                # Check that custom tickers were passed
                call_args = mock_seed.call_args
                assert "AAPL" in call_args[0][0]
                assert "MSFT" in call_args[0][0]

    def test_main_custom_delay(self):
        """Test --delay argument."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": [], "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py", "--tickers", "AAPL", "--delay", "2.0"]):
                    with pytest.raises(SystemExit):
                        main()
                # Check delay was passed
                call_args = mock_seed.call_args
                assert call_args[1]["delay_seconds"] == 2.0

    def test_main_exit_code_on_failures(self):
        """Test exit code 1 when some tickers fail."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": ["AAPL"], "failed": [{"ticker": "BAD"}]}):
                with patch("sys.argv", ["seed.py", "--tickers", "AAPL,BAD"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

    def test_main_exit_code_all_success(self):
        """Test exit code 0 when all tickers succeed."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": ["AAPL", "MSFT"], "failed": []}):
                with patch("sys.argv", ["seed.py", "--tickers", "AAPL,MSFT"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0

    def test_main_ticker_normalization(self):
        """Test tickers are normalized to uppercase."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": [], "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py", "--tickers", "aapl,msft"]):
                    with pytest.raises(SystemExit):
                        main()
                call_args = mock_seed.call_args
                assert "AAPL" in call_args[0][0]
                assert "MSFT" in call_args[0][0]

    def test_main_ticker_whitespace_handling(self):
        """Test tickers with whitespace are trimmed."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": [], "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py", "--tickers", " AAPL , MSFT "]):
                    with pytest.raises(SystemExit):
                        main()
                call_args = mock_seed.call_args
                assert "AAPL" in call_args[0][0]
                assert "MSFT" in call_args[0][0]

    def test_main_uses_default_tickers_when_none_specified(self):
        """Test uses DEFAULT_TICKERS when --tickers not provided."""
        with patch("app.cli.seed.check_db_has_companies", return_value=0):
            with patch("app.cli.seed.seed_tickers", return_value={"success": DEFAULT_TICKERS, "failed": []}) as mock_seed:
                with patch("sys.argv", ["seed.py"]):
                    with pytest.raises(SystemExit):
                        main()
                call_args = mock_seed.call_args
                assert call_args[0][0] == DEFAULT_TICKERS
