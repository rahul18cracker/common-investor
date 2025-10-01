from dataclasses import dataclass
from typing import Optional

@dataclass
class StickerInputs:
    eps0: float
    g: float = 0.15
    pe_cap: int = 20
    discount: float = 0.15

@dataclass
class StickerResult:
    future_eps: float
    terminal_pe: float
    future_price: float
    sticker: float
    mos_price: float

def sticker_and_mos(inp: StickerInputs, mos_pct: float = 0.5) -> StickerResult:
    g = max(0.0, min(inp.g, 0.5))
    future_eps = inp.eps0 * ((1.0 + g) ** 10.0)
    recommended_pe = min(inp.pe_cap, max(5.0, 2.0 * (g * 100.0)))
    future_price = future_eps * recommended_pe
    sticker = future_price / ((1.0 + inp.discount) ** 10.0)
    mos_price = sticker * (1.0 - mos_pct)
    return StickerResult(future_eps, recommended_pe, future_price, sticker, mos_price)

def ten_cap_price(owner_earnings_per_share: Optional[float]) -> Optional[float]:
    if owner_earnings_per_share is None or owner_earnings_per_share <= 0: 
        return None
    return owner_earnings_per_share / 0.10

def payback_time(purchase_price: float, owner_earnings_ps: Optional[float], growth: float, max_years: int = 10) -> Optional[int]:
    if purchase_price <= 0 or owner_earnings_ps is None or owner_earnings_ps <= 0:
        return None
    cum = 0.0
    cur = owner_earnings_ps
    for year in range(1, max_years + 1):
        cum += cur
        if cum >= purchase_price:
            return year
        cur *= (1.0 + max(0.0, growth))
    return None