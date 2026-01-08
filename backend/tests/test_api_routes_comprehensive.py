"""
Comprehensive unit tests for API v1 routes.

Tests all endpoints with mocked dependencies for isolation.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


pytestmark = pytest.mark.unit


# Fixtures for common mocks
@pytest.fixture
def mock_execute():
    with patch("app.api.v1.routes.execute") as mock:
        yield mock


@pytest.fixture
def mock_background_tasks():
    return MagicMock()


class TestCompanyEndpoints:
    """Test company listing and summary endpoints."""

    def test_list_companies_success(self, mock_execute):
        """Test successful company listing."""
        mock_execute.return_value.fetchall.return_value = [
            (1, "0000789019", "MSFT", "Microsoft Corporation", 10),
            (2, "0001318605", "TSLA", "Tesla Inc", 8),
        ]
        
        from app.api.v1.routes import list_companies
        result = list_companies()
        
        assert result["count"] == 2
        assert len(result["companies"]) == 2
        assert result["companies"][0]["ticker"] == "MSFT"

    def test_list_companies_empty(self, mock_execute):
        """Test listing when no companies exist."""
        mock_execute.return_value.fetchall.return_value = []
        
        from app.api.v1.routes import list_companies
        result = list_companies()
        
        assert result["count"] == 0
        assert result["companies"] == []

    def test_company_summary_success(self, mock_execute):
        """Test successful company summary retrieval."""
        # Updated to match new API response: (fy, revenue, cogs, gross_profit, sga, rnd, 
        #   depreciation, ebit, interest_expense, taxes, net_income, eps_diluted, shares_diluted)
        mock_execute.return_value.first.side_effect = [
            (1, "0000789019", "MSFT", "Microsoft Corporation"),
            (2023, 211915.0, 65863.0, 146052.0, 22759.0, 27195.0, 13861.0, 88523.0, 1968.0, 16950.0, 72361.0, 9.72, 7446.0),
        ]
        
        from app.api.v1.routes import company_summary
        result = company_summary("MSFT")
        
        assert result["company"]["ticker"] == "MSFT"
        assert result["latest_is"]["fy"] == 2023
        assert result["latest_is"]["revenue"] == 211915.0
        assert result["latest_is"]["cogs"] == 65863.0
        assert result["latest_is"]["gross_profit"] == 146052.0
        assert result["latest_is"]["gross_margin"] is not None

    def test_company_summary_not_found(self, mock_execute):
        """Test 404 when company not found."""
        mock_execute.return_value.first.return_value = None
        
        from app.api.v1.routes import company_summary
        with pytest.raises(HTTPException) as exc:
            company_summary("INVALID")
        assert exc.value.status_code == 404

    def test_company_summary_no_financial_data(self, mock_execute):
        """Test company summary when no financial data exists."""
        mock_execute.return_value.first.side_effect = [
            (1, "0000789019", "MSFT", "Microsoft Corporation"),
            None,
        ]
        
        from app.api.v1.routes import company_summary
        result = company_summary("MSFT")
        
        assert result["company"]["ticker"] == "MSFT"
        assert result["latest_is"] is None


class TestSeedEndpoints:
    """Test database seeding endpoints."""

    @patch("app.api.v1.routes.enqueue_ingest")
    def test_seed_database_default_tickers(self, mock_enqueue, mock_background_tasks):
        """Test seeding with default tickers."""
        from app.api.v1.routes import seed_database, SeedRequest
        
        body = SeedRequest()
        result = seed_database(body, mock_background_tasks)
        
        assert result["status"] == "queued"
        assert len(result["tickers"]) > 0

    @patch("app.api.v1.routes.enqueue_ingest")
    def test_seed_database_custom_tickers(self, mock_enqueue, mock_background_tasks):
        """Test seeding with custom ticker list."""
        from app.api.v1.routes import seed_database, SeedRequest
        
        body = SeedRequest(tickers=["AAPL", "GOOGL"])
        result = seed_database(body, mock_background_tasks)
        
        assert result["status"] == "queued"
        assert result["tickers"] == ["AAPL", "GOOGL"]

    def test_seed_status(self, mock_execute):
        """Test seed status endpoint."""
        mock_execute.return_value.first.return_value = (5,)
        
        from app.api.v1.routes import seed_status
        result = seed_status()
        
        assert result["companies_loaded"] == 5
        assert result["is_seeded"] is True

    @patch("app.api.v1.routes.enqueue_ingest")
    def test_ingest_company(self, mock_enqueue, mock_background_tasks):
        """Test individual company ingestion."""
        from app.api.v1.routes import ingest_company
        
        result = ingest_company("MSFT", mock_background_tasks)
        
        assert result.status == "queued"
        assert "MSFT" in result.detail


class TestMetricsEndpoints:
    """Test metrics and timeseries endpoints."""

    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.latest_owner_earnings_growth")
    @patch("app.api.v1.routes.latest_debt_to_equity")
    @patch("app.api.v1.routes.roic_average")
    @patch("app.api.v1.routes.compute_growth_metrics")
    def test_get_metrics_success(self, mock_growth, mock_roic, mock_debt, mock_fcf, mock_cik):
        """Test successful metrics retrieval."""
        mock_cik.return_value = "0000789019"
        mock_growth.return_value = {"eps_cagr_5y": 0.15, "rev_cagr_5y": 0.12}
        mock_roic.return_value = 0.25
        mock_debt.return_value = 0.5
        mock_fcf.return_value = 0.18
        
        from app.api.v1.routes import get_metrics
        result = get_metrics("MSFT")
        
        assert result["cik"] == "0000789019"
        assert result["growths"]["eps_cagr_5y"] == 0.15
        assert result["roic_avg_10y"] == 0.25

    @patch("app.api.v1.routes.get_company_cik")
    def test_get_metrics_not_found(self, mock_cik):
        """Test 404 when company not found."""
        mock_cik.side_effect = HTTPException(404, detail="Company not found. Ingest first.")
        
        from app.api.v1.routes import get_metrics
        with pytest.raises(HTTPException) as exc:
            get_metrics("INVALID")
        assert exc.value.status_code == 404

    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.timeseries_all")
    def test_get_timeseries_success(self, mock_timeseries, mock_cik):
        """Test successful timeseries retrieval."""
        mock_cik.return_value = "0000789019"
        mock_timeseries.return_value = {"revenue": [{"fy": 2023, "value": 211915}]}
        
        from app.api.v1.routes import get_timeseries
        result = get_timeseries("MSFT")
        
        assert "revenue" in result

    @patch("app.api.v1.routes.get_company_cik")
    def test_get_timeseries_not_found(self, mock_cik):
        """Test 404 when company not found."""
        mock_cik.side_effect = HTTPException(404, detail="Company not found. Ingest first.")
        
        from app.api.v1.routes import get_timeseries
        with pytest.raises(HTTPException) as exc:
            get_timeseries("INVALID")
        assert exc.value.status_code == 404


class TestValuationEndpoints:
    """Test valuation endpoints."""

    @patch("app.api.v1.routes.run_default_scenario")
    def test_run_valuation_success(self, mock_scenario):
        """Test successful valuation."""
        mock_scenario.return_value = {
            "inputs": {"eps0": 10.0, "g": 0.15},
            "results": {"sticker": 100.0, "mos_price": 50.0}
        }
        
        from app.api.v1.routes import run_valuation, ValuationRequest
        body = ValuationRequest(mos_pct=0.5)
        result = run_valuation("MSFT", body)
        
        assert result["results"]["sticker"] == 100.0

    @patch("app.api.v1.routes.run_default_scenario")
    def test_run_valuation_not_found(self, mock_scenario):
        """Test 404 when valuation fails."""
        mock_scenario.side_effect = ValueError("Unknown ticker")
        
        from app.api.v1.routes import run_valuation, ValuationRequest
        body = ValuationRequest()
        with pytest.raises(HTTPException) as exc:
            run_valuation("INVALID", body)
        assert exc.value.status_code == 404

    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.compute_growth_metrics")
    def test_export_metrics_csv(self, mock_growth, mock_cik):
        """Test CSV export of metrics."""
        mock_cik.return_value = "0000789019"
        mock_growth.return_value = {"eps_cagr_5y": 0.15, "rev_cagr_5y": 0.12}
        
        from app.api.v1.routes import export_metrics_csv
        result = export_metrics_csv("MSFT")
        
        assert "metric,value" in result
        assert "eps_cagr_5y" in result

    @patch("app.api.v1.routes.run_default_scenario")
    def test_export_valuation_json(self, mock_scenario):
        """Test JSON export of valuation."""
        mock_scenario.return_value = {"inputs": {}, "results": {}}
        
        from app.api.v1.routes import export_valuation_json
        result = export_valuation_json("MSFT")
        
        assert "inputs" in result


class TestAlertEndpoints:
    """Test alert management endpoints."""

    def test_create_alert_success(self, mock_execute):
        """Test successful alert creation."""
        mock_execute.return_value.first.return_value = (1,)
        
        from app.api.v1.routes import create_alert, AlertCreate
        body = AlertCreate(rule_type="mos_breach", threshold=50.0)
        result = create_alert("MSFT", body)
        
        assert result["status"] == "ok"

    def test_create_alert_company_not_found(self, mock_execute):
        """Test 404 when company not found."""
        mock_execute.return_value.first.return_value = None
        
        from app.api.v1.routes import create_alert, AlertCreate
        body = AlertCreate(rule_type="mos_breach")
        with pytest.raises(HTTPException) as exc:
            create_alert("INVALID", body)
        assert exc.value.status_code == 404

    def test_list_alerts(self, mock_execute):
        """Test listing alerts for a company."""
        mock_execute.return_value.fetchall.return_value = [
            (1, "mos_breach", 50.0, True),
            (2, "price_drop", None, False),
        ]
        
        from app.api.v1.routes import list_alerts
        result = list_alerts("MSFT")
        
        assert len(result) == 2
        assert result[0]["rule_type"] == "mos_breach"

    def test_delete_alert(self, mock_execute):
        """Test alert deletion."""
        from app.api.v1.routes import delete_alert
        result = delete_alert(1)
        
        assert result["status"] == "deleted"
        assert result["id"] == 1

    def test_toggle_alert(self, mock_execute):
        """Test toggling alert enabled status."""
        from app.api.v1.routes import toggle_alert, AlertToggle
        body = AlertToggle(enabled=False)
        result = toggle_alert(1, body)
        
        assert result["status"] == "ok"
        assert result["enabled"] is False


class TestFourMsEndpoints:
    """Test Four Ms analysis endpoints."""

    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.compute_margin_of_safety_recommendation")
    @patch("app.api.v1.routes.compute_management")
    @patch("app.api.v1.routes.compute_moat")
    def test_get_fourm_analysis_success(self, mock_moat, mock_mgmt, mock_mos, mock_cik):
        """Test successful Four Ms analysis."""
        mock_cik.return_value = "0000789019"
        mock_moat.return_value = {"roic_avg": 0.25, "score": 8}
        mock_mgmt.return_value = {"reinvestment_rate": 0.7, "score": 7}
        mock_mos.return_value = {"recommended_mos": 0.5}
        
        from app.api.v1.routes import get_fourm_analysis
        result = get_fourm_analysis("MSFT")
        
        assert result["moat"]["score"] == 8
        assert result["management"]["score"] == 7

    @patch("app.api.v1.routes.get_company_cik")
    def test_get_fourm_analysis_not_found(self, mock_cik):
        """Test 404 when company not found."""
        mock_cik.side_effect = HTTPException(404, detail="Company not found. Ingest first.")
        
        from app.api.v1.routes import get_fourm_analysis
        with pytest.raises(HTTPException) as exc:
            get_fourm_analysis("INVALID")
        assert exc.value.status_code == 404

    @patch("app.api.v1.routes.execute")
    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.get_meaning_item1")
    def test_refresh_meaning_success(self, mock_meaning, mock_cik, mock_execute):
        """Test successful meaning refresh."""
        mock_cik.return_value = "0000789019"
        mock_execute.return_value.first.return_value = None  # No recent note
        mock_meaning.return_value = {
            "status": "ok",
            "accession": "0001564590-23-012345",
            "doc": "msft-20230630.htm",
            "item1_excerpt": "Microsoft develops software..."
        }
        
        from app.api.v1.routes import refresh_meaning_analysis
        result = refresh_meaning_analysis("MSFT")
        
        assert result["status"] == "ok"

    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.get_meaning_item1")
    def test_refresh_meaning_not_found_filing(self, mock_meaning, mock_cik):
        """Test 404 when no 10-K filing found."""
        mock_cik.return_value = "0000789019"
        mock_meaning.return_value = {"status": "not_found"}
        
        from app.api.v1.routes import refresh_meaning_analysis
        with pytest.raises(HTTPException) as exc:
            refresh_meaning_analysis("MSFT")
        assert exc.value.status_code == 404

    @patch("app.api.v1.routes.execute")
    @patch("app.api.v1.routes.get_company_cik")
    @patch("app.api.v1.routes.get_meaning_item1")
    def test_refresh_meaning_skips_recent_note(self, mock_meaning, mock_cik, mock_execute):
        """Test that refresh skips if recent note exists."""
        mock_cik.return_value = "0000789019"
        mock_execute.return_value.first.return_value = ("existing_id",)  # Recent note exists
        mock_meaning.return_value = {
            "status": "ok",
            "accession": "0001564590-23-012345",
            "doc": "msft-20230630.htm",
            "item1_excerpt": "Microsoft develops software..."
        }
        
        from app.api.v1.routes import refresh_meaning_analysis
        result = refresh_meaning_analysis("MSFT")
        
        # Should still return data but not insert duplicate
        assert result["status"] == "ok"


class TestDebugEndpoints:
    """Test debug endpoints."""

    def test_debug_modules(self):
        """Test debug modules endpoint."""
        from app.api.v1.routes import debug_modules
        result = debug_modules()
        
        assert isinstance(result, dict)
        assert "app.metrics.compute" in result
