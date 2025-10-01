from app.db.session import execute
from app.pricefeed.provider import price_yfinance
from app.valuation.service import run_default_scenario

def snapshot_price_for_ticker(ticker: str):
    p = price_yfinance(ticker)
    if p is None: return None
    row = execute("SELECT id FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    if not row: return None
    cid = int(row[0])
    execute("INSERT INTO price_snapshot (company_id, price, source, currency) VALUES (:cid,:p,:src,:ccy)",
            cid=cid, p=p, src="yfinance", ccy="USD")
    return p

def evaluate_alerts():
    rules = execute("SELECT ar.id, c.ticker, ar.rule_type, ar.threshold, ar.enabled FROM alert_rule ar JOIN company c ON c.id=ar.company_id WHERE ar.enabled").fetchall()
    triggered = []
    for rid, ticker, rtype, threshold, enabled in rules:
        p = price_yfinance(ticker)
        if p is None: continue
        if rtype == "price_below_threshold" and threshold is not None and p < float(threshold):
            triggered.append((rid,ticker,p,"price_below_threshold"))
        if rtype == "price_below_mos":
            try:
                val = run_default_scenario(ticker)
                mos = float(val["results"]["mos_price"])
                if p < mos:
                    triggered.append((rid,ticker,p,"price_below_mos"))
            except Exception:
                continue
    for rid, ticker, p, typ in triggered:
        execute("""
            INSERT INTO meaning_note (company_id, ts, text, source_url, section, evidence_type)
            SELECT c.id, NOW(), :text, '', 'alerts', :typ FROM company c WHERE upper(c.ticker)=upper(:t)
        """, text=f"ALERT {typ}: price {p} triggered", typ=typ, t=ticker)
    return {"triggered": len(triggered)}