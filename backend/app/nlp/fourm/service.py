from __future__ import annotations
from typing import Dict, Any, Optional, List
from statistics import mean, pstdev
from app.db.session import execute
from app.metrics.compute import roic_series, margin_stability, coverage_series, compute_growth_metrics

def _series_values(series: List[dict], key: str) -> List[float]:
    return [float(x[key]) for x in series if x.get(key) is not None]

def _normalize_score(tuples):
    vals = []
    for v, low, high in tuples:
        if v is None: continue
        if v <= low: vals.append(0.0)
        elif v >= high: vals.append(1.0)
        else: vals.append((v - low) / (high - low))
    return (sum(vals)/len(vals)) if vals else None

def compute_moat(cik: str) -> dict:
    roics = _series_values(roic_series(cik), "roic")
    roic_avg = mean(roics) if roics else None
    roic_sd = pstdev(roics) if len(roics) >= 2 else None
    margin_stab = margin_stability(cik)
    return {
        "roic_avg": roic_avg,
        "roic_sd": roic_sd,
        "margin_stability": margin_stab,
        "score": _normalize_score([
            (roic_avg, 0.1, 0.25),
            (None if roic_sd is None else 1.0/(1.0+roic_sd), 0.4, 0.9),
            (margin_stab, 0.3, 0.9)
        ])
    }

def compute_management(cik: str) -> dict:
    rows = execute("""
        SELECT COALESCE(cf.fy, si.fy) as fy, cf.cfo, cf.capex, cf.buybacks, cf.dividends, si.revenue
        FROM filing f
        LEFT JOIN statement_cf cf ON cf.filing_id=f.id
        LEFT JOIN statement_is si ON si.filing_id=f.id AND si.fy = cf.fy
        WHERE f.cik=:cik ORDER BY 1 ASC
    """, cik=cik).fetchall()
    items = []
    for fy, cfo, capex, buybacks, dividends, revenue in rows:
        if fy is None: continue
        cfo = float(cfo) if cfo is not None else None
        capex = float(capex) if capex is not None else None
        bb = float(buybacks) if buybacks is not None else 0.0
        divs = float(dividends) if dividends is not None else 0.0
        reinvest_ratio = None
        if cfo and cfo != 0 and capex is not None:
            reinvest_ratio = capex / cfo
        payout_ratio = None
        if cfo and cfo != 0:
            payout_ratio = (bb + divs) / cfo
        items.append({"fy": int(fy), "reinvest_ratio": reinvest_ratio, "payout_ratio": payout_ratio})
    reinvest = [x["reinvest_ratio"] for x in items if x["reinvest_ratio"] is not None]
    payout = [x["payout_ratio"] for x in items if x["payout_ratio"] is not None]
    def band_score(x, low, high):
        if x is None: return None
        if x < low: return x/low * 0.7
        if x > high: return max(0.0, 1.0 - (x-high)/(2*high))
        return 1.0
    scores = []
    if reinvest: scores.append(mean([band_score(x, 0.3, 0.7) for x in reinvest if x is not None]))
    if payout: scores.append(mean([band_score(x, 0.0, 0.6) for x in payout if x is not None]))
    mgmt_score = mean(scores) if scores else None
    return {"reinvest_ratio_avg": mean(reinvest) if reinvest else None,
            "payout_ratio_avg": mean(payout) if payout else None,
            "score": mgmt_score}

def compute_margin_of_safety_recommendation(cik: str) -> dict:
    moat = compute_moat(cik)
    mgmt = compute_management(cik)
    growths = compute_growth_metrics(cik)
    moat_s = moat.get("score") or 0.5
    mgmt_s = mgmt.get("score") or 0.5
    g = growths.get("eps_cagr_5y") or growths.get("rev_cagr_5y") or 0.10
    base = 0.5
    adj = 0.0
    adj += (0.15 - min(0.15, g))
    adj += (0.5 - max(moat_s, 0.0)) * 0.2
    adj += (0.5 - max(mgmt_s, 0.0)) * 0.2
    mos = min(0.7, max(0.3, base + adj))
    return {"recommended_mos": mos, "drivers": {"growth": g, "moat_score": moat_s, "mgmt_score": mgmt_s}}