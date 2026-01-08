"""
Comprehensive unit tests for app/api/v1/routes.py

Tests cover all API endpoints with mocked dependencies:
- Company list and seed endpoints
- Company summary and ingest
- Metrics and timeseries
- Valuation
- Alerts CRUD
- Four Ms analysis
- Export endpoints
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.routes import (
    list_companies,
    seed_database,
    seed_status,
    ingest_company,
    company_summary,
    get_metrics,
    get_timeseries,
    run_valuation,
    export_metrics_csv,
    export_valuation_json,
    create_alert,
    list_alerts,
    delete_alert,
    toggle_alert,
    get_fourm_analysis,
    refresh_meaning_analysis,
    debug_modules,
    SeedRequest,
    ValuationRequest,
    AlertCreate,
    AlertToggle,
)


class TestListCompanies:
    """Tests for list_companies endpoint."""

    def test_list_companies_returns_all(self):
        """Test listing all companies."""
        mock_rows = [
            (1, "0000320193", "AAPL", "Apple Inc.", 10),
            (2, "0000789019", "MSFT", "Microsoft Corporation", 8),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            result = list_companies()

            assert result["count"] == 2
            assert len(result["companies"]) == 2
            assert result["companies"][0]["ticker"] == "AAPL"
            assert result["companies"][1]["ticker"] == "MSFT"

    def test_list_companies_empty(self):
        """Test listing when no companies exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            result = list_companies()

            assert result["count"] == 0
            assert result["companies"] == []

    def test_list_companies_handles_none_years(self):
        """Test handling of None years_data."""
        mock_rows = [(1, "0000320193", "AAPL", "Apple Inc.", None)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            result = list_companies()

            assert result["companies"][0]["years_data"] == 0


class TestSeedDatabase:
    """Tests for seed_database endpoint."""

    def test_seed_with_default_tickers(self):
        """Test seeding with default tickers."""
        background_tasks = MagicMock()
        body = SeedRequest(tickers=None)

        with patch("app.api.v1.routes.enqueue_ingest") as mock_enqueue:
            with patch("app.cli.seed.DEFAULT_TICKERS", ["AAPL", "MSFT"]):
                result = seed_database(body, background_tasks)

                assert result["status"] == "queued"
                assert len(result["tickers"]) == 2
                assert background_tasks.add_task.call_count == 2

    def test_seed_with_custom_tickers(self):
        """Test seeding with custom tickers."""
        background_tasks = MagicMock()
        body = SeedRequest(tickers=["GOOGL", "META"])

        result = seed_database(body, background_tasks)

        assert result["status"] == "queued"
        assert result["tickers"] == ["GOOGL", "META"]
        assert background_tasks.add_task.call_count == 2

    def test_seed_uppercases_tickers(self):
        """Test that tickers are uppercased."""
        background_tasks = MagicMock()
        body = SeedRequest(tickers=["aapl", "msft"])

        result = seed_database(body, background_tasks)

        assert result["tickers"] == ["AAPL", "MSFT"]


class TestSeedStatus:
    """Tests for seed_status endpoint."""

    def test_seed_status_with_companies(self):
        """Test status when companies exist."""
        mock_result = MagicMock()
        mock_result.first.return_value = [5]

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            with patch("app.cli.seed.DEFAULT_TICKERS", ["AAPL", "MSFT", "GOOGL"]):
                result = seed_status()

                assert result["companies_loaded"] == 5
                assert result["is_seeded"] is True
                assert result["default_ticker_count"] == 3

    def test_seed_status_empty(self):
        """Test status when no companies exist."""
        mock_result = MagicMock()
        mock_result.first.return_value = [0]

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            with patch("app.cli.seed.DEFAULT_TICKERS", ["AAPL"]):
                result = seed_status()

                assert result["companies_loaded"] == 0
                assert result["is_seeded"] is False


class TestIngestCompany:
    """Tests for ingest_company endpoint."""

    def test_ingest_company_queues_task(self):
        """Test that ingest queues a background task."""
        background_tasks = MagicMock()

        result = ingest_company("AAPL", background_tasks)

        assert result.status == "queued"
        assert "AAPL" in result.detail
        background_tasks.add_task.assert_called_once()


class TestCompanySummary:
    """Tests for company_summary endpoint."""

    def test_company_summary_success(self):
        """Test successful company summary retrieval."""
        mock_company_row = (1, "0000320193", "AAPL", "Apple Inc.")
        # Updated to match new API response: (fy, revenue, cogs, gross_profit, sga, rnd, 
        #   depreciation, ebit, interest_expense, taxes, net_income, eps_diluted, shares_diluted)
        mock_latest_row = (
            2023,           # fy
            394328000000,   # revenue
            214137000000,   # cogs
            180191000000,   # gross_profit
            24932000000,    # sga
            29915000000,    # rnd
            11519000000,    # depreciation
            114301000000,   # ebit
            3933000000,     # interest_expense
            16741000000,    # taxes
            96995000000,    # net_income
            6.16,           # eps_diluted
            15744000000,    # shares_diluted
        )

        mock_company_result = MagicMock()
        mock_company_result.first.return_value = mock_company_row

        mock_latest_result = MagicMock()
        mock_latest_result.first.return_value = mock_latest_row

        with patch("app.api.v1.routes.execute") as mock_execute:
            mock_execute.side_effect = [mock_company_result, mock_latest_result]

            result = company_summary("AAPL")

            assert result["company"]["ticker"] == "AAPL"
            assert result["latest_is"]["fy"] == 2023
            assert result["latest_is"]["revenue"] == 394328000000
            assert result["latest_is"]["cogs"] == 214137000000
            assert result["latest_is"]["gross_profit"] == 180191000000
            assert result["latest_is"]["gross_margin"] is not None
            assert result["latest_is"]["operating_margin"] is not None

    def test_company_summary_not_found(self):
        """Test company not found raises 404."""
        mock_result = MagicMock()
        mock_result.first.return_value = None

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            with pytest.raises(HTTPException) as exc_info:
                company_summary("INVALID")

            assert exc_info.value.status_code == 404

    def test_company_summary_no_latest_data(self):
        """Test company with no financial data."""
        mock_company_row = (1, "0000320193", "AAPL", "Apple Inc.")

        mock_company_result = MagicMock()
        mock_company_result.first.return_value = mock_company_row

        mock_latest_result = MagicMock()
        mock_latest_result.first.return_value = None

        with patch("app.api.v1.routes.execute") as mock_execute:
            mock_execute.side_effect = [mock_company_result, mock_latest_result]

            result = company_summary("AAPL")

            assert result["company"]["ticker"] == "AAPL"
            assert result["latest_is"] is None


class TestGetMetrics:
    """Tests for get_metrics endpoint."""

    def test_get_metrics_success(self):
        """Test successful metrics retrieval."""
        mock_growths = {"revenue_cagr_5y": 0.15, "eps_cagr_5y": 0.20}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.compute_growth_metrics", return_value=mock_growths):
                with patch("app.api.v1.routes.roic_average", return_value=0.25):
                    with patch("app.api.v1.routes.latest_debt_to_equity", return_value=1.5):
                        with patch("app.api.v1.routes.latest_owner_earnings_growth", return_value=0.10):
                            result = get_metrics("AAPL")

                            assert result["cik"] == "0000320193"
                            assert result["growths"] == mock_growths
                            assert result["roic_avg_10y"] == 0.25


class TestGetTimeseries:
    """Tests for get_timeseries endpoint."""

    def test_get_timeseries_success(self):
        """Test successful timeseries retrieval."""
        mock_timeseries = {"years": [2020, 2021, 2022], "revenue": [100, 110, 120]}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.timeseries_all", return_value=mock_timeseries):
                result = get_timeseries("AAPL")

                assert result == mock_timeseries


class TestRunValuation:
    """Tests for run_valuation endpoint."""

    def test_run_valuation_success(self):
        """Test successful valuation."""
        mock_valuation = {"sticker_price": 150.0, "mos_price": 75.0}
        body = ValuationRequest(mos_pct=0.5)

        with patch("app.api.v1.routes.run_default_scenario", return_value=mock_valuation):
            result = run_valuation("AAPL", body)

            assert result == mock_valuation

    def test_run_valuation_with_overrides(self):
        """Test valuation with custom parameters."""
        mock_valuation = {"sticker_price": 200.0}
        body = ValuationRequest(mos_pct=0.4, g=0.12, pe_cap=25, discount=0.12)

        with patch("app.api.v1.routes.run_default_scenario", return_value=mock_valuation) as mock_run:
            result = run_valuation("AAPL", body)

            mock_run.assert_called_once_with(
                "AAPL",
                mos_pct=0.4,
                g_override=0.12,
                pe_cap=25,
                discount=0.12,
            )

    def test_run_valuation_not_found(self):
        """Test valuation raises 404 on ValueError."""
        body = ValuationRequest()

        with patch("app.api.v1.routes.run_default_scenario", side_effect=ValueError("Company not found")):
            with pytest.raises(HTTPException) as exc_info:
                run_valuation("INVALID", body)

            assert exc_info.value.status_code == 404


class TestExportMetricsCsv:
    """Tests for export_metrics_csv endpoint."""

    def test_export_metrics_csv_success(self):
        """Test CSV export."""
        mock_metrics = {"revenue_cagr_5y": 0.15, "eps_cagr_5y": 0.20}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.compute_growth_metrics", return_value=mock_metrics):
                result = export_metrics_csv("AAPL")

                assert "metric,value" in result
                assert "revenue_cagr_5y,0.15" in result

    def test_export_metrics_csv_handles_none(self):
        """Test CSV export with None values."""
        mock_metrics = {"revenue_cagr_5y": None, "eps_cagr_5y": 0.20}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.compute_growth_metrics", return_value=mock_metrics):
                result = export_metrics_csv("AAPL")

                assert "revenue_cagr_5y," in result  # Empty value for None


class TestExportValuationJson:
    """Tests for export_valuation_json endpoint."""

    def test_export_valuation_json_success(self):
        """Test JSON export."""
        mock_valuation = {"sticker_price": 150.0}

        with patch("app.api.v1.routes.run_default_scenario", return_value=mock_valuation):
            result = export_valuation_json("AAPL")

            assert result == mock_valuation

    def test_export_valuation_json_custom_mos(self):
        """Test JSON export with custom MOS."""
        mock_valuation = {"sticker_price": 150.0}

        with patch("app.api.v1.routes.run_default_scenario", return_value=mock_valuation) as mock_run:
            export_valuation_json("AAPL", mos_pct=0.4)

            mock_run.assert_called_once_with("AAPL", mos_pct=0.4)


class TestCreateAlert:
    """Tests for create_alert endpoint."""

    def test_create_alert_success(self):
        """Test successful alert creation."""
        mock_company_result = MagicMock()
        mock_company_result.first.return_value = [1]

        body = AlertCreate(rule_type="price_below", threshold=100.0)

        with patch("app.api.v1.routes.execute") as mock_execute:
            mock_execute.return_value = mock_company_result

            result = create_alert("AAPL", body)

            assert result["status"] == "ok"
            assert mock_execute.call_count == 2  # SELECT and INSERT

    def test_create_alert_company_not_found(self):
        """Test alert creation for non-existent company."""
        mock_result = MagicMock()
        mock_result.first.return_value = None

        body = AlertCreate(rule_type="price_below", threshold=100.0)

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            with pytest.raises(HTTPException) as exc_info:
                create_alert("INVALID", body)

            assert exc_info.value.status_code == 404


class TestListAlerts:
    """Tests for list_alerts endpoint."""

    def test_list_alerts_success(self):
        """Test listing alerts."""
        mock_rows = [
            (1, "price_below", 100.0, True),
            (2, "price_above", 200.0, False),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            result = list_alerts("AAPL")

            assert len(result) == 2
            assert result[0]["rule_type"] == "price_below"
            assert result[1]["enabled"] is False

    def test_list_alerts_empty(self):
        """Test listing when no alerts exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with patch("app.api.v1.routes.execute", return_value=mock_result):
            result = list_alerts("AAPL")

            assert result == []


class TestDeleteAlert:
    """Tests for delete_alert endpoint."""

    def test_delete_alert_success(self):
        """Test successful alert deletion."""
        with patch("app.api.v1.routes.execute"):
            result = delete_alert(1)

            assert result["status"] == "deleted"
            assert result["id"] == 1


class TestToggleAlert:
    """Tests for toggle_alert endpoint."""

    def test_toggle_alert_enable(self):
        """Test enabling an alert."""
        body = AlertToggle(enabled=True)

        with patch("app.api.v1.routes.execute"):
            result = toggle_alert(1, body)

            assert result["status"] == "ok"
            assert result["enabled"] is True

    def test_toggle_alert_disable(self):
        """Test disabling an alert."""
        body = AlertToggle(enabled=False)

        with patch("app.api.v1.routes.execute"):
            result = toggle_alert(1, body)

            assert result["enabled"] is False


class TestGetFourmAnalysis:
    """Tests for get_fourm_analysis endpoint."""

    def test_get_fourm_analysis_success(self):
        """Test successful Four Ms analysis."""
        mock_moat = {"score": 85, "rating": "Excellent"}
        mock_management = {"score": 75, "rating": "Good"}
        mock_mos = {"recommended_mos": 0.5}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.compute_moat", return_value=mock_moat):
                with patch("app.api.v1.routes.compute_management", return_value=mock_management):
                    with patch("app.api.v1.routes.compute_margin_of_safety_recommendation", return_value=mock_mos):
                        result = get_fourm_analysis("AAPL")

                        assert result["cik"] == "0000320193"
                        assert result["moat"] == mock_moat
                        assert result["management"] == mock_management
                        assert result["mos_recommendation"] == mock_mos


class TestRefreshMeaningAnalysis:
    """Tests for refresh_meaning_analysis endpoint."""

    def test_refresh_meaning_success(self):
        """Test successful meaning refresh."""
        mock_meaning = {
            "status": "ok",
            "item1_excerpt": "Apple designs and manufactures...",
            "accession": "0000320193-23-000077",
            "doc": "aapl-20230930.htm",
        }

        mock_existing_result = MagicMock()
        mock_existing_result.first.return_value = None

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.get_meaning_item1", return_value=mock_meaning):
                with patch("app.api.v1.routes.execute", return_value=mock_existing_result):
                    result = refresh_meaning_analysis("AAPL")

                    assert result["status"] == "ok"

    def test_refresh_meaning_not_found(self):
        """Test meaning refresh when no 10-K found."""
        mock_meaning = {"status": "not_found"}

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.get_meaning_item1", return_value=mock_meaning):
                with pytest.raises(HTTPException) as exc_info:
                    refresh_meaning_analysis("AAPL")

                assert exc_info.value.status_code == 404

    def test_refresh_meaning_skips_recent(self):
        """Test that recent meaning notes are not duplicated."""
        mock_meaning = {
            "status": "ok",
            "item1_excerpt": "Apple designs...",
            "accession": "0000320193-23-000077",
            "doc": "aapl-20230930.htm",
        }

        mock_existing_result = MagicMock()
        mock_existing_result.first.return_value = [1]  # Existing recent note

        with patch("app.api.v1.routes.get_company_cik", return_value="0000320193"):
            with patch("app.api.v1.routes.get_meaning_item1", return_value=mock_meaning):
                with patch("app.api.v1.routes.execute", return_value=mock_existing_result) as mock_execute:
                    result = refresh_meaning_analysis("AAPL")

                    # Should only call execute once (for checking existing)
                    # Not twice (no INSERT since recent exists)
                    assert mock_execute.call_count == 1


class TestDebugModules:
    """Tests for debug_modules endpoint."""

    def test_debug_modules_returns_paths(self):
        """Test debug endpoint returns module paths."""
        result = debug_modules()

        assert "app.metrics.compute" in result
        assert "app.valuation.service" in result
        assert "app.valuation.core" in result
        assert "app.nlp.fourm.service" in result
        assert "app.nlp.fourm.sec_item1" in result
