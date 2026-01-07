"""
Integration tests for the CLI seed module
"""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO


pytestmark = pytest.mark.integration


class TestCheckDbHasCompanies:
    """Tests for check_db_has_companies function"""
    
    def test_check_db_has_companies_with_data(self):
        """Test checking database with existing companies"""
        from app.cli.seed import check_db_has_companies
        
        with patch('app.db.session.execute') as mock_execute:
            mock_execute.return_value.first.return_value = (5,)
            
            result = check_db_has_companies()
            
            assert result == 5
    
    def test_check_db_has_companies_empty(self):
        """Test checking empty database"""
        from app.cli.seed import check_db_has_companies
        
        with patch('app.db.session.execute') as mock_execute:
            mock_execute.return_value.first.return_value = (0,)
            
            result = check_db_has_companies()
            
            assert result == 0
    
    def test_check_db_has_companies_no_row(self):
        """Test checking database when query returns no row"""
        from app.cli.seed import check_db_has_companies
        
        with patch('app.db.session.execute') as mock_execute:
            mock_execute.return_value.first.return_value = None
            
            result = check_db_has_companies()
            
            assert result == 0
    
    def test_check_db_has_companies_exception(self):
        """Test checking database when exception occurs"""
        from app.cli.seed import check_db_has_companies
        
        with patch('app.db.session.execute') as mock_execute:
            mock_execute.side_effect = Exception("Database error")
            
            result = check_db_has_companies()
            
            assert result == 0


class TestIngestTicker:
    """Tests for ingest_ticker function"""
    
    def test_ingest_ticker_success(self):
        """Test successful ticker ingestion"""
        from app.cli.seed import ingest_ticker
        
        with patch('app.ingest.sec.ingest_companyfacts_richer_by_ticker') as mock_ingest:
            mock_ingest.return_value = {"years": [2020, 2021, 2022, 2023]}
            
            result = ingest_ticker("AAPL")
            
            assert result["ticker"] == "AAPL"
            assert result["status"] == "success"
            assert result["result"]["years"] == [2020, 2021, 2022, 2023]
    
    def test_ingest_ticker_error(self):
        """Test ticker ingestion with error"""
        from app.cli.seed import ingest_ticker
        
        with patch('app.ingest.sec.ingest_companyfacts_richer_by_ticker') as mock_ingest:
            mock_ingest.side_effect = Exception("API Error")
            
            result = ingest_ticker("INVALID")
            
            assert result["ticker"] == "INVALID"
            assert result["status"] == "error"
            assert "API Error" in result["error"]


class TestSeedTickers:
    """Tests for seed_tickers function"""
    
    def test_seed_tickers_all_success(self):
        """Test seeding multiple tickers successfully"""
        from app.cli.seed import seed_tickers
        
        with patch('app.cli.seed.ingest_ticker') as mock_ingest, \
             patch('app.cli.seed.time.sleep'):
            
            mock_ingest.side_effect = [
                {"ticker": "AAPL", "status": "success", "result": {"years": [2020, 2021]}},
                {"ticker": "MSFT", "status": "success", "result": {"years": [2020, 2021]}},
            ]
            
            result = seed_tickers(["AAPL", "MSFT"], delay_seconds=0)
            
            assert len(result["success"]) == 2
            assert len(result["failed"]) == 0
            assert "AAPL" in result["success"]
            assert "MSFT" in result["success"]
    
    def test_seed_tickers_with_failures(self):
        """Test seeding with some failures"""
        from app.cli.seed import seed_tickers
        
        with patch('app.cli.seed.ingest_ticker') as mock_ingest, \
             patch('app.cli.seed.time.sleep'):
            
            mock_ingest.side_effect = [
                {"ticker": "AAPL", "status": "success", "result": {"years": [2020, 2021]}},
                {"ticker": "INVALID", "status": "error", "error": "Not found"},
            ]
            
            result = seed_tickers(["AAPL", "INVALID"], delay_seconds=0)
            
            assert len(result["success"]) == 1
            assert len(result["failed"]) == 1
            assert "AAPL" in result["success"]
            assert result["failed"][0]["ticker"] == "INVALID"
    
    def test_seed_tickers_empty_list(self):
        """Test seeding with empty ticker list"""
        from app.cli.seed import seed_tickers
        
        result = seed_tickers([], delay_seconds=0)
        
        assert len(result["success"]) == 0
        assert len(result["failed"]) == 0


class TestMain:
    """Tests for main function"""
    
    def test_main_check_mode_empty_db(self):
        """Test main in check mode with empty database"""
        from app.cli.seed import main
        import sys
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('sys.argv', ['seed.py', '--check']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 0
            main()
        
        assert exc_info.value.code == 1  # Exit code 1 = needs seeding
    
    def test_main_check_mode_has_data(self):
        """Test main in check mode with existing data"""
        from app.cli.seed import main
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('sys.argv', ['seed.py', '--check']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 5
            main()
        
        assert exc_info.value.code == 0  # Exit code 0 = no seeding needed
    
    def test_main_skip_seeding_when_data_exists(self):
        """Test main skips seeding when data exists and no force flag"""
        from app.cli.seed import main
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('app.cli.seed.seed_tickers') as mock_seed, \
             patch('sys.argv', ['seed.py']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 5
            main()
        
        mock_seed.assert_not_called()
        assert exc_info.value.code == 0
    
    def test_main_force_seeding(self):
        """Test main forces seeding with --force flag"""
        from app.cli.seed import main
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('app.cli.seed.seed_tickers') as mock_seed, \
             patch('sys.argv', ['seed.py', '--force']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 5
            mock_seed.return_value = {"success": ["MSFT"], "failed": []}
            main()
        
        mock_seed.assert_called_once()
        assert exc_info.value.code == 0
    
    def test_main_custom_tickers(self):
        """Test main with custom tickers"""
        from app.cli.seed import main
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('app.cli.seed.seed_tickers') as mock_seed, \
             patch('sys.argv', ['seed.py', '--tickers', 'AAPL,MSFT']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 0
            mock_seed.return_value = {"success": ["AAPL", "MSFT"], "failed": []}
            main()
        
        # Check that seed_tickers was called with the custom tickers
        call_args = mock_seed.call_args
        assert "AAPL" in call_args[0][0]
        assert "MSFT" in call_args[0][0]
    
    def test_main_seeding_with_failures(self):
        """Test main exits with code 1 when seeding has failures"""
        from app.cli.seed import main
        
        with patch('app.cli.seed.check_db_has_companies') as mock_check, \
             patch('app.cli.seed.seed_tickers') as mock_seed, \
             patch('sys.argv', ['seed.py', '--tickers', 'AAPL']), \
             pytest.raises(SystemExit) as exc_info:
            
            mock_check.return_value = 0
            mock_seed.return_value = {
                "success": [],
                "failed": [{"ticker": "AAPL", "error": "Not found"}]
            }
            main()
        
        assert exc_info.value.code == 1


class TestDefaultTickers:
    """Tests for DEFAULT_TICKERS constant"""
    
    def test_default_tickers_not_empty(self):
        """Test that DEFAULT_TICKERS is not empty"""
        from app.cli.seed import DEFAULT_TICKERS
        
        assert len(DEFAULT_TICKERS) > 0
    
    def test_default_tickers_are_strings(self):
        """Test that all DEFAULT_TICKERS are strings"""
        from app.cli.seed import DEFAULT_TICKERS
        
        for ticker in DEFAULT_TICKERS:
            assert isinstance(ticker, str)
            assert len(ticker) > 0
