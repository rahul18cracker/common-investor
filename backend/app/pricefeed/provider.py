import logging
from typing import Optional

log = logging.getLogger(__name__)


def price_yfinance(ticker: str) -> Optional[float]:
    try:
        import yfinance as yf

        data = yf.Ticker(ticker).history(period="1d", interval="1d")
        if data is None or data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as e:
        log.warning("Price fetch failed for %s: %s", ticker, e)
        return None
