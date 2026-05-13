#!/usr/bin/env python3
"""
Phase 1B Pre-flight: ingest 25-company pilot cohort and verify data readiness.

Checks which tickers are missing from the DB, ingests them via SEC EDGAR,
runs the coverage matrix to confirm field population, then prints a readiness
report. Exits 0 if all companies are ready, 1 if any are missing or critically
under-populated (<50% field coverage).

Usage (from backend/ directory):
    python -m scripts.workflows.phase1b_preflight
    python -m scripts.workflows.phase1b_preflight --skip-ingest      # DB-only check
    python -m scripts.workflows.phase1b_preflight --output report.json
    python -m scripts.workflows.phase1b_preflight --tickers NVDA LLY  # partial run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import execute
from app.ingest.sec import ingest_companyfacts_richer_by_ticker
from scripts.workflows.coverage_matrix import IS_FIELDS, BS_FIELDS, CF_FIELDS, build_matrix

# ---------------------------------------------------------------------------
# 25-company Phase 1B cohort — one ticker per distinct financial archetype
# ---------------------------------------------------------------------------

PHASE1B_COHORT: dict[str, dict] = {
    # Already piloted in Increment 3 (skip in pilot_runner but keep for preflight)
    "enterprise_software": {
        "ticker": "MSFT",
        "archetype": "Enterprise software + cloud (Azure)",
        "known_gaps": [],
    },
    "consumer_electronics": {
        "ticker": "AAPL",
        "archetype": "Consumer electronics + services",
        "known_gaps": [],
    },
    "bigbox_retail": {
        "ticker": "WMT",
        "archetype": "Big-box retail, low-margin high-volume",
        "known_gaps": [],
    },
    "commercial_bank": {
        "ticker": "JPM",
        "archetype": "Commercial bank — interest income, NIM",
        "known_gaps": ["operating_margin", "fcf_margin"],
    },
    "qsr_neg_equity": {
        "ticker": "SBUX",
        "archetype": "QSR franchise, structural negative equity",
        "known_gaps": ["roic_suppressed_years"],
    },
    # Already ingested, not yet piloted
    "search_cloud": {
        "ticker": "GOOGL",
        "archetype": "Search + advertising + cloud (GCP)",
        "known_gaps": [],
    },
    "heavy_machinery": {
        "ticker": "CAT",
        "archetype": "Heavy machinery / industrial cyclical",
        "known_gaps": [],
    },
    "pharma_medtech": {
        "ticker": "JNJ",
        "archetype": "Diversified pharma + medical devices",
        "known_gaps": [],
    },
    "managed_care": {
        "ticker": "UNH",
        "archetype": "Managed care / health insurance",
        "known_gaps": [],
    },
    "consumer_staples_beverage": {
        "ticker": "KO",
        "archetype": "Consumer staples — franchise model, asset-light",
        "known_gaps": [],
    },
    "household_products": {
        "ticker": "PG",
        "archetype": "Household / personal care products",
        "known_gaps": [],
    },
    "membership_retail": {
        "ticker": "COST",
        "archetype": "Warehouse / membership retail",
        "known_gaps": [],
    },
    "home_improvement": {
        "ticker": "HD",
        "archetype": "Home improvement big-box retail",
        "known_gaps": [],
    },
    "conglomerate_insurance": {
        "ticker": "BRK-B",
        "archetype": "Diversified conglomerate + P&C insurance",
        "known_gaps": ["sga", "rnd"],
    },
    "payment_network": {
        "ticker": "MA",
        "archetype": "Payment network — toll-road model, no credit risk",
        "known_gaps": [],
    },
    # New tickers — need ingest
    "oil_major": {
        "ticker": "XOM",
        "archetype": "Integrated energy / oil major — commodity cyclicality",
        "known_gaps": ["rnd"],
    },
    "regulated_utility": {
        "ticker": "NEE",
        "archetype": "Regulated utility — rate-of-return, capex-heavy",
        "known_gaps": [],
    },
    "net_lease_reit": {
        "ticker": "O",
        "archetype": "Net-lease REIT — FFO not earnings, pass-through entity",
        "known_gaps": ["roic", "fcf_margin"],
    },
    "fabless_semiconductor": {
        "ticker": "NVDA",
        "archetype": "Fabless semiconductor — R&D intensive, hypergrowth",
        "known_gaps": [],
    },
    "saas_crm": {
        "ticker": "CRM",
        "archetype": "SaaS / cloud pure-play — deferred revenue, high SBC",
        "known_gaps": ["rnd"],
    },
    "ecommerce_cloud": {
        "ticker": "AMZN",
        "archetype": "E-commerce + cloud (AWS) — thin retail, massive reinvestment",
        "known_gaps": [],
    },
    "aerospace_defense": {
        "ticker": "LMT",
        "archetype": "Aerospace / defense — long-cycle gov't contracts, backlog",
        "known_gaps": [],
    },
    "biopharma": {
        "ticker": "LLY",
        "archetype": "Biopharma — R&D as value driver, patent-cliff risk",
        "known_gaps": ["cogs"],
    },
    "streaming_media": {
        "ticker": "NFLX",
        "archetype": "Media / streaming — content capex, subscriber churn",
        "known_gaps": [],
    },
    "qsr_franchise_asset_heavy": {
        "ticker": "MCD",
        "archetype": "QSR franchise + real estate — negative equity, high leverage",
        "known_gaps": ["roic"],
    },
}

ALL_TICKERS: list[str] = [v["ticker"] for v in PHASE1B_COHORT.values()]

# Tickers already piloted — skip in pilot_runner invocation
ALREADY_PILOTED = {"AAPL", "WMT", "MSFT", "JPM", "SBUX"}


def _resolve_cik(ticker: str) -> str | None:
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    return row[0] if row else None


def _check_ingested(tickers: list[str]) -> tuple[list[str], list[str]]:
    """Return (already_ingested, missing) lists."""
    ingested, missing = [], []
    for t in tickers:
        if _resolve_cik(t):
            ingested.append(t)
        else:
            missing.append(t)
    return ingested, missing


def _ingest_missing(tickers: list[str], delay: float = 1.0) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for i, ticker in enumerate(tickers):
        try:
            info = ingest_companyfacts_richer_by_ticker(ticker)
            years = len(info.get("years", []))
            results[ticker] = {"status": "ok", "years": years}
            print(f"  [{i+1}/{len(tickers)}] {ticker}: ingested {years} years")
        except Exception as e:
            results[ticker] = {"status": "error", "error": str(e)}
            print(f"  [{i+1}/{len(tickers)}] {ticker}: FAILED — {e}")
        if i < len(tickers) - 1:
            time.sleep(delay)
    return results


def _archetype_for(ticker: str) -> str:
    for info in PHASE1B_COHORT.values():
        if info["ticker"] == ticker:
            return info["archetype"]
    return "unknown"


def _known_gaps_for(ticker: str) -> list[str]:
    for info in PHASE1B_COHORT.values():
        if info["ticker"] == ticker:
            return info["known_gaps"]
    return []


def _build_report(
    tickers: list[str],
    ingest_results: dict[str, dict],
) -> dict:
    """Build the full preflight report dict."""
    matrix = build_matrix(tickers)
    matrix_by_ticker = {row["ticker"]: row for row in matrix}

    ready: list[str] = []
    not_ready: list[str] = []
    ticker_details: list[dict] = []

    for ticker in tickers:
        row = matrix_by_ticker.get(ticker, {})
        ingest = ingest_results.get(ticker, {"status": "already_present"})
        archetype = _archetype_for(ticker)
        known_gaps = _known_gaps_for(ticker)
        is_piloted = ticker in ALREADY_PILOTED

        if "error" in row:
            status = "not_ingested"
            not_ready.append(ticker)
        else:
            coverage_pct = row.get("pct", 0)
            unexpected_nulls = [f for f in row.get("nulls", []) if f not in known_gaps]
            status = "ready" if coverage_pct >= 50 else "low_coverage"
            if status == "ready":
                ready.append(ticker)
            else:
                not_ready.append(ticker)

        detail: dict = {
            "ticker": ticker,
            "archetype": archetype,
            "known_gaps": known_gaps,
            "ingest_status": ingest.get("status", "already_present"),
            "ingest_years": ingest.get("years"),
            "ingest_error": ingest.get("error"),
            "coverage_pct": row.get("pct"),
            "fields_filled": row.get("filled"),
            "fields_total": row.get("total"),
            "null_fields": row.get("nulls", []),
            "unexpected_nulls": [
                f for f in row.get("nulls", []) if f not in known_gaps
            ] if "nulls" in row else [],
            "preflight_status": status,
            "already_piloted": is_piloted,
            "include_in_pilot": not is_piloted,
        }
        ticker_details.append(detail)

    pilot_tickers = [t for t in tickers if t not in ALREADY_PILOTED]

    return {
        "summary": {
            "total": len(tickers),
            "ready": len(ready),
            "not_ready": len(not_ready),
            "already_piloted": len(ALREADY_PILOTED & set(tickers)),
            "pilot_run_tickers": pilot_tickers,
            "go_no_go": "GO" if not not_ready else "NO_GO",
        },
        "tickers": ticker_details,
    }


def _print_preflight_report(report: dict) -> None:
    summary = report["summary"]
    tickers = report["tickers"]

    print("\n" + "=" * 100)
    print("PHASE 1B PRE-FLIGHT REPORT")
    print("=" * 100)
    print(f"Total companies:    {summary['total']}")
    print(f"Ready for pilot:    {summary['ready']}")
    print(f"Not ready:          {summary['not_ready']}")
    print(f"Already piloted:    {summary['already_piloted']} (will be skipped)")
    print(f"New pilot tickers:  {len(summary['pilot_run_tickers'])}")
    print(f"Decision:           {summary['go_no_go']}")
    print()

    header = (
        f"{'Ticker':<8} {'Archetype':<45} {'Coverage':<12} "
        f"{'Unexpected NULLs':<30} {'Status':<14} {'Pilot?'}"
    )
    print(header)
    print("-" * 115)

    for t in tickers:
        ticker = t["ticker"]
        archetype = t["archetype"][:44]
        cov = f"{t['coverage_pct']:.0f}%" if t["coverage_pct"] is not None else "N/A"
        coverage = f"{t['fields_filled']}/{t['fields_total']} ({cov})" if t["fields_filled"] is not None else "not ingested"
        unexpected = ", ".join(t["unexpected_nulls"][:3]) if t["unexpected_nulls"] else "(none)"
        if len(t["unexpected_nulls"]) > 3:
            unexpected += f" +{len(t['unexpected_nulls'])-3}"
        status = t["preflight_status"]
        pilot = "SKIP (done)" if t["already_piloted"] else "RUN"
        print(f"{ticker:<8} {archetype:<45} {coverage:<22} {unexpected:<30} {status:<14} {pilot}")

    print("=" * 100)

    if summary["not_ready"]:
        not_ready_tickers = [t["ticker"] for t in tickers if t["preflight_status"] in ("not_ingested", "low_coverage")]
        print(f"\nNOT READY: {', '.join(not_ready_tickers)}")
        print("Fix ingestion errors above before running pilot_runner.py")
    else:
        print(f"\nAll {summary['ready']} companies ready.")
        pilot = summary["pilot_run_tickers"]
        print(f"\nRun pilot with:")
        print(f"  cd backend")
        print(f"  python -m app.nlp.research_agent.harness.pilot_runner \\")
        print(f"    --tickers {' '.join(pilot)}")


def main():
    parser = argparse.ArgumentParser(description="Phase 1B pre-flight: ingest + verify 25-company cohort")
    parser.add_argument(
        "--tickers",
        help="Comma-separated subset of tickers (default: full 25-company cohort)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip ingest step — only check existing DB coverage",
    )
    parser.add_argument(
        "--output",
        help="Write full report as JSON to this path",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between SEC API calls (default: 1.0)",
    )
    args = parser.parse_args()

    tickers = (
        [t.strip().upper() for t in args.tickers.split(",")]
        if args.tickers
        else ALL_TICKERS
    )

    print(f"Phase 1B Pre-flight — {len(tickers)} tickers")
    print("=" * 60)

    # Step 1: check what's already ingested
    ingested, missing = _check_ingested(tickers)
    print(f"\nAlready in DB: {len(ingested)}  —  {', '.join(sorted(ingested))}")
    print(f"Need ingest:   {len(missing)}  —  {', '.join(sorted(missing))}")

    ingest_results: dict[str, dict] = {}

    # Step 2: ingest missing tickers
    if missing and not args.skip_ingest:
        print(f"\nIngesting {len(missing)} new tickers (1s delay between SEC calls)...")
        ingest_results = _ingest_missing(missing, delay=args.delay)
    elif missing and args.skip_ingest:
        print(f"\n--skip-ingest set. Skipping ingest for: {', '.join(missing)}")
        for t in missing:
            ingest_results[t] = {"status": "skipped"}
    else:
        print("\nAll tickers already ingested. Skipping ingest step.")

    # Step 3: build coverage matrix and report
    print("\nBuilding coverage matrix...")
    report = _build_report(tickers, ingest_results)

    # Step 4: print report
    _print_preflight_report(report)

    # Step 5: optional JSON output
    if args.output:
        out_path = args.output
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nFull report written to: {out_path}")

    # Exit code
    go = report["summary"]["go_no_go"] == "GO"
    sys.exit(0 if go else 1)


if __name__ == "__main__":
    main()
