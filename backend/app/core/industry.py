"""Industry classification from SIC codes.

Maps SEC SIC codes to broad categories and provides plain-English notes
for the qualitative analysis agent. No metric suppression — just data.
"""


# Specific SIC ranges checked first (more specific wins over broad)
_SPECIFIC_RANGES = [
    # Technology (software)
    (7372, 7374, "technology"),
    # Technology (hardware / semiconductors)
    (3571, 3672, "technology"),
    # Pharma / biotech
    (2830, 2836, "pharma"),
    # Utilities (electric, gas, water)
    (4911, 4991, "utilities"),
    # Energy (oil & gas extraction + services)
    (1311, 1389, "energy"),
    # Energy (petroleum refining)
    (2911, 2911, "energy"),
    # Energy (petroleum and coal products)
    (2900, 2999, "energy"),
    # Defense / aerospace
    (3760, 3769, "defense"),
    # Banking (depository institutions)
    (6000, 6199, "banking"),
    # Securities / investments
    (6200, 6399, "securities_investments"),
    # REITs / real estate (6500-6599 + 6798 REIT trust code)
    (6500, 6599, "reits"),
    (6798, 6798, "reits"),
]

# Broad SIC division ranges (fallback)
_BROAD_RANGES = [
    (100, 999, "agriculture"),
    (1000, 1499, "mining"),
    (1500, 1799, "construction"),
    (2000, 3999, "manufacturing"),
    (4000, 4999, "transportation_utilities"),
    (5000, 5199, "wholesale"),
    (5200, 5999, "retail"),
    (6000, 6999, "financials"),
    (7000, 8999, "services"),
    (9100, 9999, "public_administration"),
]

# Agent guidance notes per category
_METRIC_NOTES: dict[str, list[str]] = {
    "banking": [
        "ROIC is not meaningful for depository banks — interest income is core revenue, not expense",
        "Use ROE and net interest margin instead of ROIC",
        "High leverage is structural, not a red flag — focus on capital ratios",
        "Deposits are liabilities but also a competitive advantage (cheap funding)",
    ],
    "reits": [
        "EPS is misleading — use FFO (Funds from Operations) instead",
        "High leverage is structural for REITs, not a moat failure",
        "Dividend yield and payout ratio are key metrics",
        "ROIC is less meaningful due to real estate depreciation rules",
    ],
    "utilities": [
        "Low ROIC is structural due to regulated returns, not a moat failure",
        "Revenue growth is typically slow — regulated rate increases",
        "High debt/equity is normal for capital-intensive regulated utilities",
        "Focus on rate base growth and regulatory environment",
    ],
    "pharma": [
        "R&D expense is the key investment — treat it like CapEx for moat analysis",
        "Patent cliffs can cause sudden revenue drops",
        "Pipeline value is not captured in financial statements",
    ],
    "energy": [
        "Revenue is commodity-driven and highly cyclical — use through-cycle averages",
        "CapEx is lumpy — maintenance vs growth CapEx distinction matters",
        "Reserve replacement ratio matters more than short-term earnings",
    ],
    "defense": [
        "Government contracts provide revenue visibility but limit pricing power",
        "Backlog/book-to-bill ratio is a key leading indicator",
        "Some defense companies carry negative equity from buybacks (e.g. LMT)",
    ],
    "securities_investments": [
        "Revenue is highly market-dependent and cyclical",
        "AUM (assets under management) is the key driver, not captured in XBRL",
        "Mark-to-market gains/losses distort net income",
    ],
    "technology": [
        "SBC (stock-based compensation) can significantly distort EPS and margins",
        "Recurring revenue (SaaS) vs one-time license revenue matters for valuation",
        "R&D spending is the moat investment — high R&D ratio is expected",
    ],
}


def sic_to_category(sic_code: str) -> str:
    """Map SIC code to broad industry category.

    Checks specific sub-ranges first (e.g. banking, pharma, technology),
    then falls back to broad SIC division ranges.

    Returns 'unknown' if the code can't be parsed or doesn't match.
    """
    try:
        code = int(sic_code)
    except (TypeError, ValueError):
        return "unknown"

    # Check specific ranges first
    for lo, hi, cat in _SPECIFIC_RANGES:
        if lo <= code <= hi:
            return cat

    # Fallback to broad ranges
    for lo, hi, cat in _BROAD_RANGES:
        if lo <= code <= hi:
            return cat

    return "unknown"


def sic_to_metric_notes(sic_code: str) -> list[str]:
    """Return plain-English notes about what the agent should know.

    These are informational strings for the qualitative analysis agent,
    NOT suppression logic. The agent uses these to contextualize metrics.
    """
    category = sic_to_category(sic_code)
    return list(_METRIC_NOTES.get(category, []))
