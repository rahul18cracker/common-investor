from app.metrics.compute import owner_earnings_series, roic_series, coverage_series, revenue_eps_series
from app.metrics import compute

def test_owner_earnings_series(monkeypatch):
    rows = [
        (2020, 1000.0, 200.0, 100.0, 500.0, 100.0, 300.0, 700.0, 50.0, 2000.0),
        (2021, 1200.0, 250.0, 100.0, 600.0, 120.0, 320.0, 750.0, 60.0, 2300.0),
    ]
    def fake_execute(sql, **params):
        class R: 
            def fetchall(self): return rows
        return R()
    monkeypatch.setattr(compute, "execute", fake_execute)
    ser = owner_earnings_series("0000000001")
    assert len(ser) == 2
    assert ser[0]["owner_earnings"] == 800.0
    assert ser[0]["owner_earnings_ps"] == 8.0

def test_roic_series(monkeypatch):
    rows = [
        (2020, 1000.0, 200.0, 100.0, 500.0, 100.0, 300.0, 700.0, 50.0, 2000.0),
    ]
    def fake_execute(sql, **params):
        class R:
            def fetchall(self): return rows
        return R()
    monkeypatch.setattr(compute, "execute", fake_execute)
    roic = roic_series("0000000001")
    assert len(roic) == 1
    assert roic[0]["roic"] is not None

def test_coverage_series(monkeypatch):
    rows = [
        (2020, 500.0, 100.0),
        (2021, 600.0, 0.0),
    ]
    def fake_execute(sql, **params):
        class R:
            def fetchall(self): return rows
        return R()
    monkeypatch.setattr(compute, "execute", fake_execute)
    cov = coverage_series("0000000001")
    assert cov[0]["coverage"] == 5.0

def test_revenue_eps_series(monkeypatch):
    rows = [
        (2019, 1000.0, 5.0),
        (2020, 1200.0, 6.0),
    ]
    def fake_execute(sql, **params):
        class R:
            def fetchall(self): return rows
        return R()
    monkeypatch.setattr(compute, "execute", fake_execute)
    ser = revenue_eps_series("0000000001")
    assert ser[0]["revenue"] == 1000.0
    assert ser[1]["eps"] == 6.0