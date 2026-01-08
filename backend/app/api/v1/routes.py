from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from app.db.session import execute
from app.core.utils import safe_float, safe_int, get_company_cik
from app.workers.tasks import enqueue_ingest
from app.metrics.compute import (
    compute_growth_metrics,
    timeseries_all,
    roic_average,
    latest_debt_to_equity,
    latest_owner_earnings_growth,
    quality_scores,
)
from app.valuation.service import run_default_scenario
from app.nlp.fourm.service import (
    compute_moat,
    compute_management,
    compute_margin_of_safety_recommendation,
)
from app.nlp.fourm.sec_item1 import get_meaning_item1

router = APIRouter()


# ============================================================================
# Company List and Seed Endpoints
# ============================================================================


@router.get("/companies")
def list_companies():
    """List all companies in the database with basic info"""
    rows = execute(
        """
        SELECT c.id, c.cik, c.ticker, c.name,
               (SELECT COUNT(*) FROM statement_is si JOIN filing f ON si.filing_id=f.id WHERE f.cik=c.cik) as years_data
        FROM company c
        ORDER BY c.ticker
    """
    ).fetchall()
    return {
        "count": len(rows),
        "companies": [
            {
                "id": safe_int(r[0]),
                "cik": r[1],
                "ticker": r[2],
                "name": r[3],
                "years_data": safe_int(r[4]) or 0,
            }
            for r in rows
        ],
    }


class SeedRequest(BaseModel):
    tickers: Optional[List[str]] = None


@router.post("/seed")
def seed_database(body: SeedRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger database seeding with company data.

    If no tickers provided, uses the default curated list.
    Seeding runs in background to avoid timeout.
    """
    from app.cli.seed import DEFAULT_TICKERS

    tickers = body.tickers if body.tickers else DEFAULT_TICKERS

    # Queue each ticker for background ingestion
    for ticker in tickers:
        background_tasks.add_task(enqueue_ingest, ticker.upper())

    return {
        "status": "queued",
        "tickers": [t.upper() for t in tickers],
        "message": f"Queued {len(tickers)} tickers for ingestion. Check /api/v1/companies to see progress.",
    }


@router.get("/seed/status")
def seed_status():
    """Check the current seeding status - how many companies are loaded"""
    count_row = execute("SELECT COUNT(*) FROM company").first()
    company_count = safe_int(count_row[0]) if count_row else 0

    from app.cli.seed import DEFAULT_TICKERS

    return {
        "companies_loaded": company_count,
        "default_ticker_count": len(DEFAULT_TICKERS),
        "is_seeded": company_count > 0,
        "default_tickers": DEFAULT_TICKERS,
    }


class IngestResponse(BaseModel):
    status: str
    detail: str


@router.post("/company/{ticker}/ingest", response_model=IngestResponse)
def ingest_company(ticker: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(enqueue_ingest, ticker)
    return IngestResponse(status="queued", detail=f"Ingestion queued for {ticker}")


@router.get("/company/{ticker}")
def company_summary(ticker: str):
    row = execute(
        "SELECT c.id, c.cik, c.ticker, c.name FROM company c WHERE upper(c.ticker)=upper(:t)",
        t=ticker,
    ).first()
    if not row:
        raise HTTPException(404, detail="Company not found. Click 'Ingest'.")
    company_id, cik, tick, name = row
    latest = execute(
        """
        SELECT si.fy, si.revenue, si.cogs, si.gross_profit, si.sga, si.rnd, 
               si.depreciation, si.ebit, si.interest_expense, si.taxes,
               si.net_income, si.eps_diluted, si.shares_diluted
        FROM statement_is si JOIN filing f ON si.filing_id=f.id WHERE f.cik=:cik ORDER BY si.fy DESC LIMIT 1
    """,
        cik=cik,
    ).first()
    
    latest_is = None
    if latest:
        revenue = safe_float(latest[1])
        gross_profit = safe_float(latest[3])
        ebit = safe_float(latest[7])
        
        latest_is = {
            "fy": latest[0],
            "revenue": revenue,
            "cogs": safe_float(latest[2]),
            "gross_profit": gross_profit,
            "sga": safe_float(latest[4]),
            "rnd": safe_float(latest[5]),
            "depreciation": safe_float(latest[6]),
            "ebit": ebit,
            "interest_expense": safe_float(latest[8]),
            "taxes": safe_float(latest[9]),
            "net_income": safe_float(latest[10]),
            "eps_diluted": safe_float(latest[11]),
            "shares_diluted": safe_float(latest[12]),
            "gross_margin": (gross_profit / revenue) if revenue and gross_profit else None,
            "operating_margin": (ebit / revenue) if revenue and ebit else None,
        }
    
    return {
        "company": {"id": company_id, "cik": cik, "ticker": tick, "name": name},
        "latest_is": latest_is,
    }


@router.get("/company/{ticker}/metrics")
def get_metrics(ticker: str):
    cik = get_company_cik(ticker)
    growths = compute_growth_metrics(cik)
    roic_avg_10y = roic_average(cik, years=10)
    debt_to_equity = latest_debt_to_equity(cik)
    fcf_growth = latest_owner_earnings_growth(cik)

    return {
        "cik": cik,
        "growths": growths,
        "roic_avg_10y": roic_avg_10y,
        "debt_to_equity": debt_to_equity,
        "fcf_growth": fcf_growth,
    }


@router.get("/company/{ticker}/timeseries")
def get_timeseries(ticker: str):
    cik = get_company_cik(ticker)
    return timeseries_all(cik)


@router.get("/company/{ticker}/quality-scores")
def get_quality_scores(ticker: str):
    """
    Phase B: New endpoint returning quality-related metrics for qualitative analysis.
    
    Returns:
    - gross_margin_series: Historical gross margins for trend analysis
    - latest_gross_margin: Most recent gross margin
    - gross_margin_trend: Change in gross margin (positive = improving)
    - revenue_volatility: Std dev of YoY revenue growth (cyclicality indicator)
    - growth_metrics: Extended CAGR windows (1y/3y/5y/10y for revenue and EPS)
    - net_debt_series: Historical net debt (total_debt - cash)
    - latest_net_debt: Most recent net debt
    - share_count_trend: Share count with YoY changes (dilution tracking)
    - avg_share_dilution_3y: Average share dilution over last 3 years
    - roic_persistence_score: 0-5 rating based on ROIC consistency (Option C)
    """
    cik = get_company_cik(ticker)
    return quality_scores(cik)


class ValuationRequest(BaseModel):
    mos_pct: float = 0.5
    g: float | None = None
    pe_cap: int | None = None
    discount: float | None = None


@router.post("/company/{ticker}/valuation")
def run_valuation(ticker: str, body: ValuationRequest):
    try:
        res = run_default_scenario(
            ticker,
            mos_pct=body.mos_pct,
            g_override=body.g,
            pe_cap=body.pe_cap or 20,
            discount=body.discount or 0.15,
        )
        return res
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/company/{ticker}/export/metrics.csv", response_class=PlainTextResponse)
def export_metrics_csv(ticker: str):
    cik = get_company_cik(ticker)
    g = compute_growth_metrics(cik)
    lines = ["metric,value"] + [f"{k},{'' if v is None else v}" for k, v in g.items()]
    return "\n".join(lines)


@router.get("/company/{ticker}/export/valuation.json", response_class=JSONResponse)
def export_valuation_json(ticker: str, mos_pct: float = 0.5):
    return run_default_scenario(ticker, mos_pct=mos_pct)


class AlertCreate(BaseModel):
    rule_type: str
    threshold: float | None = None


@router.post("/company/{ticker}/alerts")
def create_alert(ticker: str, body: AlertCreate):
    row = execute(
        "SELECT id FROM company WHERE upper(ticker)=upper(:t)", t=ticker
    ).first()
    if not row:
        raise HTTPException(404, detail="Company not found")
    cid = safe_int(row[0])
    execute(
        "INSERT INTO alert_rule (company_id, rule_type, threshold, enabled) VALUES (:cid, :rtype, :thr, true)",
        cid=cid,
        rtype=body.rule_type,
        thr=body.threshold,
    )
    return {"status": "ok"}


@router.get("/company/{ticker}/alerts")
def list_alerts(ticker: str):
    rows = execute(
        """
        SELECT ar.id, ar.rule_type, ar.threshold, ar.enabled
        FROM alert_rule ar JOIN company c ON c.id=ar.company_id
        WHERE upper(c.ticker)=upper(:t)
    """,
        t=ticker,
    ).fetchall()
    return [
        {
            "id": safe_int(r[0]),
            "rule_type": r[1],
            "threshold": safe_float(r[2]),
            "enabled": bool(r[3]),
        }
        for r in rows
    ]


class AlertToggle(BaseModel):
    enabled: bool


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    execute("DELETE FROM alert_rule WHERE id=:id", id=alert_id)
    return {"status": "deleted", "id": alert_id}


@router.patch("/alerts/{alert_id}")
def toggle_alert(alert_id: int, body: AlertToggle):
    execute(
        "UPDATE alert_rule SET enabled=:e WHERE id=:id", e=body.enabled, id=alert_id
    )
    return {"status": "ok", "id": alert_id, "enabled": body.enabled}


@router.get("/company/{ticker}/fourm")
def get_fourm_analysis(ticker: str):
    """Get Four Ms analysis for a company (Meaning, Moat, Management, Margin of Safety)"""
    cik = get_company_cik(ticker)

    # Compute the Four Ms analysis
    moat_analysis = compute_moat(cik)
    management_analysis = compute_management(cik)
    mos_recommendation = compute_margin_of_safety_recommendation(cik)

    return {
        "moat": moat_analysis,
        "management": management_analysis,
        "mos_recommendation": mos_recommendation,
        "cik": cik,
    }


@router.post("/company/{ticker}/fourm/meaning/refresh")
def refresh_meaning_analysis(ticker: str):
    """Refresh meaning analysis by extracting latest Item 1 from SEC filings"""
    cik = get_company_cik(ticker)

    # Extract Item 1 business description from latest 10-K
    meaning_data = get_meaning_item1(cik)

    if meaning_data.get("status") == "not_found":
        raise HTTPException(404, detail="No 10-K filing found for this company")

    # Store the meaning note in the database for future reference
    if meaning_data.get("status") == "ok":
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{meaning_data.get('accession', '').replace('-', '')}/"
            f"{meaning_data.get('doc', '')}"
        )

        # Check if we already have a recent meaning note for this company
        existing = execute(
            """
            SELECT id FROM meaning_note 
            WHERE company_id = (SELECT id FROM company WHERE cik = :cik)
            AND evidence_type = 'sec_10k_item1'
            AND ts > NOW() - INTERVAL '30 days'
        """,
            cik=cik,
        ).first()

        # Only insert if we don't have a recent note
        if not existing:
            execute(
                """
                INSERT INTO meaning_note (company_id, ts, text, source_url, section, evidence_type)
                VALUES (
                    (SELECT id FROM company WHERE cik = :cik),
                    NOW(),
                    :text,
                    :source_url,
                    'Item 1 - Business',
                    'sec_10k_item1'
                )
            """,
                cik=cik,
                text=meaning_data.get("item1_excerpt", ""),
                source_url=source_url,
            )

    return meaning_data


@router.get("/debug/modules")
def debug_modules():
    import importlib
    import inspect

    mods = {}
    for name in [
        "app.metrics.compute",
        "app.valuation.service",
        "app.valuation.core",
        "app.nlp.fourm.service",
        "app.nlp.fourm.sec_item1",
    ]:
        try:
            m = importlib.import_module(name)
            mods[name] = inspect.getfile(m)
        except Exception as e:
            mods[name] = f"ERROR: {e}"
    return mods
