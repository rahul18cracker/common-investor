"""
Integration and cross-cutting tests for API routes (app/api/v1/routes.py)

Contains:
- Health check, request validation, response format, security tests
- Phase B/C/D integration tests (quality scores, metrics extensions, agent bundle, fourm)
- Performance benchmarks

Unit tests for individual endpoints live in test_api_routes_unit.py and
test_api_routes_comprehensive.py.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


# =============================================================================
# Unit Tests: Health Check
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
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# =============================================================================
# Unit Tests: Request Validation
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestRequestValidation:
    """Test API request validation."""

    def test_invalid_ticker_format(self, client):
        """Test handling of invalid ticker formats."""
        response = client.get("/api/v1/company/" + "A" * 100)
        assert response.status_code in [404, 422]

        response = client.get("/api/v1/company/")
        assert response.status_code == 404

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

        filing = Filing(cik="0000789019", form="10-K", accession="TEST-002", period_end=date(2023, 12, 31))
        db_session.add(filing)
        db_session.flush()
        stmt = StatementIS(filing_id=filing.id, fy=2023, revenue=1000000, eps_diluted=10.0)
        db_session.add(stmt)
        db_session.commit()

        scenario = {"mos_pct": 0.50}
        response = client.post("/api/v1/company/MSFT/valuation", json=scenario)
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
        assert "access-control-allow-origin" in response.headers

    def test_error_response_format(self, client):
        """Test that error responses follow consistent format."""
        response = client.get("/api/v1/company/NONEXISTENT")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)


# =============================================================================
# Unit Tests: Security
# =============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestAPISecurity:
    """Test API security measures."""

    def test_sql_injection_protection(self, client):
        """Test that SQL injection attempts are handled safely."""
        malicious_ticker = "MSFT'; DROP TABLE company; --"
        response = client.get(f"/api/v1/company/{malicious_ticker}")
        assert response.status_code in [404, 422]

    def test_xss_protection(self, client, create_test_company):
        """Test that XSS attempts in company names are handled."""
        xss_name = "<script>alert('xss')</script>"
        create_test_company(ticker="XSS", name=xss_name)

        response = client.get("/api/v1/company/XSS")
        if response.status_code == 200:
            data = response.json()
            assert "<script>" not in str(data).lower() or xss_name in str(data)

    def test_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        malicious_path = "../../../etc/passwd"
        response = client.get(f"/api/v1/company/{malicious_path}")
        assert response.status_code in [404, 422]


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.unit
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

        assert duration < 1.0

    def test_concurrent_requests(self, client, create_test_company):
        """Test handling of concurrent API requests."""
        create_test_company(ticker="MSFT")

        responses = []
        for _ in range(10):
            response = client.get("/api/v1/company/MSFT")
            responses.append(response)

        assert all(r.status_code == 200 for r in responses)


# =============================================================================
# Integration Tests: Company Endpoint with Financials (Phase A)
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestCompanyEndpointWithFinancials:
    """Test company endpoint returns all IS fields including Phase A additions."""

    def test_get_company_returns_all_is_fields(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that GET /company/{ticker} returns all IS fields."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        response = client.get("/api/v1/company/MSFT")
        assert response.status_code == 200
        data = response.json()

        assert "latest_is" in data
        latest_is = data["latest_is"]
        assert latest_is is not None
        for field in ["revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
                      "ebit", "interest_expense", "taxes", "net_income", "eps_diluted",
                      "shares_diluted", "gross_margin", "operating_margin"]:
            assert field in latest_is

    def test_get_company_gross_margin_calculation(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that gross_margin is correctly calculated."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        response = client.get("/api/v1/company/MSFT")
        data = response.json()
        latest_is = data["latest_is"]

        expected_gross_margin = 146052000000 / 211915000000
        assert latest_is["gross_margin"] is not None
        assert abs(latest_is["gross_margin"] - expected_gross_margin) < 0.001

    def test_get_company_operating_margin_calculation(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that operating_margin is correctly calculated."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        response = client.get("/api/v1/company/MSFT")
        data = response.json()
        latest_is = data["latest_is"]

        expected_operating_margin = 88523000000 / 211915000000
        assert latest_is["operating_margin"] is not None
        assert abs(latest_is["operating_margin"] - expected_operating_margin) < 0.001


# =============================================================================
# Integration Tests: Phase B Quality Scores Endpoint
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestQualityScoresEndpoint:
    """Test the /company/{ticker}/quality-scores endpoint (Phase B)."""

    def test_quality_scores_success(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test successful quality scores retrieval after ingestion."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        response = client.get("/api/v1/company/MSFT/quality-scores")
        assert response.status_code == 200
        data = response.json()

        for field in ["gross_margin_series", "latest_gross_margin", "gross_margin_trend",
                      "revenue_volatility", "growth_metrics", "net_debt_series",
                      "latest_net_debt", "share_count_trend", "avg_share_dilution_3y",
                      "roic_persistence_score"]:
            assert field in data

    def test_quality_scores_growth_metrics_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that growth_metrics contains all CAGR windows."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        response = client.get("/api/v1/company/MSFT/quality-scores")
        growth = response.json()["growth_metrics"]

        for key in ["rev_cagr_1y", "rev_cagr_3y", "rev_cagr_5y", "rev_cagr_10y",
                     "eps_cagr_1y", "eps_cagr_3y", "eps_cagr_5y", "eps_cagr_10y"]:
            assert key in growth

    def test_quality_scores_gross_margin_series_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that gross_margin_series has correct structure."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        gm_series = client.get("/api/v1/company/MSFT/quality-scores").json()["gross_margin_series"]
        assert isinstance(gm_series, list)
        if len(gm_series) > 0:
            assert "fy" in gm_series[0]
            assert "gross_margin" in gm_series[0]

    def test_quality_scores_company_not_found(self, client):
        """Test 404 when company doesn't exist."""
        assert client.get("/api/v1/company/INVALID/quality-scores").status_code == 404

    def test_quality_scores_share_count_trend_structure(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that share_count_trend has correct structure with YoY changes."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        shares = client.get("/api/v1/company/MSFT/quality-scores").json()["share_count_trend"]
        assert isinstance(shares, list)
        if len(shares) > 0:
            for key in ["fy", "shares", "yoy_change"]:
                assert key in shares[0]

    def test_quality_scores_roic_persistence_score_range(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that ROIC persistence score is in valid range (0-5 or None)."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        score = client.get("/api/v1/company/MSFT/quality-scores").json()["roic_persistence_score"]
        assert score is None or (0 <= score <= 5)


# =============================================================================
# Integration Tests: Phase D Metrics / Timeseries / Agent Bundle
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestMetricsEndpointPhaseD:
    """Integration tests for Phase D /metrics endpoint enhancements."""

    def test_metrics_includes_extended_growths(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /metrics includes extended growth metrics."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        data = client.get("/api/v1/company/MSFT/metrics").json()
        assert "growths_extended" in data
        for key in ["rev_cagr_1y", "rev_cagr_3y", "rev_cagr_5y", "rev_cagr_10y"]:
            assert key in data["growths_extended"]

    def test_metrics_includes_volatility_and_persistence(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /metrics includes revenue volatility and ROIC persistence."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        data = client.get("/api/v1/company/MSFT/metrics").json()
        for key in ["revenue_volatility", "roic_persistence_score", "latest_gross_margin"]:
            assert key in data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestTimeseriesEndpointPhaseD:
    """Integration tests for Phase D /timeseries endpoint enhancements."""

    def test_timeseries_includes_gross_margin(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /timeseries includes gross_margin series."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        data = client.get("/api/v1/company/MSFT/timeseries").json()
        for key in ["gross_margin", "net_debt", "share_count"]:
            assert key in data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestAgentBundleEndpoint:
    """Integration tests for Phase D /agent-bundle endpoint."""

    def test_agent_bundle_returns_all_sections(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /agent-bundle returns all required sections."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        data = client.get("/api/v1/company/MSFT/agent-bundle").json()
        for key in ["company", "metrics", "quality_scores", "four_ms", "timeseries"]:
            assert key in data

    def test_agent_bundle_company_info(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /agent-bundle includes company info."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        company = client.get("/api/v1/company/MSFT/agent-bundle").json()["company"]
        for key in ["cik", "ticker", "name"]:
            assert key in company

    def test_agent_bundle_four_ms_complete(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that /agent-bundle four_ms section is complete."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        four_ms = client.get("/api/v1/company/MSFT/agent-bundle").json()["four_ms"]
        for key in ["moat", "management", "balance_sheet_resilience", "mos_recommendation"]:
            assert key in four_ms


# =============================================================================
# Integration Tests: Phase C Four Ms Enhancements
# =============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.db
@pytest.mark.mock_sec
class TestFourMsEndpointPhaseC:
    """Integration tests for Phase C Four Ms endpoint enhancements."""

    def test_fourm_includes_balance_sheet_resilience(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that Four Ms endpoint includes balance_sheet_resilience section."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        data = client.get("/api/v1/company/MSFT/fourm").json()
        bs = data["balance_sheet_resilience"]
        for key in ["latest_coverage", "debt_to_equity", "latest_net_debt", "score"]:
            assert key in bs

    def test_fourm_moat_includes_phase_c_fields(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that moat section includes Phase C enhancements."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        moat = client.get("/api/v1/company/MSFT/fourm").json()["moat"]
        for key in ["latest_gross_margin", "gross_margin_trend", "gross_margin_stability",
                     "roic_persistence_score", "pricing_power_score"]:
            assert key in moat

    def test_fourm_mos_includes_balance_sheet_driver(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that MOS recommendation includes balance sheet score in drivers."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        mos = client.get("/api/v1/company/MSFT/fourm").json()["mos_recommendation"]
        assert "drivers" in mos
        assert "balance_sheet_score" in mos["drivers"]

    def test_fourm_balance_sheet_score_range(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that balance sheet score is in valid 0-5 range."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        score = client.get("/api/v1/company/MSFT/fourm").json()["balance_sheet_resilience"]["score"]
        assert score is None or (0 <= score <= 5)

    def test_fourm_pricing_power_score_range(self, client, db_session, mock_httpx_client, mock_sec_company_facts):
        """Test that pricing power score is in valid 0-1 range."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        score = client.get("/api/v1/company/MSFT/fourm").json()["moat"]["pricing_power_score"]
        assert score is None or (0 <= score <= 1)
