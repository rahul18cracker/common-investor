"""Tests for Phase 1B: Industry classification via SIC codes.

Covers:
- sic_to_category() mapping for all SIC ranges
- sic_to_metric_notes() for banks, REITs, utilities, etc.
- Ingestion populates SIC fields on Company
- Agent-bundle includes industry fields
"""

import pytest


# =============================================================================
# Unit Tests: SIC Mapping
# =============================================================================


class TestSicToCategory:
    """Test sic_to_category() covers all SIC ranges correctly."""

    def test_technology_software(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("7372") == "technology"
        assert sic_to_category("7374") == "technology"

    def test_technology_hardware(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("3571") == "technology"
        assert sic_to_category("3672") == "technology"

    def test_banking(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("6021") == "banking"
        assert sic_to_category("6022") == "banking"
        assert sic_to_category("6199") == "banking"

    def test_reits(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("6500") == "reits"
        assert sic_to_category("6512") == "reits"
        assert sic_to_category("6599") == "reits"
        # REIT trust code (Realty Income SIC=6798)
        assert sic_to_category("6798") == "reits"

    def test_utilities(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("4911") == "utilities"
        assert sic_to_category("4991") == "utilities"

    def test_energy(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("1311") == "energy"
        assert sic_to_category("1389") == "energy"
        # Petroleum refining (XOM SIC=2911)
        assert sic_to_category("2911") == "energy"
        assert sic_to_category("2900") == "energy"

    def test_pharma(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("2830") == "pharma"
        assert sic_to_category("2836") == "pharma"

    def test_defense(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("3760") == "defense"
        assert sic_to_category("3769") == "defense"

    def test_securities_investments(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("6200") == "securities_investments"
        assert sic_to_category("6399") == "securities_investments"

    def test_broad_manufacturing(self):
        from app.core.industry import sic_to_category
        # SIC in manufacturing range but not matching specific sub-ranges
        assert sic_to_category("2000") == "manufacturing"
        assert sic_to_category("3100") == "manufacturing"

    def test_broad_retail(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("5200") == "retail"
        assert sic_to_category("5961") == "retail"

    def test_broad_services(self):
        from app.core.industry import sic_to_category
        # SIC in services range but not matching technology sub-range
        assert sic_to_category("7011") == "services"
        assert sic_to_category("8000") == "services"

    def test_broad_financials_fallback(self):
        from app.core.industry import sic_to_category
        # SIC in financials range but not matching banking/securities/reits
        assert sic_to_category("6411") == "financials"
        assert sic_to_category("6900") == "financials"

    def test_agriculture(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("100") == "agriculture"
        assert sic_to_category("999") == "agriculture"

    def test_mining(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("1000") == "mining"
        assert sic_to_category("1200") == "mining"

    def test_construction(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("1500") == "construction"

    def test_wholesale(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("5000") == "wholesale"
        assert sic_to_category("5199") == "wholesale"

    def test_transportation_utilities_broad(self):
        from app.core.industry import sic_to_category
        # SIC 4000-4999 but not matching specific utilities sub-range
        assert sic_to_category("4000") == "transportation_utilities"
        assert sic_to_category("4500") == "transportation_utilities"

    def test_unknown_for_invalid_input(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("") == "unknown"
        assert sic_to_category(None) == "unknown"
        assert sic_to_category("abc") == "unknown"
        assert sic_to_category("99999") == "unknown"

    def test_specific_range_wins_over_broad(self):
        from app.core.industry import sic_to_category
        # SIC 7372 is in both services (7000-8999) and technology (7372-7374)
        # Specific should win
        assert sic_to_category("7372") == "technology"
        # SIC 6021 is in both financials (6000-6999) and banking (6000-6199)
        assert sic_to_category("6021") == "banking"


class TestRealWorldSicCodes:
    """Verify SIC codes from actual SEC submissions for our stress test cohort."""

    def test_msft(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("7372") == "technology"

    def test_jpm(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("6021") == "banking"

    def test_realty_income(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("6798") == "reits"

    def test_nextera_energy(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("4911") == "utilities"

    def test_starbucks(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("5810") == "retail"

    def test_exxon(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("2911") == "energy"

    def test_salesforce(self):
        from app.core.industry import sic_to_category
        assert sic_to_category("7372") == "technology"


class TestSicToMetricNotes:
    """Test sic_to_metric_notes() returns appropriate guidance."""

    def test_banking_notes(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("6021")
        assert len(notes) > 0
        assert any("ROIC" in n for n in notes)
        assert any("ROE" in n or "interest" in n.lower() for n in notes)

    def test_reits_notes(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("6512")
        assert len(notes) > 0
        assert any("FFO" in n for n in notes)

    def test_utilities_notes(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("4911")
        assert len(notes) > 0
        assert any("ROIC" in n or "regulated" in n.lower() for n in notes)

    def test_energy_notes(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("1311")
        assert len(notes) > 0
        assert any("cyclical" in n.lower() or "commodity" in n.lower() for n in notes)

    def test_technology_notes(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("7372")
        assert len(notes) > 0
        assert any("SBC" in n or "R&D" in n for n in notes)

    def test_no_notes_for_unknown(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes("99999")
        assert notes == []

    def test_no_notes_for_none(self):
        from app.core.industry import sic_to_metric_notes
        notes = sic_to_metric_notes(None)
        assert notes == []

    def test_returns_new_list(self):
        """Ensure returned list is a copy, not the internal reference."""
        from app.core.industry import sic_to_metric_notes
        notes1 = sic_to_metric_notes("6021")
        notes2 = sic_to_metric_notes("6021")
        assert notes1 == notes2
        assert notes1 is not notes2


# =============================================================================
# Unit Tests: Fiscal Year End Parsing
# =============================================================================


class TestFiscalYearEndParsing:
    """Test _parse_fiscal_year_end_month()."""

    def test_june(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("0630") == 6

    def test_december(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("1231") == 12

    def test_september(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("0930") == 9

    def test_january(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("0131") == 1

    def test_none_input(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month(None) is None

    def test_empty_string(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("") is None

    def test_short_string(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("0") is None

    def test_non_numeric(self):
        from app.ingest.sec import _parse_fiscal_year_end_month
        assert _parse_fiscal_year_end_month("abcd") is None


# =============================================================================
# Integration Tests: Ingestion with SIC Fields
# =============================================================================


@pytest.mark.integration
class TestIngestionWithSIC:
    """Test that ingestion populates SIC fields on Company."""

    def test_ingest_populates_sic_fields(
        self, db_session, mock_httpx_client
    ):
        """After ingestion, Company should have sic_code, sector, industry."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker

        ingest_companyfacts_richer_by_ticker("MSFT")

        from app.db.models import Company
        company = db_session.query(Company).filter_by(ticker="MSFT").first()
        assert company is not None
        assert company.sic_code == "7372"
        assert company.sector == "technology"
        assert company.industry == "SERVICES-PREPACKAGED SOFTWARE"
        assert company.fiscal_year_end_month == 6

    def test_ingest_handles_missing_submissions(
        self, db_session, httpx_mock
    ):
        """If submissions endpoint fails, ingestion should still work."""
        # Mock ticker map and company facts but NOT submissions
        httpx_mock.add_response(
            url="https://www.sec.gov/files/company_tickers.json",
            json={"0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORPORATION"}}
        )
        httpx_mock.add_response(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
            json={"cik": 789019, "entityName": "MICROSOFT CORPORATION", "facts": {}}
        )
        # Return 500 for submissions to simulate failure
        httpx_mock.add_response(
            url="https://data.sec.gov/submissions/CIK0000789019.json",
            status_code=500,
        )

        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        # Should not raise — gracefully handles failure
        result = ingest_companyfacts_richer_by_ticker("MSFT")
        assert result["ticker"] == "MSFT"

        from app.db.models import Company
        company = db_session.query(Company).filter_by(ticker="MSFT").first()
        assert company is not None
        # SIC fields should be None since submissions failed
        assert company.sic_code is None
        assert company.sector is None


# =============================================================================
# Integration Tests: Agent-Bundle with Industry
# =============================================================================


@pytest.mark.integration
class TestAgentBundleIndustry:
    """Test agent-bundle endpoint includes industry fields."""

    def test_agent_bundle_includes_industry(
        self, client, db_session, mock_httpx_client
    ):
        """Agent-bundle should include SIC code, category, and notes."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        ingest_companyfacts_richer_by_ticker("MSFT")

        resp = client.get("/api/v1/company/MSFT/agent-bundle")
        assert resp.status_code == 200
        data = resp.json()

        company = data["company"]
        assert company["sic_code"] == "7372"
        assert company["sic_description"] == "SERVICES-PREPACKAGED SOFTWARE"
        assert company["industry_category"] == "technology"
        assert isinstance(company["industry_notes"], list)
        assert len(company["industry_notes"]) > 0
        assert company["fiscal_year_end_month"] == 6

    def test_agent_bundle_includes_new_metrics(
        self, client, db_session, mock_httpx_client
    ):
        """Agent-bundle should include 1C metrics (operating margin, FCF margin, etc.)."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        ingest_companyfacts_richer_by_ticker("MSFT")

        resp = client.get("/api/v1/company/MSFT/agent-bundle")
        assert resp.status_code == 200
        data = resp.json()

        metrics = data["metrics"]
        assert "latest_operating_margin" in metrics
        assert "latest_fcf_margin" in metrics
        assert "latest_cash_conversion" in metrics
        assert "roe_avg" in metrics

        # With mock data, these should be computable
        assert metrics["latest_operating_margin"] is not None
        assert metrics["latest_fcf_margin"] is not None
