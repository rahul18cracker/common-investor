#!/usr/bin/env python3
"""
Regression Check — diff current DB values against a saved baseline.

Saves a baseline snapshot of all field values for a cohort, then on
subsequent runs compares current values to detect regressions (fields
that were populated but are now NULL, or values that changed significantly).

Usage:
    cd backend

    # Save current state as baseline:
    python -m scripts.workflows.regression_check --save-baseline

    # Compare current state to baseline:
    python -m scripts.workflows.regression_check

    # Compare specific tickers:
    python -m scripts.workflows.regression_check --tickers MSFT,AAPL

    # Custom baseline file:
    python -m scripts.workflows.regression_check --baseline-file my_baseline.json
"""

import argparse
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import execute
from scripts.workflows.cohort import all_tickers, industry_for_ticker

DEFAULT_BASELINE = Path(__file__).parent / "baseline.json"

IS_FIELDS = [
    "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
    "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
]
BS_FIELDS = [
    "cash", "receivables", "inventory", "total_assets",
    "total_liabilities", "total_debt", "shareholder_equity",
]
CF_FIELDS = ["cfo", "capex", "buybacks", "dividends", "acquisitions"]

ALL_FIELDS = IS_FIELDS + BS_FIELDS + CF_FIELDS

STATEMENTS = [
    ("statement_is", IS_FIELDS),
    ("statement_bs", BS_FIELDS),
    ("statement_cf", CF_FIELDS),
]


def resolve_cik(ticker: str) -> str | None:
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    return row[0] if row else None


def snapshot_ticker(ticker: str) -> dict | None:
    """Capture latest-year values for all fields."""
    cik = resolve_cik(ticker)
    if not cik:
        return None

    values = {}
    for table, fields in STATEMENTS:
        cols = ", ".join(fields)
        row = execute(
            f"SELECT fy, {cols} FROM {table} t "
            f"JOIN filing f ON t.filing_id=f.id "
            f"WHERE f.cik=:cik ORDER BY t.fy DESC LIMIT 1",
            cik=cik,
        ).first()
        if row:
            values["fy"] = row[0]
            for i, field in enumerate(fields):
                val = row[i + 1]
                values[field] = float(val) if val is not None else None
        else:
            for field in fields:
                values[field] = None

    return values


def save_baseline(tickers: list[str], path: Path):
    """Save current DB state as baseline."""
    baseline = {}
    for ticker in tickers:
        snap = snapshot_ticker(ticker)
        if snap:
            baseline[ticker] = snap
            print(f"  {ticker}: fy={snap.get('fy')} — {sum(1 for v in snap.values() if v is not None)}/{len(ALL_FIELDS)} fields")
        else:
            print(f"  {ticker}: not in DB")

    with open(path, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"\nBaseline saved to {path} ({len(baseline)} tickers)")


def compare(tickers: list[str], baseline_path: Path) -> list[dict]:
    """Compare current DB to baseline. Returns list of anomalies."""
    if not baseline_path.exists():
        print(f"ERROR: No baseline at {baseline_path}. Run with --save-baseline first.")
        sys.exit(1)

    with open(baseline_path) as f:
        baseline = json.load(f)

    anomalies = []
    for ticker in tickers:
        if ticker not in baseline:
            anomalies.append({
                "ticker": ticker, "type": "missing_baseline",
                "detail": "Ticker not in baseline — cannot compare",
            })
            continue

        current = snapshot_ticker(ticker)
        if not current:
            anomalies.append({
                "ticker": ticker, "type": "not_ingested",
                "detail": "Ticker not in current DB",
            })
            continue

        base = baseline[ticker]
        for field in ALL_FIELDS:
            base_val = base.get(field)
            curr_val = current.get(field)

            # Regression: was populated, now NULL
            if base_val is not None and curr_val is None:
                anomalies.append({
                    "ticker": ticker, "type": "regression_to_null",
                    "field": field, "baseline": base_val, "current": None,
                    "industry": industry_for_ticker(ticker),
                })

            # New fill: was NULL, now populated (good news)
            elif base_val is None and curr_val is not None:
                anomalies.append({
                    "ticker": ticker, "type": "new_fill",
                    "field": field, "baseline": None, "current": curr_val,
                    "industry": industry_for_ticker(ticker),
                })

            # Value changed significantly (>10% relative)
            elif base_val is not None and curr_val is not None and base_val != 0:
                pct_change = abs(curr_val - base_val) / abs(base_val)
                if pct_change > 0.10:
                    anomalies.append({
                        "ticker": ticker, "type": "value_changed",
                        "field": field, "baseline": base_val, "current": curr_val,
                        "pct_change": round(pct_change * 100, 1),
                        "industry": industry_for_ticker(ticker),
                    })

    return anomalies


def print_anomalies(anomalies: list[dict]):
    """Print anomalies grouped by type."""
    if not anomalies:
        print("\nNo anomalies found. All clear.")
        return

    regressions = [a for a in anomalies if a["type"] == "regression_to_null"]
    new_fills = [a for a in anomalies if a["type"] == "new_fill"]
    changes = [a for a in anomalies if a["type"] == "value_changed"]
    other = [a for a in anomalies if a["type"] in ("missing_baseline", "not_ingested")]

    if regressions:
        print(f"\nREGRESSIONS ({len(regressions)}) — fields that lost data:")
        for a in regressions:
            print(f"  {a['ticker']:<8} {a['field']:<22} was {a['baseline']}, now NULL")

    if new_fills:
        print(f"\nNEW FILLS ({len(new_fills)}) — fields that gained data:")
        for a in new_fills:
            print(f"  {a['ticker']:<8} {a['field']:<22} was NULL, now {a['current']}")

    if changes:
        print(f"\nVALUE CHANGES >10% ({len(changes)}):")
        for a in changes:
            print(f"  {a['ticker']:<8} {a['field']:<22} {a['baseline']} -> {a['current']} ({a['pct_change']}%)")

    if other:
        print(f"\nOTHER ({len(other)}):")
        for a in other:
            print(f"  {a['ticker']:<8} {a['type']}: {a['detail']}")

    print(f"\nSummary: {len(regressions)} regressions, {len(new_fills)} new fills, {len(changes)} value changes")


def main():
    parser = argparse.ArgumentParser(description="Regression check against saved baseline")
    parser.add_argument("--save-baseline", action="store_true", help="Save current DB as baseline")
    parser.add_argument("--tickers", help="Comma-separated tickers (default: full cohort)")
    parser.add_argument("--baseline-file", type=Path, default=DEFAULT_BASELINE, help="Baseline JSON path")
    parser.add_argument("--output", help="Write anomalies JSON to file")
    args = parser.parse_args()

    tickers = args.tickers.split(",") if args.tickers else all_tickers()
    tickers = [t.strip().upper() for t in tickers]

    if args.save_baseline:
        print(f"Saving baseline for {len(tickers)} tickers...")
        save_baseline(tickers, args.baseline_file)
        return 0

    print(f"Regression Check — {len(tickers)} tickers vs baseline")
    print("=" * 80)
    anomalies = compare(tickers, args.baseline_file)
    print_anomalies(anomalies)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(anomalies, f, indent=2)
        print(f"\nJSON written to {args.output}")

    # Exit code: 1 if any regressions
    regressions = [a for a in anomalies if a["type"] == "regression_to_null"]
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
