from typing import Optional, Dict, Any
from app.db.session import execute
from app.metrics.compute import compute_growth_metrics, latest_eps, latest_owner_earnings_ps
from .core import StickerInputs, sticker_and_mos, ten_cap_price, payback_time

def resolve_cik_by_ticker(ticker: str) -> Optional[str]:
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    return row[0] if row else None

def run_default_scenario(ticker: str, mos_pct: float = 0.5, g_override: float | None = None, pe_cap: int = 20, discount: float = 0.15) -> Dict[str, Any]:
    cik = resolve_cik_by_ticker(ticker)
    if not cik: raise ValueError("Unknown ticker; ingest first.")
    eps0 = latest_eps(cik)
    growths = compute_growth_metrics(cik)
    g = g_override if g_override is not None else (growths.get("eps_cagr_5y") or growths.get("rev_cagr_5y") or growths.get("eps_cagr_10y") or growths.get("rev_cagr_10y") or 0.10)
    if eps0 is None: raise ValueError("Missing EPS; cannot compute sticker. Ingest fuller statements.")
    inputs = StickerInputs(eps0=eps0, g=float(g), pe_cap=pe_cap, discount=discount)
    sticker = sticker_and_mos(inputs, mos_pct=mos_pct)

    oe_ps = latest_owner_earnings_ps(cik) or eps0
    ten_cap = ten_cap_price(oe_ps)
    price_row = execute("SELECT price FROM price_snapshot ps JOIN company c ON ps.company_id=c.id WHERE c.cik=:cik ORDER BY ts DESC LIMIT 1", cik=cik).first()
    price = float(price_row[0]) if price_row else None
    payback = payback_time(price if price else sticker.mos_price, oe_ps, float(g)) if oe_ps else None

    return {
        "inputs": {"eps0": eps0, "g": g, "pe_cap": pe_cap, "discount": discount, "mos_pct": mos_pct},
        "results": {
            "future_eps": sticker.future_eps,
            "terminal_pe": sticker.terminal_pe,
            "future_price": sticker.future_price,
            "sticker": sticker.sticker,
            "mos_price": sticker.mos_price,
            "ten_cap_price": ten_cap,
            "payback_years": payback,
            "owner_earnings_ps": oe_ps,
            "current_price": price
        }
    }