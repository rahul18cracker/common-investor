from __future__ import annotations
from typing import List, Tuple, Optional, Dict
from statistics import pstdev
from app.db.session import execute


def cagr(first: float, last: float, years: int) -> Optional[float]:
    if first is None or last is None or years <= 0 or first <= 0 or last <= 0:
        return None
    try:
        return (last / first) ** (1.0 / years) - 1.0
    except Exception:
        return None


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
    out = []
    for r in rows:
        fy, cfo, capex, shares, ebit, taxes, debt, equity, cash, revenue = r
        out.append(
            {
                "fy": int(fy) if fy is not None else None,
                "cfo": float(cfo) if cfo is not None else None,
                "capex": float(capex) if capex is not None else None,
                "shares": float(shares) if shares is not None else None,
                "ebit": float(ebit) if ebit is not None else None,
                "taxes": float(taxes) if taxes is not None else None,
                "debt": float(debt) if debt is not None else None,
                "equity": float(equity) if equity is not None else None,
                "cash": float(cash) if cash is not None else None,
                "revenue": float(revenue) if revenue is not None else None,
            }
        )
    return out


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

    def window(vals, n):
        last_year = years[-1]
        first_year = max(years[0], last_year - (n - 1))
        first_idx = next(
            (
                i
                for i, (fy, v) in enumerate(zip(years, vals))
                if fy >= first_year and v is not None
            ),
            None,
        )
        last_idx = next(
            (
                i
                for i, (fy, v) in reversed(list(enumerate(zip(years, vals))))
                if fy <= last_year and v is not None
            ),
            None,
        )
        if first_idx is None or last_idx is None or last_idx <= first_idx:
            return None
        span_years = years[last_idx] - years[first_idx]
        if span_years <= 0:
            return None
        return cagr(vals[first_idx], vals[last_idx], span_years)

    return {
        "rev_cagr_5y": window(revs, 5),
        "rev_cagr_10y": window(revs, 10),
        "eps_cagr_5y": window(eps, 5),
        "eps_cagr_10y": window(eps, 10),
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
    return [
        {
            "fy": int(fy),
            "revenue": float(rev) if rev is not None else None,
            "eps": float(eps) if eps is not None else None,
        }
        for fy, rev, eps in rows
    ]


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
    return {
        "is": revenue_eps_series(cik),
        "owner_earnings": owner_earnings_series(cik),
        "roic": roic_series(cik),
        "coverage": coverage_series(cik),
    }
