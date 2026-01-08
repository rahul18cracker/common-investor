from __future__ import annotations
from typing import Dict, Any, Optional, List
from statistics import mean, pstdev
from app.db.session import execute
from app.metrics.compute import (
    roic_series,
    margin_stability,
    coverage_series,
    compute_growth_metrics,
    gross_margin_series,
    roic_persistence_score,
    net_debt_series,
    latest_debt_to_equity,
)

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
    """
    Compute moat analysis including ROIC, margin stability, gross margin trajectory,
    ROIC persistence score, and pricing power indicator.
    
    Phase C enhancements:
    - C1: gross_margin_trend (recent 3yr avg - older 3yr avg)
    - C2: roic_persistence_score (0-5 rating)
    - C4: pricing_power_score (0-1 based on gross margin level, stability, trend)
    """
    # Original ROIC analysis
    roics = _series_values(roic_series(cik), "roic")
    roic_avg = mean(roics) if roics else None
    roic_sd = pstdev(roics) if len(roics) >= 2 else None
    margin_stab = margin_stability(cik)
    
    # C1: Gross margin trajectory
    gm_series = gross_margin_series(cik)
    gm_values = [x["gross_margin"] for x in gm_series if x.get("gross_margin") is not None]
    
    latest_gross_margin = gm_values[-1] if gm_values else None
    gross_margin_trend = None
    gross_margin_stability = None
    
    if len(gm_values) >= 6:
        # Trend: compare recent 3yr avg to older 3yr avg
        recent_avg = mean(gm_values[-3:])
        older_avg = mean(gm_values[:3])
        gross_margin_trend = recent_avg - older_avg
    elif len(gm_values) >= 3:
        # With less data, compare last value to first
        gross_margin_trend = gm_values[-1] - gm_values[0]
    
    if len(gm_values) >= 3:
        gross_margin_stability = 1.0 - min(1.0, pstdev(gm_values) / mean(gm_values)) if mean(gm_values) > 0 else None
    
    # C2: ROIC persistence score (0-5)
    roic_persist = roic_persistence_score(cik)
    
    # C4: Pricing power score (0-1)
    pricing_power = _compute_pricing_power(latest_gross_margin, gross_margin_stability, gross_margin_trend)
    
    # Enhanced score calculation including new metrics
    base_score = _normalize_score([
        (roic_avg, 0.1, 0.25),
        (None if roic_sd is None else 1.0/(1.0+roic_sd), 0.4, 0.9),
        (margin_stab, 0.3, 0.9)
    ])
    
    # Adjust score with pricing power (10% weight) and ROIC persistence (10% weight)
    final_score = base_score
    if final_score is not None:
        adjustments = []
        if pricing_power is not None:
            adjustments.append(pricing_power * 0.1)
        if roic_persist is not None:
            adjustments.append((roic_persist / 5.0) * 0.1)
        if adjustments:
            final_score = final_score * 0.8 + sum(adjustments)
    
    return {
        "roic_avg": roic_avg,
        "roic_sd": roic_sd,
        "margin_stability": margin_stab,
        "latest_gross_margin": latest_gross_margin,
        "gross_margin_trend": gross_margin_trend,
        "gross_margin_stability": gross_margin_stability,
        "roic_persistence_score": roic_persist,
        "pricing_power_score": pricing_power,
        "score": final_score,
    }


def _compute_pricing_power(
    gross_margin: Optional[float],
    stability: Optional[float],
    trend: Optional[float]
) -> Optional[float]:
    """
    C4: Compute pricing power score (0-1) based on gross margin characteristics.
    
    Components (weighted):
    - Gross margin level (40%): Higher margin = stronger pricing power
    - Gross margin stability (30%): Lower volatility = more durable
    - Gross margin trend (30%): Improving = strengthening pricing power
    """
    scores = []
    weights = []
    
    # Gross margin level: 0-20% = 0, 20-50% = 0-1, >50% = 1
    if gross_margin is not None:
        if gross_margin <= 0.20:
            level_score = 0.0
        elif gross_margin >= 0.50:
            level_score = 1.0
        else:
            level_score = (gross_margin - 0.20) / 0.30
        scores.append(level_score)
        weights.append(0.4)
    
    # Stability: already 0-1 scale
    if stability is not None:
        scores.append(stability)
        weights.append(0.3)
    
    # Trend: -5% to +5% mapped to 0-1
    if trend is not None:
        if trend <= -0.05:
            trend_score = 0.0
        elif trend >= 0.05:
            trend_score = 1.0
        else:
            trend_score = (trend + 0.05) / 0.10
        scores.append(trend_score)
        weights.append(0.3)
    
    if not scores:
        return None
    
    # Weighted average
    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight

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

def compute_balance_sheet_resilience(cik: str) -> dict:
    """
    C3: Compute balance sheet resilience score (0-5) based on:
    - Interest coverage ratio (40% weight): >10x = 5, 5-10x = 3-5, 2-5x = 1-3, <2x = 0-1
    - Debt/Equity ratio (30% weight): <0.3 = 5, 0.3-0.7 = 3-5, 0.7-1.5 = 1-3, >1.5 = 0-1
    - Net debt trend (30% weight): Decreasing = bonus, Increasing = penalty
    """
    # Get coverage series for interest coverage
    cov_series = coverage_series(cik)
    cov_values = [x["coverage"] for x in cov_series if x.get("coverage") is not None]
    latest_coverage = cov_values[-1] if cov_values else None
    
    # Get debt/equity
    debt_equity = latest_debt_to_equity(cik)
    
    # Get net debt trend
    nd_series = net_debt_series(cik)
    nd_values = [x["net_debt"] for x in nd_series if x.get("net_debt") is not None]
    net_debt_trend = None
    latest_net_debt = nd_values[-1] if nd_values else None
    
    if len(nd_values) >= 3:
        # Compare recent avg to older avg
        recent_nd = mean(nd_values[-2:]) if len(nd_values) >= 2 else nd_values[-1]
        older_nd = mean(nd_values[:2]) if len(nd_values) >= 2 else nd_values[0]
        if older_nd != 0:
            net_debt_trend = (recent_nd - older_nd) / abs(older_nd)
        else:
            net_debt_trend = 0.0 if recent_nd == 0 else (1.0 if recent_nd > 0 else -1.0)
    
    # Calculate component scores (0-5 scale)
    coverage_score = None
    if latest_coverage is not None:
        if latest_coverage >= 10:
            coverage_score = 5.0
        elif latest_coverage >= 5:
            coverage_score = 3.0 + (latest_coverage - 5) / 5 * 2
        elif latest_coverage >= 2:
            coverage_score = 1.0 + (latest_coverage - 2) / 3 * 2
        else:
            coverage_score = max(0.0, latest_coverage / 2)
    
    debt_equity_score = None
    if debt_equity is not None:
        if debt_equity <= 0.3:
            debt_equity_score = 5.0
        elif debt_equity <= 0.7:
            debt_equity_score = 3.0 + (0.7 - debt_equity) / 0.4 * 2
        elif debt_equity <= 1.5:
            debt_equity_score = 1.0 + (1.5 - debt_equity) / 0.8 * 2
        else:
            debt_equity_score = max(0.0, 1.0 - (debt_equity - 1.5) / 1.5)
    
    trend_score = None
    if net_debt_trend is not None:
        # Decreasing debt (negative trend) is good
        if net_debt_trend <= -0.10:  # Debt decreased by 10%+
            trend_score = 5.0
        elif net_debt_trend <= 0:
            trend_score = 3.0 + (-net_debt_trend) / 0.10 * 2
        elif net_debt_trend <= 0.10:
            trend_score = 1.0 + (0.10 - net_debt_trend) / 0.10 * 2
        else:
            trend_score = max(0.0, 1.0 - (net_debt_trend - 0.10) / 0.20)
    
    # Weighted average (0-5 scale)
    scores = []
    weights = []
    if coverage_score is not None:
        scores.append(coverage_score)
        weights.append(0.4)
    if debt_equity_score is not None:
        scores.append(debt_equity_score)
        weights.append(0.3)
    if trend_score is not None:
        scores.append(trend_score)
        weights.append(0.3)
    
    final_score = None
    if scores:
        total_weight = sum(weights)
        final_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    
    return {
        "latest_coverage": latest_coverage,
        "debt_to_equity": debt_equity,
        "latest_net_debt": latest_net_debt,
        "net_debt_trend": net_debt_trend,
        "coverage_score": coverage_score,
        "debt_equity_score": debt_equity_score,
        "trend_score": trend_score,
        "score": final_score,
    }


def compute_margin_of_safety_recommendation(cik: str) -> dict:
    """
    Compute recommended margin of safety percentage based on moat, management,
    growth, and balance sheet resilience.
    """
    moat = compute_moat(cik)
    mgmt = compute_management(cik)
    growths = compute_growth_metrics(cik)
    balance_sheet = compute_balance_sheet_resilience(cik)
    
    moat_s = moat.get("score") or 0.5
    mgmt_s = mgmt.get("score") or 0.5
    bs_s = balance_sheet.get("score")
    g = growths.get("eps_cagr_5y") or growths.get("rev_cagr_5y") or 0.10
    
    base = 0.5
    adj = 0.0
    adj += (0.15 - min(0.15, g))
    adj += (0.5 - max(moat_s, 0.0)) * 0.2
    adj += (0.5 - max(mgmt_s, 0.0)) * 0.2
    
    # Adjust for balance sheet resilience (weak balance sheet = higher MOS needed)
    if bs_s is not None:
        # bs_s is 0-5, normalize to 0-1 and adjust
        bs_normalized = bs_s / 5.0
        adj += (0.5 - bs_normalized) * 0.1
    
    mos = min(0.7, max(0.3, base + adj))
    return {
        "recommended_mos": mos,
        "drivers": {
            "growth": g,
            "moat_score": moat_s,
            "mgmt_score": mgmt_s,
            "balance_sheet_score": bs_s,
        }
    }