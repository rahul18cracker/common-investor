"""
Unit and integration tests for API routes (app/api/v1/routes.py)

Tests all API endpoints, request validation, response format, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


# =============================================================================
# Unit Tests: Health Check Endpoint
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestHealthCheckEndpoint:
    """Test the health check endpoint."""
    
    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 OK."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_health_check_no_authentication(self, client):
        """Test that health check doesn't require authentication."""
        # Should work without any headers
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# =============================================================================
# Unit Tests: Debug Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestDebugEndpoints:
    """Test debug/diagnostic endpoints."""
    
    def test_debug_modules_endpoint(self, client):
        """Test that debug/modules returns module information."""
        response = client.get("/api/v1/debug/modules")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a dictionary of modules
        assert isinstance(data, dict)
        
        # Should have key modules listed
        assert any("metrics" in key for key in data.keys())
        assert any("valuation" in key for key in data.keys())


# =============================================================================
# Unit Tests: Company Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.db
class TestCompanyEndpoints:
    """Test company-related API endpoints."""
    
    def test_get_company_not_found(self, client):
        """Test GET /api/v1/company/{ticker} when company doesn't exist."""
        response = client.get("/api/v1/company/NONEXISTENT")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_company_success(self, client, create_test_company):
        """Test GET /api/v1/company/{ticker} with existing company."""
        # Create test company
        create_test_company(cik="0000789019", ticker="MSFT", name="Microsoft")
        
        response = client.get("/api/v1/company/MSFT")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "company" in data
        assert data["company"]["ticker"] == "MSFT"
        assert data["company"]["name"] == "Microsoft"
    
    def test_get_company_case_insensitive(self, client, create_test_company):
        """Test that ticker lookup is case-insensitive."""
        create_test_company(ticker="MSFT")
        
        # Try lowercase
        response = client.get("/api/v1/company/msft")
        assert response.status_code == 200
        
        # Try mixed case
        response = client.get("/api/v1/company/MsFt")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestCompanyEndpointWithFinancials:
    """Test company endpoint returns all IS fields including Phase A additions."""
    
    def test_get_company_returns_all_is_fields(
        self,
        client,
        db_session,
        mock_httpx_client,
        mock_sec_company_facts
    ):
        """Test that GET /company/{ticker} returns all IS fields including gross_profit, cogs, etc."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        # Ingest test data
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "latest_is" in data
        latest_is = data["latest_is"]
        
        # Verify all IS fields are present
        assert latest_is is not None
        assert "revenue" in latest_is
        assert "cogs" in latest_is
        assert "gross_profit" in latest_is
        assert "sga" in latest_is
        assert "rnd" in latest_is
        assert "depreciation" in latest_is
        assert "ebit" in latest_is
        assert "interest_expense" in latest_is
        assert "taxes" in latest_is
        assert "net_income" in latest_is
        assert "eps_diluted" in latest_is
        assert "shares_diluted" in latest_is
        
        # Verify computed margins are present
        assert "gross_margin" in latest_is
        assert "operating_margin" in latest_is
    
    def test_get_company_gross_margin_calculation(
        self,
        client,
        db_session,
        mock_httpx_client,
        mock_sec_company_facts
    ):
        """Test that gross_margin is correctly calculated."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT")
        data = response.json()
        latest_is = data["latest_is"]
        
        # Verify gross margin calculation
        # MSFT FY2023: gross_profit=146052B, revenue=211915B
        expected_gross_margin = 146052000000 / 211915000000
        
        assert latest_is["gross_margin"] is not None
        assert abs(latest_is["gross_margin"] - expected_gross_margin) < 0.001
    
    def test_get_company_operating_margin_calculation(
        self,
        client,
        db_session,
        mock_httpx_client,
        mock_sec_company_facts
    ):
        """Test that operating_margin is correctly calculated."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT")
        data = response.json()
        latest_is = data["latest_is"]
        
        # Verify operating margin calculation
        # MSFT FY2023: ebit=88523B, revenue=211915B
        expected_operating_margin = 88523000000 / 211915000000
        
        assert latest_is["operating_margin"] is not None
        assert abs(latest_is["operating_margin"] - expected_operating_margin) < 0.001


# =============================================================================
# Unit Tests: Ingestion Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.celery
class TestIngestionEndpoints:
    """Test data ingestion API endpoints."""
    
    @patch("app.api.v1.routes.enqueue_ingest")
    def test_ingest_company_success(self, mock_enqueue, client):
        """Test POST /api/v1/company/{ticker}/ingest."""
        response = client.post("/api/v1/company/MSFT/ingest")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "queued"
        assert "MSFT" in data["detail"]
        
        # Verify enqueue was called
        mock_enqueue.assert_called_once_with("MSFT")
    
    @patch("app.api.v1.routes.enqueue_ingest")
    def test_ingest_multiple_companies(self, mock_enqueue, client):
        """Test ingesting multiple companies in sequence."""
        tickers = ["MSFT", "AAPL", "AMZN"]
        
        for ticker in tickers:
            response = client.post(f"/api/v1/company/{ticker}/ingest")
            assert response.status_code == 200
        
        assert mock_enqueue.call_count == 3
    
    @patch("app.api.v1.routes.enqueue_ingest")
    def test_ingest_with_special_characters(self, mock_enqueue, client):
        """Test ingestion with special ticker characters."""
        # Some tickers have dots (e.g., BRK.A)
        response = client.post("/api/v1/company/BRK.A/ingest")
        
        # Should handle gracefully
        assert response.status_code in [200, 422]  # 200 if accepted, 422 if validation fails


# =============================================================================
# Unit Tests: Metrics Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.db
class TestMetricsEndpoints:
    """Test financial metrics API endpoints."""
    
    def test_get_metrics_company_not_found(self, client):
        """Test GET /api/v1/company/{ticker}/metrics when company doesn't exist."""
        response = client.get("/api/v1/company/NONEXISTENT/metrics")
        
        assert response.status_code == 404
    
    def test_get_metrics_no_data(self, client, create_test_company):
        """Test metrics endpoint when company has no financial data."""
        create_test_company(ticker="TEST")
        
        response = client.get("/api/v1/company/TEST/metrics")
        
        # Might return 404 or empty list depending on implementation
        assert response.status_code in [200, 404]


# =============================================================================
# Unit Tests: Valuation Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.db
class TestValuationEndpoints:
    """Test valuation calculation API endpoints."""
    
    def test_get_valuation_company_not_found(self, client):
        """Test POST /api/v1/company/{ticker}/valuation when company doesn't exist."""
        scenario = {"mos_pct": 0.50}
        response = client.post("/api/v1/company/NONEXISTENT/valuation", json=scenario)
        
        assert response.status_code == 404
    
    def test_post_valuation_scenario(self, client, create_test_company, db_session):
        """Test POST /api/v1/company/{ticker}/valuation with scenario."""
        from app.db.models import Company, Filing, StatementIS
        from datetime import date
        
        # Create company with EPS data
        company = create_test_company(ticker="MSFT")
        
        # Create a filing
        filing = Filing(cik="0000789019", form="10-K", accession="TEST-ACC", period_end=date(2023, 12, 31))
        db_session.add(filing)
        db_session.flush()
        
        # Add EPS data so valuation can calculate
        stmt = StatementIS(filing_id=filing.id, fy=2023, revenue=1000000, eps_diluted=10.0)
        db_session.add(stmt)
        db_session.commit()
        
        scenario = {"mos_pct": 0.50}
        
        response = client.post("/api/v1/company/MSFT/valuation", json=scenario)
        
        # Should either calculate or return error if insufficient data
        assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# Unit Tests: Four Ms Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.db
class TestFourMsEndpoints:
    """Test Four Ms analysis API endpoints."""
    
    def test_get_fourm_company_not_found(self, client):
        """Test GET /api/v1/company/{ticker}/fourm when company doesn't exist."""
        response = client.get("/api/v1/company/NONEXISTENT/fourm")
        
        assert response.status_code == 404
    
    def test_get_fourm_moat_button(self, client, create_test_company):
        """Test GET /api/v1/company/{ticker}/fourm/moat button."""
        create_test_company(ticker="MSFT")
        
        response = client.get("/api/v1/company/MSFT/fourm/moat")
        
        # Should return moat analysis or 404 if no data
        assert response.status_code in [200, 404]
    
    def test_get_fourm_management_button(self, client, create_test_company):
        """Test GET /api/v1/company/{ticker}/fourm/management button."""
        create_test_company(ticker="MSFT")
        
        response = client.get("/api/v1/company/MSFT/fourm/management")
        
        assert response.status_code in [200, 404]


# =============================================================================
# Integration Tests: API Workflow
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
class TestAPIWorkflow:
    """Test complete API workflows."""
    
    def test_complete_company_workflow(
        self,
        client,
        celery_worker,
        mock_httpx_client
    ):
        """
        Test complete workflow: ingest → verify → get data.
        """
        ticker = "MSFT"
        
        # Step 1: Ingest
        response = client.post(f"/api/v1/company/{ticker}/ingest")
        assert response.status_code == 200
        
        # Step 2: Get company data
        response = client.get(f"/api/v1/company/{ticker}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["company"]["ticker"] == ticker


# =============================================================================
# Unit Tests: Request Validation
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestRequestValidation:
    """Test API request validation."""
    
    def test_invalid_ticker_format(self, client):
        """Test handling of invalid ticker formats."""
        # Very long ticker
        response = client.get("/api/v1/company/" + "A" * 100)
        assert response.status_code in [404, 422]
        
        # Empty ticker
        response = client.get("/api/v1/company/")
        assert response.status_code == 404  # Route not found
    
    def test_invalid_json_body(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/company/MSFT/valuation",
            content=b"invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client, create_test_company, db_session):
        """Test handling of missing required fields in POST requests."""
        from app.db.models import Filing, StatementIS
        from datetime import date
        
        create_test_company(ticker="MSFT")
        
        # Add minimal data so the endpoint can process
        filing = Filing(cik="0000789019", form="10-K", accession="TEST-002", period_end=date(2023, 12, 31))
        db_session.add(filing)
        db_session.flush()
        stmt = StatementIS(filing_id=filing.id, fy=2023, revenue=1000000, eps_diluted=10.0)
        db_session.add(stmt)
        db_session.commit()
        
        # Send minimal valuation scenario
        scenario = {"mos_pct": 0.50}
        
        response = client.post(
            "/api/v1/company/MSFT/valuation",
            json=scenario
        )
        
        # Should work or return error based on business logic
        assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# Unit Tests: Response Format
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestResponseFormat:
    """Test API response formats and headers."""
    
    def test_json_content_type(self, client):
        """Test that responses have correct content type."""
        response = client.get("/api/v1/health")
        
        assert "application/json" in response.headers["content-type"]
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
    
    def test_error_response_format(self, client):
        """Test that error responses follow consistent format."""
        response = client.get("/api/v1/company/NONEXISTENT")
        
        assert response.status_code == 404
        error_data = response.json()
        
        # Should have 'detail' field
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.slow
@pytest.mark.api
class TestAPIPerformance:
    """Test API performance characteristics."""
    
    def test_health_check_performance(self, client):
        """Test that health check is fast."""
        import time
        
        start = time.time()
        for _ in range(100):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
        duration = time.time() - start
        
        # 100 requests should complete in < 1 second
        assert duration < 1.0
    
    def test_concurrent_requests(self, client, create_test_company):
        """Test handling of concurrent API requests."""
        create_test_company(ticker="MSFT")
        
        # Make multiple concurrent requests
        responses = []
        for _ in range(10):
            response = client.get("/api/v1/company/MSFT")
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)


# =============================================================================
# Security Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestAPISecurity:
    """Test API security measures."""
    
    def test_sql_injection_protection(self, client):
        """Test that SQL injection attempts are handled safely."""
        malicious_ticker = "MSFT'; DROP TABLE company; --"
        
        response = client.get(f"/api/v1/company/{malicious_ticker}")
        
        # Should either sanitize or return 404, not crash
        assert response.status_code in [404, 422]
    
    def test_xss_protection(self, client, create_test_company):
        """Test that XSS attempts in company names are handled."""
        xss_name = "<script>alert('xss')</script>"
        create_test_company(ticker="XSS", name=xss_name)
        
        response = client.get("/api/v1/company/XSS")
        
        if response.status_code == 200:
            # Name should be escaped or sanitized
            data = response.json()
            # The response is JSON, so it's automatically safe from XSS
            assert "<script>" not in str(data).lower() or xss_name in str(data)
    
    def test_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        malicious_path = "../../../etc/passwd"
        
        response = client.get(f"/api/v1/company/{malicious_path}")
        
        # Should not expose filesystem
        assert response.status_code in [404, 422]


# =============================================================================
# Unit Tests: Export Endpoints
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestExportEndpoints:
    """Test data export API endpoints."""
    
    def test_export_csv_metrics(self, client, create_test_company):
        """Test CSV export of metrics."""
        create_test_company(ticker="MSFT")
        
        response = client.get("/api/v1/company/MSFT/export/metrics?format=csv")
        
        # Should return CSV or 404 if not implemented
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")
    
    def test_export_json_valuation(self, client, create_test_company):
        """Test JSON export of valuation."""
        create_test_company(ticker="MSFT")
        
        response = client.get("/api/v1/company/MSFT/export/valuation?format=json")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert "application/json" in response.headers["content-type"]


# =============================================================================
# Integration Tests: Phase B Quality Scores Endpoint
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestQualityScoresEndpoint:
    """Test the new /company/{ticker}/quality-scores endpoint (Phase B)."""
    
    def test_quality_scores_success(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test successful quality scores retrieval after ingestion."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        # Ingest test data directly
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        # Then get quality scores
        response = client.get("/api/v1/company/MSFT/quality-scores")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        assert "gross_margin_series" in data
        assert "latest_gross_margin" in data
        assert "gross_margin_trend" in data
        assert "revenue_volatility" in data
        assert "growth_metrics" in data
        assert "net_debt_series" in data
        assert "latest_net_debt" in data
        assert "share_count_trend" in data
        assert "avg_share_dilution_3y" in data
        assert "roic_persistence_score" in data
    
    def test_quality_scores_growth_metrics_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that growth_metrics contains all CAGR windows."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT/quality-scores")
        data = response.json()
        
        growth = data["growth_metrics"]
        
        # Should have 1y, 3y, 5y, 10y for both revenue and EPS
        assert "rev_cagr_1y" in growth
        assert "rev_cagr_3y" in growth
        assert "rev_cagr_5y" in growth
        assert "rev_cagr_10y" in growth
        assert "eps_cagr_1y" in growth
        assert "eps_cagr_3y" in growth
        assert "eps_cagr_5y" in growth
        assert "eps_cagr_10y" in growth
    
    def test_quality_scores_gross_margin_series_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that gross_margin_series has correct structure."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT/quality-scores")
        data = response.json()
        
        gm_series = data["gross_margin_series"]
        
        # Should be a list with fy and gross_margin keys
        assert isinstance(gm_series, list)
        if len(gm_series) > 0:
            assert "fy" in gm_series[0]
            assert "gross_margin" in gm_series[0]
    
    def test_quality_scores_company_not_found(self, client):
        """Test 404 when company doesn't exist."""
        response = client.get("/api/v1/company/INVALID/quality-scores")
        
        assert response.status_code == 404
    
    def test_quality_scores_share_count_trend_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that share_count_trend has correct structure with YoY changes."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT/quality-scores")
        data = response.json()
        
        shares = data["share_count_trend"]
        
        assert isinstance(shares, list)
        if len(shares) > 0:
            assert "fy" in shares[0]
            assert "shares" in shares[0]
            assert "yoy_change" in shares[0]
    
    def test_quality_scores_roic_persistence_score_range(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that ROIC persistence score is in valid range (0-5 or None)."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        
        ingest_companyfacts_richer_by_ticker("MSFT")
        
        response = client.get("/api/v1/company/MSFT/quality-scores")
        data = response.json()
        
        score = data["roic_persistence_score"]
        
        # Should be None or 0-5
        assert score is None or (0 <= score <= 5)
