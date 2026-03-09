"""
Phase 1D — Step 1: Ingest diverse companies across 9 industries.

Uses the existing seed infrastructure with a stress-test ticker list
that covers industry archetypes known to break generic financial metrics.

Usage:
    # From backend directory, inside Docker:
    docker compose exec api python -m scripts.stress_test_ingest

    # Or locally (with DB running):
    cd backend
    python -m scripts.stress_test_ingest

    # Check what's already ingested:
    python -m scripts.stress_test_ingest --check
"""

import argparse
import sys
import os

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.cli.seed import seed_tickers, check_db_has_companies

# Stress test portfolio — chosen to expose industry-specific problems.
# Each category has a brief note on what we expect to break.
STRESS_TEST_TICKERS = {
    "tech": {
        "tickers": ["MSFT", "AAPL", "GOOG"],
        "expect": "Baseline — should work well. AAPL has high buybacks.",
    },
    "banks": {
        "tickers": ["JPM", "BAC"],
        "expect": "ROIC meaningless, deposits != debt, interest is revenue not expense.",
    },
    "reits": {
        "tickers": ["O", "SPG"],
        "expect": "EPS misleading, high leverage is structural, FFO matters.",
    },
    "defense": {
        "tickers": ["LMT", "RTX"],
        "expect": "Government contract concentration, stable margins.",
    },
    "consumer_neg_equity": {
        "tickers": ["MCD", "SBUX"],
        "expect": "Negative shareholder equity from buybacks. ROIC/D-E will blow up.",
    },
    "energy": {
        "tickers": ["XOM", "CVX"],
        "expect": "Cyclical revenue, commodity-driven, different CapEx dynamics.",
    },
    "utilities": {
        "tickers": ["NEE", "DUK"],
        "expect": "Regulated, low ROIC is structural not a moat failure.",
    },
    "healthcare": {
        "tickers": ["JNJ", "UNH"],
        "expect": "Different sub-models (pharma vs managed care).",
    },
    "saas": {
        "tickers": ["CRM", "NOW"],
        "expect": "High SBC distorts EPS, recurring revenue key metric.",
    },
}


def get_all_tickers():
    """Flatten all stress test tickers into a single list."""
    tickers = []
    for category in STRESS_TEST_TICKERS.values():
        tickers.extend(category["tickers"])
    return tickers


def print_plan():
    """Print the stress test plan before executing."""
    total = sum(len(c["tickers"]) for c in STRESS_TEST_TICKERS.values())
    print(f"\nPhase 1D Stress Test — {total} companies across {len(STRESS_TEST_TICKERS)} industries\n")
    for category, info in STRESS_TEST_TICKERS.items():
        tickers_str = ", ".join(info["tickers"])
        print(f"  {category:25s} [{tickers_str}]")
        print(f"  {'':25s} Expect: {info['expect']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Phase 1D: Ingest stress test companies")
    parser.add_argument("--check", action="store_true", help="Only show plan, don't ingest")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between SEC API calls in seconds (default: 1.0)")
    parser.add_argument("--category", type=str, default=None,
                        help="Ingest only one category (e.g., 'banks', 'reits')")
    args = parser.parse_args()

    print_plan()

    if args.check:
        existing = check_db_has_companies()
        print(f"Companies currently in DB: {existing}")
        return

    if args.category:
        if args.category not in STRESS_TEST_TICKERS:
            print(f"Unknown category: {args.category}")
            print(f"Valid categories: {', '.join(STRESS_TEST_TICKERS.keys())}")
            sys.exit(1)
        tickers = STRESS_TEST_TICKERS[args.category]["tickers"]
        print(f"Ingesting category '{args.category}' only: {tickers}\n")
    else:
        tickers = get_all_tickers()

    results = seed_tickers(tickers, delay_seconds=args.delay)

    if results["failed"]:
        print("\nSome tickers failed. Review errors above and retry individually.")
        sys.exit(1)

    print("\nIngestion complete. Run stress_test_analyze.py next to check what breaks.")


if __name__ == "__main__":
    main()
