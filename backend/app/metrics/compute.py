from __future__ import annotations
from typing import List, Tuple, Optional, Dict
from statistics import pstdev
from app.db.session import execute
from app.core.utils import convert_row_to_dict


def cagr(first: float, last: float, years: int) -> Optional[float]:
    if first is None or last is None or years <= 0 or first <= 0 or last <= 0:
        return None
    try:
        return (last / first) ** (1.0 / years) - 1.0
    except Exception:
        return None


def _calculate_window_cagr(years: List[int], values: List[Optional[float]], window_years: int) -> Optional[float]:
    """Calculate CAGR over a sliding window of years.
    
    Finds the first and last non-None values within the window and computes CAGR.
    
    Args:
        years: List of fiscal years (ascending order)
        values: List of values corresponding to each year
        window_years: Number of years for the window (e.g., 5 for 5-year CAGR)
    
    Returns:
        CAGR as a decimal (e.g., 0.15 for 15%) or None if insufficient data
    """
    if not years or not values or len(years) != len(values):
        return None
    
    last_year = years[-1]
    first_year = max(years[0], last_year - (window_years - 1))
    
    # Find first non-None value in window
    first_idx = next(
        (i for i, (fy, v) in enumerate(zip(years, values))
         if fy >= first_year and v is not None),
        None,
    )
    
    # Find last non-None value in window
    last_idx = next(
        (i for i, (fy, v) in reversed(list(enumerate(zip(years, values))))
         if fy <= last_year and v is not None),
        None,
    )
    
    if first_idx is None or last_idx is None or last_idx <= first_idx:
        return None
    
    span_years = years[last_idx] - years[first_idx]
    if span_years <= 0:
        return None
    
    return cagr(values[first_idx], values[last_idx], span_years)


def _fetch_is_series(
    cik: str,
) -> List[Tuple[int, Optional[float], Optional[float], Optional[float]]]:
    rows = execute(
        """
        SELECT si.fy, si.revenue, si.eps_diluted, si.ebit
        FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.fy IS NOT NULL
        ORDER BY si.fy ASC
    """,
        cik=cik,
    ).fetchall()
    return [
        (
            int(r[0]),
            float(r[1]) if r[1] is not None else None,
            float(r[2]) if r[2] is not None else None,
            float(r[3]) if r[3] is not None else None,
        )
        for r in rows
    ]


def _fetch_cf_bs_for_roic(cik: str):
    rows = execute(
        """
        SELECT COALESCE(cf.fy, si.fy) as fy,
               cf.cfo, cf.capex, si.shares_diluted, si.ebit, si.taxes,
               bs.total_debt, bs.shareholder_equity, bs.cash, si.revenue
        FROM filing f
        LEFT JOIN statement_cf cf ON cf.filing_id=f.id
        LEFT JOIN statement_is si ON si.filing_id=f.id AND si.fy = cf.fy
        LEFT JOIN statement_bs bs ON bs.filing_id=f.id AND bs.fy = cf.fy
        WHERE f.cik=:cik
        ORDER BY 1 ASC
    """,
        cik=cik,
    ).fetchall()
    
    fields = ['fy', 'cfo', 'capex', 'shares', 'ebit', 'taxes', 'debt', 'equity', 'cash', 'revenue']
    type_map = {
        'fy': int,
        'cfo': float,
        'capex': float,
        'shares': float,
        'ebit': float,
        'taxes': float,
        'debt': float,
        'equity': float,
        'cash': float,
        'revenue': float,
    }
    
    return [convert_row_to_dict(row, fields, type_map) for row in rows]


def compute_growth_metrics(cik: str) -> Dict[str, Optional[float]]:
    series = _fetch_is_series(cik)
    if not series or len(series) < 2:
        return {
            "rev_cagr_5y": None,
            "rev_cagr_10y": None,
            "eps_cagr_5y": None,
            "eps_cagr_10y": None,
        }
    years = [fy for fy, *_ in series]
    revs = [rev for _, rev, _, _ in series]
    eps = [e for _, _, e, _ in series]

    return {
        "rev_cagr_5y": _calculate_window_cagr(years, revs, 5),
        "rev_cagr_10y": _calculate_window_cagr(years, revs, 10),
        "eps_cagr_5y": _calculate_window_cagr(years, eps, 5),
        "eps_cagr_10y": _calculate_window_cagr(years, eps, 10),
    }


def owner_earnings_series(cik: str):
    rows = _fetch_cf_bs_for_roic(cik)
    out = []
    for r in rows:
        fy = r["fy"]
        if fy is None:
            continue
        cfo, capex, shares = r["cfo"], r["capex"], r["shares"]
        oe = (cfo - capex) if (cfo is not None and capex is not None) else None
        oe_ps = (oe / shares) if (oe is not None and shares and shares != 0) else None
        out.append({"fy": fy, "owner_earnings": oe, "owner_earnings_ps": oe_ps})
    return out


def latest_owner_earnings_ps(cik: str):
    ser = owner_earnings_series(cik)
    if not ser:
        return None
    last = next(
        (x for x in reversed(ser) if x.get("owner_earnings_ps") is not None), None
    )
    return float(last["owner_earnings_ps"]) if last else None


def roic_series(cik: str):
    rows = _fetch_cf_bs_for_roic(cik)
    out = []
    for r in rows:
        fy, ebit, taxes, debt, equity, cash = (
            r["fy"],
            r["ebit"],
            r["taxes"],
            r["debt"],
            r["equity"],
            r["cash"],
        )
        if fy is None:
            continue
        roic = None
        if (
            ebit is not None
            and equity is not None
            and debt is not None
            and cash is not None
        ):
            tax_rate = None
            if taxes is not None and ebit != 0:
                tax_rate = max(0.0, min(0.35, taxes / abs(ebit)))
            nopat = ebit * (1.0 - (tax_rate if tax_rate is not None else 0.21))
            inv_cap = equity + debt - cash
            if inv_cap != 0:
                roic = nopat / inv_cap
        out.append({"fy": fy, "roic": roic})
    return out


def coverage_series(cik: str):
    rows = execute(
        """
        SELECT si.fy, si.ebit, si.interest_expense
        FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.fy IS NOT NULL
        ORDER BY si.fy ASC
    """,
        cik=cik,
    ).fetchall()
    out = []
    for fy, ebit, interest in rows:
        cov = None
        if ebit is not None and interest is not None and float(interest) != 0:
            cov = float(ebit) / float(interest)
        out.append({"fy": int(fy), "coverage": cov})
    return out


def margin_stability(cik: str):
    series = _fetch_is_series(cik)
    margins = [
        (e / rev) for _, rev, _, e in series if rev and e is not None and rev != 0
    ]
    if len(margins) < 3:
        return None
    sd = pstdev(margins)
    avg = sum(margins) / len(margins)
    if avg == 0:
        return None
    stability = max(0.0, min(1.0, 1.0 - (sd / abs(avg))))
    return stability


def latest_eps(cik: str) -> Optional[float]:
    row = execute(
        """
        SELECT si.eps_diluted FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.eps_diluted IS NOT NULL ORDER BY si.fy DESC LIMIT 1
    """,
        cik=cik,
    ).first()
    return float(row[0]) if row and row[0] is not None else None


def revenue_eps_series(cik: str):
    rows = execute(
        """
        SELECT si.fy, si.revenue, si.eps_diluted
        FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.fy IS NOT NULL
        ORDER BY si.fy ASC
    """,
        cik=cik,
    ).fetchall()
    
    fields = ['fy', 'revenue', 'eps']
    type_map = {'fy': int, 'revenue': float, 'eps': float}
    return [convert_row_to_dict(row, fields, type_map) for row in rows]


def roic_average(cik: str, years: int = 10) -> Optional[float]:
    """Calculate average ROIC over the specified number of years"""
    series = roic_series(cik)
    recent = [x["roic"] for x in series if x["roic"] is not None][-years:]
    if not recent:
        return None
    return sum(recent) / len(recent)


def latest_debt_to_equity(cik: str) -> Optional[float]:
    """Calculate latest debt-to-equity ratio"""
    rows = execute(
        """
        SELECT bs.total_debt, bs.shareholder_equity
        FROM statement_bs bs JOIN filing f ON bs.filing_id=f.id
        WHERE f.cik=:cik AND bs.total_debt IS NOT NULL AND bs.shareholder_equity IS NOT NULL
        ORDER BY bs.fy DESC LIMIT 1
    """,
        cik=cik,
    ).first()
    if not rows or not rows[0] or not rows[1]:
        return None
    debt, equity = float(rows[0]), float(rows[1])
    if equity == 0:
        return None
    return debt / equity


def latest_owner_earnings_growth(cik: str) -> Optional[float]:
    """Calculate 5-year owner earnings CAGR"""
    series = owner_earnings_series(cik)
    oe_vals = [
        (x["fy"], x["owner_earnings"])
        for x in series
        if x["owner_earnings"] is not None
    ]
    if len(oe_vals) < 2:
        return None

    # Get 5-year window
    years = [fy for fy, _ in oe_vals]
    last_year = years[-1]
    first_year = max(years[0], last_year - 4)

    first_idx = next(
        (i for i, (fy, val) in enumerate(oe_vals) if fy >= first_year), None
    )
    last_idx = len(oe_vals) - 1

    if first_idx is None or last_idx <= first_idx:
        return None

    span_years = oe_vals[last_idx][0] - oe_vals[first_idx][0]
    if span_years <= 0:
        return None

    return cagr(oe_vals[first_idx][1], oe_vals[last_idx][1], span_years)


def timeseries_all(cik: str):
    """
    Return all time series data for charts.
    
    Phase D enhancement: Added gross_margin and net_debt series.
    """
    return {
        "is": revenue_eps_series(cik),
        "owner_earnings": owner_earnings_series(cik),
        "roic": roic_series(cik),
        "coverage": coverage_series(cik),
        "gross_margin": gross_margin_series(cik),
        "net_debt": net_debt_series(cik),
        "share_count": share_count_trend(cik),
    }


# =============================================================================
# Phase B: New Metrics Functions
# =============================================================================

def gross_margin_series(cik: str) -> List[Dict]:
    """
    B1: Calculate gross margin series for trend analysis.
    
    Returns list of {fy, gross_margin} where gross_margin = gross_profit / revenue.
    If gross_profit is not available, attempts to calculate from revenue - cogs.
    """
    rows = execute(
        """
        SELECT si.fy, si.revenue, si.gross_profit, si.cogs
        FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.fy IS NOT NULL
        ORDER BY si.fy ASC
    """,
        cik=cik,
    ).fetchall()
    
    out = []
    for fy, revenue, gross_profit, cogs in rows:
        gm = None
        rev = float(revenue) if revenue is not None else None
        gp = float(gross_profit) if gross_profit is not None else None
        cost = float(cogs) if cogs is not None else None
        
        if rev and rev != 0:
            if gp is not None:
                gm = gp / rev
            elif cost is not None:
                gm = (rev - cost) / rev
        
        out.append({"fy": int(fy), "gross_margin": gm})
    return out


def revenue_volatility(cik: str) -> Optional[float]:
    """
    B2: Calculate revenue volatility as std dev of YoY revenue growth rates.
    
    This measures cyclicality - higher volatility indicates more cyclical business.
    Returns None if insufficient data (need at least 3 years for meaningful volatility).
    """
    series = _fetch_is_series(cik)
    if len(series) < 3:
        return None
    
    # Calculate YoY growth rates
    growth_rates = []
    for i in range(1, len(series)):
        prev_rev = series[i - 1][1]  # revenue is index 1
        curr_rev = series[i][1]
        if prev_rev and curr_rev and prev_rev != 0:
            growth = (curr_rev - prev_rev) / prev_rev
            growth_rates.append(growth)
    
    if len(growth_rates) < 2:
        return None
    
    return pstdev(growth_rates)


def compute_growth_metrics_extended(cik: str) -> Dict[str, Optional[float]]:
    """
    B3: Extended growth metrics with 1y/3y/5y/10y CAGR windows.
    
    Extends the original compute_growth_metrics() with shorter windows
    for more granular trend analysis.
    """
    series = _fetch_is_series(cik)
    if not series or len(series) < 2:
        return {
            "rev_cagr_1y": None,
            "rev_cagr_3y": None,
            "rev_cagr_5y": None,
            "rev_cagr_10y": None,
            "eps_cagr_1y": None,
            "eps_cagr_3y": None,
            "eps_cagr_5y": None,
            "eps_cagr_10y": None,
        }
    
    years = [fy for fy, *_ in series]
    revs = [rev for _, rev, _, _ in series]
    eps = [e for _, _, e, _ in series]

    return {
        "rev_cagr_1y": _calculate_window_cagr(years, revs, 1),
        "rev_cagr_3y": _calculate_window_cagr(years, revs, 3),
        "rev_cagr_5y": _calculate_window_cagr(years, revs, 5),
        "rev_cagr_10y": _calculate_window_cagr(years, revs, 10),
        "eps_cagr_1y": _calculate_window_cagr(years, eps, 1),
        "eps_cagr_3y": _calculate_window_cagr(years, eps, 3),
        "eps_cagr_5y": _calculate_window_cagr(years, eps, 5),
        "eps_cagr_10y": _calculate_window_cagr(years, eps, 10),
    }


def net_debt_series(cik: str) -> List[Dict]:
    """
    B4: Calculate net debt series (total_debt - cash).
    
    Negative net debt means company has more cash than debt (strong position).
    """
    rows = execute(
        """
        SELECT bs.fy, bs.total_debt, bs.cash
        FROM statement_bs bs JOIN filing f ON bs.filing_id=f.id
        WHERE f.cik=:cik AND bs.fy IS NOT NULL
        ORDER BY bs.fy ASC
    """,
        cik=cik,
    ).fetchall()
    
    out = []
    for fy, total_debt, cash in rows:
        nd = None
        debt = float(total_debt) if total_debt is not None else None
        cash_val = float(cash) if cash is not None else None
        
        if debt is not None and cash_val is not None:
            nd = debt - cash_val
        
        out.append({"fy": int(fy), "net_debt": nd})
    return out


def share_count_trend(cik: str) -> List[Dict]:
    """
    B5: Track diluted share count and YoY changes.
    
    Decreasing shares = buybacks (shareholder friendly)
    Increasing shares = dilution (shareholder unfriendly)
    """
    rows = execute(
        """
        SELECT si.fy, si.shares_diluted
        FROM statement_is si JOIN filing f ON si.filing_id=f.id
        WHERE f.cik=:cik AND si.fy IS NOT NULL
        ORDER BY si.fy ASC
    """,
        cik=cik,
    ).fetchall()
    
    out = []
    prev_shares = None
    for fy, shares in rows:
        shares_val = float(shares) if shares is not None else None
        yoy_change = None
        
        if shares_val is not None and prev_shares is not None and prev_shares != 0:
            yoy_change = (shares_val - prev_shares) / prev_shares
        
        out.append({
            "fy": int(fy),
            "shares": shares_val,
            "yoy_change": yoy_change,
        })
        prev_shares = shares_val
    
    return out


def roic_persistence_score(cik: str, years: int = 5, threshold: float = 0.15) -> Optional[int]:
    """
    B6: Calculate ROIC persistence score (0-5) based on Option C criteria.
    
    Option C: Must be >= threshold (15%) AND stable (low variance).
    
    Scoring:
    - Start with count of years where ROIC >= threshold (0-5)
    - Penalize by 1 point if ROIC variance is high (CV > 0.3)
    - Bonus 1 point if all years meet threshold AND variance is very low (CV < 0.15)
    
    Returns 0-5 score, or None if insufficient data.
    """
    series = roic_series(cik)
    recent_roics = [x["roic"] for x in series if x["roic"] is not None][-years:]
    
    if len(recent_roics) < 2:
        return None
    
    # Count years meeting threshold
    above_threshold = sum(1 for r in recent_roics if r >= threshold)
    
    # Calculate coefficient of variation (CV) for stability
    avg_roic = sum(recent_roics) / len(recent_roics)
    if avg_roic == 0:
        return above_threshold  # Can't calculate CV, return base score
    
    std_roic = pstdev(recent_roics)
    cv = std_roic / abs(avg_roic)  # Coefficient of variation
    
    # Start with base score (years above threshold, max 5)
    score = min(above_threshold, 5)
    
    # Penalize high variance (CV > 0.3)
    if cv > 0.3:
        score = max(0, score - 1)
    
    # Bonus for excellent consistency (all years above threshold AND very stable)
    if above_threshold >= years and cv < 0.15:
        score = min(5, score + 1)
    
    return score


def quality_scores(cik: str) -> Dict:
    """
    Aggregate function returning all quality-related metrics for the new API endpoint.
    """
    gm_series = gross_margin_series(cik)
    rev_vol = revenue_volatility(cik)
    growth = compute_growth_metrics_extended(cik)
    nd_series = net_debt_series(cik)
    shares = share_count_trend(cik)
    roic_score = roic_persistence_score(cik)
    
    # Calculate gross margin trend (positive = improving)
    gm_trend = None
    gm_values = [x["gross_margin"] for x in gm_series if x["gross_margin"] is not None]
    if len(gm_values) >= 3:
        recent_avg = sum(gm_values[-3:]) / 3
        older_avg = sum(gm_values[:3]) / min(3, len(gm_values))
        gm_trend = recent_avg - older_avg
    
    # Latest gross margin
    latest_gm = gm_values[-1] if gm_values else None
    
    # Latest net debt
    nd_values = [x["net_debt"] for x in nd_series if x["net_debt"] is not None]
    latest_net_debt = nd_values[-1] if nd_values else None
    
    # Share dilution trend (average YoY change over last 3 years)
    share_changes = [x["yoy_change"] for x in shares if x["yoy_change"] is not None]
    avg_dilution = sum(share_changes[-3:]) / len(share_changes[-3:]) if len(share_changes) >= 1 else None
    
    return {
        "gross_margin_series": gm_series,
        "latest_gross_margin": latest_gm,
        "gross_margin_trend": gm_trend,
        "revenue_volatility": rev_vol,
        "growth_metrics": growth,
        "net_debt_series": nd_series,
        "latest_net_debt": latest_net_debt,
        "share_count_trend": shares,
        "avg_share_dilution_3y": avg_dilution,
        "roic_persistence_score": roic_score,
    }
