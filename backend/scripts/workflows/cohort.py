"""
Shared cohort definitions for workflow scripts.

Industry-diverse ticker list chosen to expose edge cases in XBRL parsing,
metric computation, and valuation. Each category notes what typically breaks.
"""

STRESS_TEST_COHORT = {
    "tech": {
        "tickers": ["MSFT", "AAPL", "GOOG"],
        "notes": "Baseline — should work well. AAPL has high buybacks.",
    },
    "banks": {
        "tickers": ["JPM", "BAC"],
        "notes": "ROIC meaningless, deposits != debt, interest is revenue.",
    },
    "reits": {
        "tickers": ["O", "SPG"],
        "notes": "EPS misleading, high leverage structural, FFO matters.",
    },
    "defense": {
        "tickers": ["LMT", "RTX"],
        "notes": "Government contracts, stable margins. LMT has negative equity.",
    },
    "consumer_neg_equity": {
        "tickers": ["MCD", "SBUX"],
        "notes": "Negative shareholder equity from buybacks. ROIC/D-E will be None.",
    },
    "energy": {
        "tickers": ["XOM", "CVX"],
        "notes": "Cyclical revenue, commodity-driven, different CapEx dynamics.",
    },
    "utilities": {
        "tickers": ["NEE", "DUK"],
        "notes": "Regulated, low ROIC is structural not a moat failure.",
    },
    "healthcare": {
        "tickers": ["JNJ", "UNH"],
        "notes": "Different sub-models (pharma vs managed care).",
    },
    "saas": {
        "tickers": ["CRM", "NOW"],
        "notes": "High SBC distorts EPS, recurring revenue key metric.",
    },
}


def all_tickers() -> list[str]:
    """Flat list of all cohort tickers."""
    out = []
    for cat in STRESS_TEST_COHORT.values():
        out.extend(cat["tickers"])
    return out


def industry_for_ticker(ticker: str) -> str | None:
    """Return industry category for a ticker, or None."""
    for cat, info in STRESS_TEST_COHORT.items():
        if ticker.upper() in info["tickers"]:
            return cat
    return None
