"""
Unit tests for app/ingest/sec.py

Tests SEC EDGAR API integration, data parsing, and database ingestion.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from httpx import HTTPError, Response, Request
from app.ingest.sec import (
    fetch_json,
    ticker_map,
    company_facts,
    upsert_company,
    upsert_filing,
    _pick_first_units,
    ingest_companyfacts_richer_by_ticker
)


# =============================================================================
# Unit Tests: fetch_json
# =============================================================================

@pytest.mark.unit
@pytest.mark.mock_sec
class TestFetchJson:
    """Test the fetch_json HTTP client function."""
    
    def test_fetch_json_success(self, httpx_mock):
        """Test successful JSON fetch from SEC API."""
        expected_data = {"test": "data", "value": 123}
        httpx_mock.add_response(
            url="https://test.example.com/api/data.json",
            json=expected_data
        )
        
        result = fetch_json("https://test.example.com/api/data.json")
        
        assert result == expected_data
    
    def test_fetch_json_404_error(self, httpx_mock):
        """Test 404 error handling."""
        httpx_mock.add_response(
            url="https://test.example.com/notfound.json",
            status_code=404
        )
        
        with pytest.raises(HTTPError) as exc_info:
            fetch_json("https://test.example.com/notfound.json")
        
        assert "404" in str(exc_info.value)
    
    def test_fetch_json_500_error(self, httpx_mock):
        """Test 500 server error handling."""
        httpx_mock.add_response(
            url="https://test.example.com/error.json",
            status_code=500
        )
        
        with pytest.raises(HTTPError):
            fetch_json("https://test.example.com/error.json")
    
    def test_fetch_json_timeout(self, httpx_mock):
        """Test timeout handling."""
        from httpx import TimeoutException
        
        httpx_mock.add_exception(TimeoutException("Request timed out"))
        
        with pytest.raises(TimeoutException):
            fetch_json("https://test.example.com/slow.json")
    
    def test_fetch_json_includes_user_agent(self, httpx_mock):
        """Test that User-Agent header is included."""
        httpx_mock.add_response(json={"success": True})
        
        fetch_json("https://test.example.com/api/data.json")
        
        request = httpx_mock.get_request()
        assert "User-Agent" in request.headers
        assert "CommonInvestor" in request.headers["User-Agent"] or "TestCommonInvestor" in request.headers["User-Agent"]


# =============================================================================
# Unit Tests: ticker_map
# =============================================================================

@pytest.mark.unit
@pytest.mark.mock_sec
class TestTickerMap:
    """Test ticker to CIK mapping functionality."""
    
    def test_ticker_map_success(self, httpx_mock, mock_sec_company_tickers):
        """Test successful ticker map retrieval."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            json=mock_sec_company_tickers
        )
        
        result = ticker_map()
        
        assert isinstance(result, dict)
        assert "MSFT" in result
        assert result["MSFT"] == 789019
        assert "AAPL" in result
        assert result["AAPL"] == 320193
    
    def test_ticker_map_uppercase_conversion(self, httpx_mock, mock_sec_company_tickers):
        """Test that tickers are converted to uppercase."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            json=mock_sec_company_tickers
        )
        
        result = ticker_map()
        
        # All keys should be uppercase
        for ticker in result.keys():
            assert ticker == ticker.upper()
    
    def test_ticker_map_cik_as_int(self, httpx_mock, mock_sec_company_tickers):
        """Test that CIKs are returned as integers."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            json=mock_sec_company_tickers
        )
        
        result = ticker_map()
        
        for cik in result.values():
            assert isinstance(cik, int)
    
    def test_ticker_map_api_failure(self, httpx_mock):
        """Test handling of API failure."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            status_code=503
        )
        
        with pytest.raises(HTTPError):
            ticker_map()


# =============================================================================
# Unit Tests: company_facts
# =============================================================================

@pytest.mark.unit
@pytest.mark.mock_sec
class TestCompanyFacts:
    """Test company facts retrieval from SEC API."""
    
    def test_company_facts_success(self, httpx_mock, mock_sec_company_facts):
        """Test successful company facts retrieval."""
        # Mock only the company facts endpoint (not company_tickers)
        httpx_mock.add_response(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
            json=mock_sec_company_facts
        )
        
        cik = 789019
        result = company_facts(cik)
        
        assert result["cik"] == cik
        assert result["entityName"] == "MICROSOFT CORPORATION"
        assert "facts" in result
        assert "us-gaap" in result["facts"]
    
    def test_company_facts_cik_formatting(self, httpx_mock, mock_sec_company_facts):
        """Test that CIK is properly zero-padded in URL."""
        httpx_mock.add_response(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
            json=mock_sec_company_facts
        )
        
        company_facts(789019)
        
        request = httpx_mock.get_request()
        assert "CIK0000789019" in str(request.url)
    
    def test_company_facts_invalid_cik(self, httpx_mock):
        """Test handling of invalid CIK."""
        httpx_mock.add_response(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK9999999999.json",
            status_code=404
        )
        
        with pytest.raises(HTTPError):
            company_facts(9999999999)


# =============================================================================
# Unit Tests: Database Operations
# =============================================================================

@pytest.mark.unit
@pytest.mark.db
class TestDatabaseOperations:
    """Test database upsert operations."""
    
    def test_upsert_company_new(self, db_session):
        """Test inserting a new company."""
        from app.db.models import Company
        
        upsert_company("0000789019", "MSFT", "Microsoft Corporation")
        
        company = db_session.query(Company).filter_by(cik="0000789019").first()
        assert company is not None
        assert company.ticker == "MSFT"
        assert company.name == "Microsoft Corporation"
    
    def test_upsert_company_existing(self, db_session, create_test_company):
        """Test updating an existing company."""
        from app.db.models import Company
        
        # Create initial company
        create_test_company(cik="0000789019", ticker="MSFT", name="Old Name")
        
        # Update with new name
        upsert_company("0000789019", "MSFT", "New Name")
        
        company = db_session.query(Company).filter_by(cik="0000789019").first()
        assert company.name == "New Name"
        assert company.ticker == "MSFT"
    
    def test_upsert_company_null_name(self, db_session):
        """Test upserting company with null name."""
        upsert_company("0000789019", "MSFT", None)
        
        from app.db.models import Company
        company = db_session.query(Company).filter_by(cik="0000789019").first()
        assert company is not None
        assert company.ticker == "MSFT"
        assert company.name is None
    
    def test_upsert_filing_new(self, db_session, create_test_company):
        """Test inserting a new filing."""
        from app.db.models import Filing
        from datetime import date
        
        create_test_company()
        
        filing_id = upsert_filing(
            cik="0000789019",
            form="10-K",
            accession="0000789019-23-000030",
            period_end="2023-06-30"
        )
        
        assert filing_id is not None
        filing = db_session.query(Filing).filter_by(id=filing_id).first()
        assert filing.form == "10-K"
        assert filing.accession == "0000789019-23-000030"
        assert filing.period_end == date(2023, 6, 30)
    
    def test_upsert_filing_duplicate(self, db_session, create_test_company, create_test_filing):
        """Test that duplicate filings return None (conflict)."""
        create_test_company()
        create_test_filing(accession="TEST-DUPLICATE")
        
        # Try to insert duplicate
        result = upsert_filing(
            cik="0000789019",
            form="10-K",
            accession="TEST-DUPLICATE",
            period_end="2023-06-30"
        )
        
        assert result is None
    
    def test_upsert_filing_date_casting(self, db_session, create_test_company):
        """Test that period_end string is properly cast to date."""
        from app.db.models import Filing
        from datetime import date
        
        create_test_company()
        
        filing_id = upsert_filing(
            cik="0000789019",
            form="10-K",
            accession="TEST-DATE",
            period_end="2023-12-31"
        )
        
        filing = db_session.query(Filing).filter_by(id=filing_id).first()
        assert isinstance(filing.period_end, date)
        assert filing.period_end == date(2023, 12, 31)


# =============================================================================
# Unit Tests: Data Parsing
# =============================================================================

@pytest.mark.unit
class TestDataParsing:
    """Test parsing of SEC financial data."""
    
    def test_pick_first_units_success(self, mock_sec_company_facts):
        """Test successful extraction of units from facts."""
        result = _pick_first_units(mock_sec_company_facts, ["Revenues"])
        
        assert result is not None
        assert "USD" in result
        assert len(result["USD"]) > 0
    
    def test_pick_first_units_fallback(self, mock_sec_company_facts):
        """Test fallback to second tag in list."""
        # Try non-existent tag first, then valid one
        result = _pick_first_units(mock_sec_company_facts, ["NonExistentTag", "Revenues"])
        
        assert result is not None
        assert "USD" in result
    
    def test_pick_first_units_no_match(self, mock_sec_company_facts):
        """Test when no tags match."""
        result = _pick_first_units(mock_sec_company_facts, ["NonExistentTag1", "NonExistentTag2"])
        
        assert result is None
    
    def test_pick_first_units_empty_facts(self):
        """Test with empty facts dictionary."""
        empty_facts = {"facts": {"us-gaap": {}}}
        result = _pick_first_units(empty_facts, ["Revenues"])
        
        assert result is None


# =============================================================================
# Integration Tests: Full Ingestion
# =============================================================================

@pytest.mark.integration
@pytest.mark.db
@pytest.mark.mock_sec
class TestIngestionIntegration:
    """Test end-to-end ingestion workflow."""
    
    def test_ingest_company_full_workflow(
        self,
        db_session,
        mock_httpx_client,
        mock_sec_company_facts
    ):
        """Test complete ingestion from ticker to database."""
        from app.db.models import Company, Filing
        
        # Run ingestion
        result = ingest_companyfacts_richer_by_ticker("MSFT")
        
        # Verify company was created
        company = db_session.query(Company).filter_by(ticker="MSFT").first()
        assert company is not None
        assert company.name == "MICROSOFT CORPORATION"
        assert company.cik == "0000789019"
        
        # Verify filings were created
        filings = db_session.query(Filing).filter_by(cik="0000789019").all()
        assert len(filings) > 0
        
        # Verify filing data
        filing = filings[0]
        assert filing.form == "10-K"
        assert filing.accession.startswith("FACTS-")
    
    def test_ingest_company_invalid_ticker(self, db_session, httpx_mock):
        """Test ingestion with invalid ticker."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            json={"0": {"cik_str": 789019, "ticker": "MSFT"}}
        )
        
        with pytest.raises(ValueError, match="No CIK found for INVALID_TICKER"):
            ingest_companyfacts_richer_by_ticker("INVALID_TICKER")
    
    def test_ingest_company_api_failure(self, db_session, httpx_mock):
        """Test ingestion when SEC API fails."""
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            status_code=503
        )
        
        with pytest.raises(HTTPError):
            ingest_companyfacts_richer_by_ticker("MSFT")
    
    @pytest.mark.slow
    def test_ingest_company_multiple_years(
        self,
        db_session,
        mock_httpx_client,
        mock_sec_company_facts
    ):
        """Test that multiple years of data are ingested."""
        from app.db.models import Filing
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        filings = db_session.query(Filing).filter_by(cik="0000789019").all()
        
        # Should have filings for multiple years
        years = set()
        for filing in filings:
            if filing.accession.startswith("FACTS-"):
                year = int(filing.accession.split("-")[-1])
                years.add(year)
        
        assert len(years) >= 3  # Should have 2021, 2022, 2023


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_company_name(self, db_session):
        """Test handling of empty company name."""
        upsert_company("0000123456", "TEST", "")
        
        from app.db.models import Company
        company = db_session.query(Company).filter_by(cik="0000123456").first()
        assert company is not None
        assert company.name == ""
    
    def test_special_characters_in_name(self, db_session):
        """Test handling of special characters in company name."""
        special_name = "Test & Company, Inc. (Holdings) [Sub]"
        upsert_company("0000123456", "TEST", special_name)
        
        from app.db.models import Company
        company = db_session.query(Company).filter_by(cik="0000123456").first()
        assert company.name == special_name
    
    def test_very_long_cik(self, db_session):
        """Test handling of maximum length CIK."""
        long_cik = "9999999999"  # 10 digits
        upsert_company(long_cik, "TEST", "Test Company")
        
        from app.db.models import Company
        company = db_session.query(Company).filter_by(cik=long_cik).first()
        assert company is not None
    
    def test_filing_with_null_values(self, db_session, create_test_company):
        """Test filing insertion with null optional values."""
        create_test_company()
        
        filing_id = upsert_filing(
            cik="0000789019",
            form=None,
            accession="TEST-NULL",
            period_end=None
        )
        
        assert filing_id is not None
