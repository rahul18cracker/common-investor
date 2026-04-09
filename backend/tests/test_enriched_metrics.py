"""Tests for Phase 1C: Enriched quantitative metrics.

Covers:
- operating_margin_series() — happy path, zero revenue, missing ebit
- fcf_margin_series() — happy path, zero revenue, missing CF data
- cash_conversion_series() — happy path, zero net income, >1.0 quality
- roe_series() — happy path, negative equity guard, single year
- Timeseries endpoint includes new series
- Integration: MSFT mock data produces expected ranges
"""

import pytest
from datetime import date

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers: Create test financial data
# =============================================================================


def _seed_company_with_data(db_session, cik="0000789019", ticker="MSFT",
                            years=None, negative_equity=False):
    """Seed a company with IS, BS, CF data for testing metrics.

    Returns the CIK string.
    """
    from app.db.models import Company, Filing, StatementIS, StatementBS, StatementCF

    company = Company(cik=cik, ticker=ticker, name=f"Test {ticker}")
    db_session.add(company)
    db_session.commit()

    if years is None:
        years = [
            {
                "fy": 2021, "revenue": 168088e6, "ebit": 69916e6,
                "net_income": 61271e6, "cfo": 76740e6, "capex": 20622e6,
                "equity": 141988e6, "debt": 50074e6, "cash": 14224e6,
            },
            {
                "fy": 2022, "revenue": 198270e6, "ebit": 83383e6,
                "net_income": 72738e6, "cfo": 89035e6, "capex": 23886e6,
                "equity": 166542e6, "debt": 47032e6, "cash": 13931e6,
            },
            {
                "fy": 2023, "revenue": 211915e6, "ebit": 88523e6,
                "net_income": 72361e6, "cfo": 87582e6, "capex": 28107e6,
                "equity": 206223e6, "debt": 41990e6, "cash": 34704e6,
            },
        ]

    for yr in years:
        filing = Filing(
            cik=cik, form="10-K",
            accession=f"TEST-{cik}-{yr['fy']}",
            period_end=date(yr["fy"], 6, 30),
        )
        db_session.add(filing)
        db_session.commit()
        db_session.refresh(filing)

        is_rec = StatementIS(
            filing_id=filing.id, fy=yr["fy"],
            revenue=yr.get("revenue"),
            ebit=yr.get("ebit"),
            net_income=yr.get("net_income"),
        )
        eq = yr.get("equity")
        if negative_equity and eq is not None:
            eq = -abs(eq)
        bs_rec = StatementBS(
            filing_id=filing.id, fy=yr["fy"],
            shareholder_equity=eq,
            total_debt=yr.get("debt"),
            cash=yr.get("cash"),
        )
        cf_rec = StatementCF(
            filing_id=filing.id, fy=yr["fy"],
            cfo=yr.get("cfo"),
            capex=yr.get("capex"),
        )
        db_session.add_all([is_rec, bs_rec, cf_rec])
        db_session.commit()

    return cik


# =============================================================================
# Unit Tests: operating_margin_series
# =============================================================================


class TestOperatingMarginSeries:

    def test_happy_path(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import operating_margin_series
        series = operating_margin_series(cik)

        assert len(series) == 3
        # MSFT FY2023: EBIT 88523M / Revenue 211915M ~ 0.4178
        assert series[-1]["fy"] == 2023
        assert series[-1]["operating_margin"] is not None
        assert 0.40 < series[-1]["operating_margin"] < 0.43

    def test_zero_revenue(self, db_session):
        """Zero revenue should produce None margin."""
        cik = _seed_company_with_data(db_session, cik="0000000001", ticker="ZERO", years=[
            {"fy": 2023, "revenue": 0, "ebit": 100e6, "net_income": 50e6,
             "cfo": 60e6, "capex": 10e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import operating_margin_series
        series = operating_margin_series(cik)
        assert len(series) == 1
        assert series[0]["operating_margin"] is None

    def test_missing_ebit(self, db_session):
        """Missing EBIT should produce None margin."""
        cik = _seed_company_with_data(db_session, cik="0000000002", ticker="NOEBIT", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": None, "net_income": 50e6,
             "cfo": 60e6, "capex": 10e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import operating_margin_series
        series = operating_margin_series(cik)
        assert len(series) == 1
        assert series[0]["operating_margin"] is None

    def test_empty_data(self, db_session):
        from app.metrics.compute import operating_margin_series
        series = operating_margin_series("0000000099")
        assert series == []


# =============================================================================
# Unit Tests: fcf_margin_series
# =============================================================================


class TestFcfMarginSeries:

    def test_happy_path(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import fcf_margin_series
        series = fcf_margin_series(cik)

        assert len(series) == 3
        # MSFT FY2023: (87582M - 28107M) / 211915M ~ 0.2807
        assert series[-1]["fy"] == 2023
        assert series[-1]["fcf_margin"] is not None
        assert 0.27 < series[-1]["fcf_margin"] < 0.30

    def test_zero_revenue(self, db_session):
        cik = _seed_company_with_data(db_session, cik="0000000003", ticker="ZREV", years=[
            {"fy": 2023, "revenue": 0, "ebit": 0, "net_income": 0,
             "cfo": 60e6, "capex": 10e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import fcf_margin_series
        series = fcf_margin_series(cik)
        assert len(series) == 1
        assert series[0]["fcf_margin"] is None

    def test_missing_cfo(self, db_session):
        cik = _seed_company_with_data(db_session, cik="0000000004", ticker="NOCFO", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": 50e6, "net_income": 40e6,
             "cfo": None, "capex": 10e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import fcf_margin_series
        series = fcf_margin_series(cik)
        assert len(series) == 1
        assert series[0]["fcf_margin"] is None

    def test_missing_capex(self, db_session):
        cik = _seed_company_with_data(db_session, cik="0000000005", ticker="NOCX", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": 50e6, "net_income": 40e6,
             "cfo": 60e6, "capex": None, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import fcf_margin_series
        series = fcf_margin_series(cik)
        assert len(series) == 1
        assert series[0]["fcf_margin"] is None


# =============================================================================
# Unit Tests: cash_conversion_series
# =============================================================================


class TestCashConversionSeries:

    def test_happy_path(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import cash_conversion_series
        series = cash_conversion_series(cik)

        assert len(series) == 3
        # MSFT FY2023: CFO 87582M / NI 72361M ~ 1.21
        assert series[-1]["fy"] == 2023
        assert series[-1]["cash_conversion"] is not None
        assert series[-1]["cash_conversion"] > 1.0  # High quality earnings

    def test_zero_net_income(self, db_session):
        """Zero net income should produce None."""
        cik = _seed_company_with_data(db_session, cik="0000000006", ticker="ZNI", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": 0, "net_income": 0,
             "cfo": 60e6, "capex": 10e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import cash_conversion_series
        series = cash_conversion_series(cik)
        assert len(series) == 1
        assert series[0]["cash_conversion"] is None

    def test_negative_net_income(self, db_session):
        """Negative net income with positive CFO — ratio is negative."""
        cik = _seed_company_with_data(db_session, cik="0000000007", ticker="LOSS", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": -50e6, "net_income": -30e6,
             "cfo": 10e6, "capex": 5e6, "equity": 500e6, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import cash_conversion_series
        series = cash_conversion_series(cik)
        assert len(series) == 1
        # CFO positive / NI negative = negative ratio
        assert series[0]["cash_conversion"] is not None
        assert series[0]["cash_conversion"] < 0


# =============================================================================
# Unit Tests: roe_series
# =============================================================================


class TestRoeSeries:

    def test_happy_path(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import roe_series
        series = roe_series(cik)

        assert len(series) == 3
        # MSFT FY2023: NI 72361M / Equity 206223M ~ 0.351
        assert series[-1]["fy"] == 2023
        assert series[-1]["roe"] is not None
        assert 0.30 < series[-1]["roe"] < 0.40

    def test_negative_equity_returns_none(self, db_session):
        """Companies with negative equity (SBUX, MCD) should get None ROE."""
        cik = _seed_company_with_data(
            db_session, cik="0000000008", ticker="NEGEQ",
            negative_equity=True,
        )
        from app.metrics.compute import roe_series
        series = roe_series(cik)

        assert len(series) == 3
        for entry in series:
            assert entry["roe"] is None

    def test_zero_equity_returns_none(self, db_session):
        cik = _seed_company_with_data(db_session, cik="0000000009", ticker="ZREQ", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": 50e6, "net_income": 40e6,
             "cfo": 60e6, "capex": 10e6, "equity": 0, "debt": 100e6, "cash": 50e6},
        ])
        from app.metrics.compute import roe_series
        series = roe_series(cik)
        assert len(series) == 1
        assert series[0]["roe"] is None

    def test_single_year(self, db_session):
        cik = _seed_company_with_data(db_session, cik="0000000010", ticker="SNGL", years=[
            {"fy": 2023, "revenue": 100e6, "ebit": 30e6, "net_income": 20e6,
             "cfo": 25e6, "capex": 5e6, "equity": 200e6, "debt": 50e6, "cash": 30e6},
        ])
        from app.metrics.compute import roe_series
        series = roe_series(cik)
        assert len(series) == 1
        # NI 20M / Equity 200M = 0.10
        assert abs(series[0]["roe"] - 0.10) < 0.001

    def test_empty_data(self, db_session):
        from app.metrics.compute import roe_series
        series = roe_series("0000000099")
        assert series == []


# =============================================================================
# Integration Tests: Timeseries includes new metrics
# =============================================================================


@pytest.mark.integration
class TestTimeseriesNewMetrics:

    def test_timeseries_includes_new_series(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import timeseries_all
        ts = timeseries_all(cik)

        assert "operating_margin" in ts
        assert "fcf_margin" in ts
        assert "cash_conversion" in ts
        assert "roe" in ts

        assert len(ts["operating_margin"]) == 3
        assert len(ts["fcf_margin"]) == 3
        assert len(ts["cash_conversion"]) == 3
        assert len(ts["roe"]) == 3

    def test_timeseries_endpoint(self, client, db_session, mock_httpx_client):
        """API timeseries endpoint should return new metric series."""
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        ingest_companyfacts_richer_by_ticker("MSFT")

        resp = client.get("/api/v1/company/MSFT/timeseries")
        assert resp.status_code == 200
        data = resp.json()

        assert "operating_margin" in data
        assert "fcf_margin" in data
        assert "cash_conversion" in data
        assert "roe" in data


# =============================================================================
# Regression: Existing metrics unchanged
# =============================================================================


@pytest.mark.integration
class TestNoRegressions:

    def test_existing_timeseries_keys_present(self, db_session):
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import timeseries_all
        ts = timeseries_all(cik)

        # All pre-existing keys should still be there
        for key in ["is", "owner_earnings", "roic", "coverage",
                     "gross_margin", "net_debt", "share_count"]:
            assert key in ts, f"Missing pre-existing key: {key}"

    def test_roic_unchanged(self, db_session):
        """Adding new metrics should not affect ROIC calculation."""
        cik = _seed_company_with_data(db_session)
        from app.metrics.compute import roic_series
        series = roic_series(cik)
        assert len(series) == 3
        # All should have valid ROIC (positive equity)
        for entry in series:
            assert entry["roic"] is not None
