from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from app.db.session import execute
from app.workers.tasks import enqueue_ingest
from app.metrics.compute import compute_growth_metrics, timeseries_all
from app.valuation.service import run_default_scenario
from app.nlp.fourm.service import compute_moat, compute_management, compute_margin_of_safety_recommendation
from app.nlp.fourm.sec_item1 import get_meaning_item1

router = APIRouter()

class IngestResponse(BaseModel):
    status: str
    detail: str

@router.post("/company/{ticker}/ingest", response_model=IngestResponse)
def ingest_company(ticker: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(enqueue_ingest, ticker)
    return IngestResponse(status="queued", detail=f"Ingestion queued for {ticker}")

@router.get("/company/{ticker}")
def company_summary(ticker: str):
    row = execute("SELECT c.id, c.cik, c.ticker, c.name FROM company c WHERE upper(c.ticker)=upper(:t)", t=ticker).first()
    if not row: raise HTTPException(404, detail="Company not found. Click 'Ingest'.")
    company_id, cik, tick, name = row
    latest = execute("""
        SELECT si.fy, si.revenue, si.eps_diluted, si.ebit, si.net_income
        FROM statement_is si JOIN filing f ON si.filing_id=f.id WHERE f.cik=:cik ORDER BY si.fy DESC LIMIT 1
    """, cik=cik).first()
    return {"company": {"id": company_id, "cik": cik, "ticker": tick, "name": name},
            "latest_is": {"fy": latest[0], "revenue": float(latest[1]) if latest and latest[1] is not None else None,
                          "eps_diluted": float(latest[2]) if latest and latest[2] is not None else None,
                          "ebit": float(latest[3]) if latest and latest[3] is not None else None,
                          "net_income": float(latest[4]) if latest and latest[4] is not None else None} if latest else None}

@router.get("/company/{ticker}/metrics")
def get_metrics(ticker: str):
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row: raise HTTPException(404, detail="Company not found. Ingest first.")
    cik = row[0]
    growths = compute_growth_metrics(cik)
    return {"cik": cik, "growths": growths}

@router.get("/company/{ticker}/timeseries")
def get_timeseries(ticker: str):
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row: raise HTTPException(404, detail="Company not found.")
    cik = row[0]
    return timeseries_all(cik)

class ValuationRequest(BaseModel):
    mos_pct: float = 0.5
    g: float | None = None
    pe_cap: int | None = None
    discount: float | None = None

@router.post("/company/{ticker}/valuation")
def run_valuation(ticker: str, body: ValuationRequest):
    res = run_default_scenario(ticker, mos_pct=body.mos_pct, g_override=body.g, pe_cap=body.pe_cap or 20, discount=body.discount or 0.15)
    return res

@router.get("/company/{ticker}/export/metrics.csv", response_class=PlainTextResponse)
def export_metrics_csv(ticker: str):
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row: raise HTTPException(404, detail="Company not found.")
    cik = row[0]
    g = compute_growth_metrics(cik)
    lines = ["metric,value"] + [f"{k},{'' if v is None else v}" for k,v in g.items()]
    return "\n".join(lines)

@router.get("/company/{ticker}/export/valuation.json", response_class=JSONResponse)
def export_valuation_json(ticker: str, mos_pct: float = 0.5):
    return run_default_scenario(ticker, mos_pct=mos_pct)

class AlertCreate(BaseModel):
    rule_type: str
    threshold: float | None = None

@router.post("/company/{ticker}/alerts")
def create_alert(ticker: str, body: AlertCreate):
    row = execute("SELECT id FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row: raise HTTPException(404, detail="Company not found")
    cid = int(row[0])
    execute("INSERT INTO alert_rule (company_id, rule_type, threshold, enabled) VALUES (:cid, :rtype, :thr, true)",
            cid=cid, rtype=body.rule_type, thr=body.threshold)
    return {"status": "ok"}

@router.get("/company/{ticker}/alerts")
def list_alerts(ticker: str):
    rows = execute("""
        SELECT ar.id, ar.rule_type, ar.threshold, ar.enabled
        FROM alert_rule ar JOIN company c ON c.id=ar.company_id
        WHERE upper(c.ticker)=upper(:t)
    """, t=ticker).fetchall()
    return [{"id": int(r[0]), "rule_type": r[1], "threshold": float(r[2]) if r[2] is not None else None, "enabled": bool(r[3])} for r in rows]

class AlertToggle(BaseModel):
    enabled: bool

@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    execute("DELETE FROM alert_rule WHERE id=:id", id=alert_id)
    return {"status": "deleted", "id": alert_id}

@router.patch("/alerts/{alert_id}")
def toggle_alert(alert_id: int, body: AlertToggle):
    execute("UPDATE alert_rule SET enabled=:e WHERE id=:id", e=body.enabled, id=alert_id)
    return {"status": "ok", "id": alert_id, "enabled": body.enabled}

@router.get("/company/{ticker}/fourm")
def get_fourm_analysis(ticker: str):
    """Get Four Ms analysis for a company (Meaning, Moat, Management, Margin of Safety)"""
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row:
        raise HTTPException(404, detail="Company not found. Ingest first.")
    cik = row[0]

    # Compute the Four Ms analysis
    moat_analysis = compute_moat(cik)
    management_analysis = compute_management(cik)
    mos_recommendation = compute_margin_of_safety_recommendation(cik)

    return {
        "moat": moat_analysis,
        "management": management_analysis,
        "mos_recommendation": mos_recommendation,
        "cik": cik
    }


@router.post("/company/{ticker}/fourm/meaning/refresh")
def refresh_meaning_analysis(ticker: str):
    """Refresh meaning analysis by extracting latest Item 1 from SEC filings"""
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row:
        raise HTTPException(404, detail="Company not found. Ingest first.")
    cik = row[0]

    # Extract Item 1 business description from latest 10-K
    meaning_data = get_meaning_item1(cik)

    if meaning_data.get("status") == "not_found":
        raise HTTPException(404, detail="No 10-K filing found for this company")

    # Store the meaning note in the database for future reference
    if meaning_data.get("status") == "ok":
        source_url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                     f"{meaning_data.get('accession', '').replace('-', '')}/"
                     f"{meaning_data.get('doc', '')}")
        
        # Check if we already have a recent meaning note for this company
        existing = execute("""
            SELECT id FROM meaning_note 
            WHERE company_id = (SELECT id FROM company WHERE cik = :cik)
            AND evidence_type = 'sec_10k_item1'
            AND ts > NOW() - INTERVAL '30 days'
        """, cik=cik).first()
        
        # Only insert if we don't have a recent note
        if not existing:
            execute("""
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
                    source_url=source_url)

    return meaning_data

@router.get("/debug/modules")
def debug_modules():
    import importlib, inspect
    mods = {}
    for name in [
        "app.metrics.compute",
        "app.valuation.service",
        "app.valuation.core",
        "app.nlp.fourm.service",
        "app.nlp.fourm.sec_item1"
    ]:
        try:
            m = importlib.import_module(name)
            mods[name] = inspect.getfile(m)
        except Exception as e:
            mods[name] = f"ERROR: {e}"
    return mods