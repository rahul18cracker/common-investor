#!/usr/bin/env python3
"""
Coverage Matrix — ingest companies and report field coverage.

Ingests a cohort of tickers via SEC EDGAR CompanyFacts API, then queries
the DB to build a matrix of which fields are populated vs NULL for the
latest fiscal year. Outputs JSON for machine consumption.

Usage:
    cd backend
    python -m scripts.workflows.coverage_matrix                  # full cohort
    python -m scripts.workflows.coverage_matrix --tickers MSFT,AAPL
    python -m scripts.workflows.coverage_matrix --skip-ingest    # DB only
    python -m scripts.workflows.coverage_matrix --output results.json
"""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import execute
from app.ingest.sec import ingest_companyfacts_richer_by_ticker
from scripts.workflows.cohort import all_tickers, industry_for_ticker

IS_FIELDS = [
    "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
    "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
]
BS_FIELDS = [
    "cash", "receivables", "inventory", "total_assets",
    "total_liabilities", "total_debt", "shareholder_equity",
]
CF_FIELDS = ["cfo", "capex", "buybacks", "dividends", "acquisitions"]


def resolve_cik(ticker: str) -> str | None:
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    return row[0] if row else None


def ingest_cohort(tickers: list[str], delay: float = 0.5) -> dict:
    """Ingest tickers, return {ticker: {status, years, error}}."""
    results = {}
    for i, ticker in enumerate(tickers):
        try:
            info = ingest_companyfacts_richer_by_ticker(ticker)
            results[ticker] = {"status": "ok", "years": len(info.get("years", []))}
            print(f"  [{i+1}/{len(tickers)}] {ticker}: {results[ticker]['years']} years")
        except Exception as e:
            results[ticker] = {"status": "error", "error": str(e)}
            print(f"  [{i+1}/{len(tickers)}] {ticker}: ERROR — {e}")
        if i < len(tickers) - 1:
            time.sleep(delay)
    return results


def check_fields(cik: str, table: str, fields: list[str]) -> dict:
    """Check which fields are NULL vs populated for latest year."""
    cols = ", ".join(fields)
    row = execute(
        f"SELECT {cols} FROM {table} t "
        f"JOIN filing f ON t.filing_id=f.id "
        f"WHERE f.cik=:cik ORDER BY t.fy DESC LIMIT 1",
        cik=cik,
    ).first()
    if not row:
        return {f: None for f in fields}
    return {fields[i]: row[i] for i in range(len(fields))}


def build_matrix(tickers: list[str]) -> list[dict]:
    """Build coverage matrix for all tickers."""
    rows = []
    for ticker in tickers:
        cik = resolve_cik(ticker)
        if not cik:
            rows.append({"ticker": ticker, "industry": industry_for_ticker(ticker),
                         "error": "not_ingested"})
            continue

        is_data = check_fields(cik, "statement_is", IS_FIELDS)
        bs_data = check_fields(cik, "statement_bs", BS_FIELDS)
        cf_data = check_fields(cik, "statement_cf", CF_FIELDS)

        all_fields = {**is_data, **bs_data, **cf_data}
        filled = sum(1 for v in all_fields.values() if v is not None)
        total = len(all_fields)
        nulls = [k for k, v in all_fields.items() if v is None]

        rows.append({
            "ticker": ticker,
            "industry": industry_for_ticker(ticker),
            "filled": filled,
            "total": total,
            "pct": round(filled / total * 100, 1) if total else 0,
            "nulls": nulls,
            "fields": {k: v is not None for k, v in all_fields.items()},
        })
    return rows


def print_summary(matrix: list[dict]):
    """Print human-readable summary to stdout."""
    print(f"\n{'Ticker':<8} {'Industry':<22} {'Coverage':<12} {'NULL fields'}")
    print("-" * 80)
    total_filled = 0
    total_possible = 0
    for row in matrix:
        if "error" in row:
            print(f"{row['ticker']:<8} {row.get('industry','?'):<22} {'ERROR':<12} {row['error']}")
            continue
        total_filled += row["filled"]
        total_possible += row["total"]
        nulls_str = ", ".join(row["nulls"]) if row["nulls"] else "(none)"
        print(f"{row['ticker']:<8} {row.get('industry','?'):<22} {row['filled']}/{row['total']} ({row['pct']}%)  {nulls_str}")

    if total_possible:
        overall = round(total_filled / total_possible * 100, 1)
        print(f"\nOverall: {total_filled}/{total_possible} fields populated ({overall}%)")
        total_nulls = total_possible - total_filled
        print(f"Total NULLs: {total_nulls}")

    # Aggregate: which fields are most commonly NULL?
    null_counts = {}
    for row in matrix:
        for n in row.get("nulls", []):
            null_counts[n] = null_counts.get(n, 0) + 1
    if null_counts:
        print(f"\nMost common NULLs:")
        for field, count in sorted(null_counts.items(), key=lambda x: -x[1]):
            print(f"  {field}: NULL in {count}/{len(matrix)} companies")


def main():
    parser = argparse.ArgumentParser(description="Coverage matrix for XBRL field population")
    parser.add_argument("--tickers", help="Comma-separated tickers (default: full cohort)")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion, query DB only")
    parser.add_argument("--output", help="Write JSON results to file")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between SEC API calls")
    args = parser.parse_args()

    tickers = args.tickers.split(",") if args.tickers else all_tickers()
    tickers = [t.strip().upper() for t in tickers]

    print(f"Coverage Matrix — {len(tickers)} tickers")
    print("=" * 80)

    if not args.skip_ingest:
        print("\nIngesting...")
        ingest_cohort(tickers, delay=args.delay)

    print("\nBuilding coverage matrix...")
    matrix = build_matrix(tickers)
    print_summary(matrix)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"tickers": tickers, "matrix": matrix}, f, indent=2)
        print(f"\nJSON written to {args.output}")

    # Exit code: 0 if >90% coverage, 1 otherwise
    total_filled = sum(r.get("filled", 0) for r in matrix)
    total_possible = sum(r.get("total", 0) for r in matrix)
    pct = (total_filled / total_possible * 100) if total_possible else 0
    return 0 if pct >= 90 else 1


if __name__ == "__main__":
    sys.exit(main())
