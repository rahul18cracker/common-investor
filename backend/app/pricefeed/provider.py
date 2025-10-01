from typing import Optional
def price_yfinance(ticker: str) -> Optional[float]:
    try:
        import yfinance as yf
        data = yf.Ticker(ticker).history(period="1d", interval="1d")
        if data is None or data.empty: return None
        return float(data["Close"].iloc[-1])
    except Exception:
        return None