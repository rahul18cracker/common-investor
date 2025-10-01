from app.valuation.core import StickerInputs, sticker_and_mos, ten_cap_price, payback_time
from app.metrics.compute import cagr

def test_cagr_basic():
    assert round(cagr(100, 161.051, 5), 4) == 0.1  # ~10%

def test_sticker_and_mos():
    inp = StickerInputs(eps0=5.0, g=0.12, pe_cap=20, discount=0.15)
    res = sticker_and_mos(inp, mos_pct=0.5)
    assert res.sticker > 0
    assert res.mos_price < res.sticker
    assert res.terminal_pe <= 24  # min(pe_cap, 2*growth%)

def test_ten_cap():
    assert ten_cap_price(10.0) == 100.0
    assert ten_cap_price(None) is None

def test_payback_time():
    assert payback_time(100.0, 10.0, 0.12, 10) is not None