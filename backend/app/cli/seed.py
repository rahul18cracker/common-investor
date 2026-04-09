"""
Seed script to pre-load ticker data into the database.

This script ingests financial data for a curated list of companies,
providing a diverse set of examples for testing and demonstration.

Usage:
    # From backend directory:
    python -m app.cli.seed                    # Seed all default tickers
    python -m app.cli.seed --tickers MSFT,AAPL  # Seed specific tickers
    python -m app.cli.seed --check            # Check if DB needs seeding
    python -m app.cli.seed --force            # Force re-seed even if data exists
"""

import argparse
import logging
import sys
import time
from typing import List

log = logging.getLogger(__name__)

# Default tickers - diverse mix for Rule #1 analysis
# Tech Giants: Strong moats, consistent data
# Consumer Moats: Brand moats, defensive
# Financials: Different business models
# Industrial: Cyclical examples
# Retail: Different moat types
DEFAULT_TICKERS = [
    "MSFT",  # Tech - Cloud/Software moat
    "AAPL",  # Tech - Ecosystem/Brand moat
    "GOOGL",  # Tech - Network effects/Search moat
    "KO",  # Consumer - Brand moat, defensive
    "PG",  # Consumer - Brand moat, staples
    "JNJ",  # Healthcare - Diversified, defensive
    "V",  # Financials - Network effects (payments)
    "BRK-B",  # Financials - Insurance/Conglomerate
    "CAT",  # Industrial - Cyclical, scale moat
    "COST",  # Retail - Membership moat
    "HD",  # Retail - Scale/Distribution moat
    "UNH",  # Healthcare - Scale moat
]


def check_db_has_companies() -> int:
    """Check how many companies are already in the database."""
    from app.db.session import execute

    try:
        result = execute("SELECT COUNT(*) FROM company")
        row = result.first()
        return int(row[0]) if row else 0
    except Exception as e:
        log.error("Error checking database: %s", e)
        return 0


def ingest_ticker(ticker: str) -> dict:
    """Ingest a single ticker synchronously."""
    from app.ingest.sec import ingest_companyfacts_richer_by_ticker

    try:
        result = ingest_companyfacts_richer_by_ticker(ticker)
        return {"ticker": ticker, "status": "success", "result": result}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "error": str(e)}


def seed_tickers(tickers: List[str], delay_seconds: float = 0.5) -> dict:
    """
    Seed multiple tickers with rate limiting.

    SEC EDGAR has rate limits, so we add a small delay between requests.
    """
    results: dict[str, list] = {"success": [], "failed": []}
    total = len(tickers)

    log.info("Seeding %d tickers", total)

    for i, ticker in enumerate(tickers, 1):
        log.info("Ingesting %s [%d/%d]", ticker, i, total)

        result = ingest_ticker(ticker)

        if result["status"] == "success":
            years = result.get("result", {}).get("years", [])
            log.info("OK: %s (%d years)", ticker, len(years))
            results["success"].append(ticker)
        else:
            log.warning("FAILED: %s - %s", ticker, result.get("error", "Unknown error"))
            results["failed"].append({"ticker": ticker, "error": result.get("error")})

        # Rate limiting - be nice to SEC EDGAR
        if i < total:
            time.sleep(delay_seconds)

    log.info("Seeding complete: %d/%d success", len(results["success"]), total)
    if results["failed"]:
        failed_tickers = [f["ticker"] for f in results["failed"]]
        log.warning("Failed tickers: %s", failed_tickers)

    return results


def main():
    parser = argparse.ArgumentParser(description="Seed the Common Investor database with company data")
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to seed (default: curated list)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if seeding is needed, don't actually seed",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force seeding even if companies already exist",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds (default: 0.5)",
    )

    args = parser.parse_args()

    # Parse tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = DEFAULT_TICKERS

    # Check current state
    existing_count = check_db_has_companies()
    log.info("Current companies in database: %d", existing_count)

    if args.check:
        if existing_count == 0:
            log.info("Database is empty. Seeding recommended.")
            sys.exit(1)  # Exit code 1 = needs seeding
        else:
            log.info("Database has data. No seeding needed.")
            sys.exit(0)  # Exit code 0 = no seeding needed

    # Decide whether to seed
    if existing_count > 0 and not args.force:
        log.info("Database already has %d companies. Use --force to re-seed anyway.", existing_count)
        sys.exit(0)

    # Run seeding
    results = seed_tickers(tickers, delay_seconds=args.delay)

    # Exit with appropriate code
    if results["failed"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
