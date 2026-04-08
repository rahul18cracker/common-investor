#!/usr/bin/env python3
"""
Metrics Snapshot — compute all metrics for a ticker and dump as JSON.

Runs the full analysis pipeline (growth, ROIC, valuation, Four Ms, quality
scores) against a single company and outputs structured JSON. Useful for
eyeball-checking a specific company's numbers or feeding into Claude for
triage.

Usage:
    cd backend
    python -m scripts.workflows.metrics_snapshot MSFT
    python -m scripts.workflows.metrics_snapshot MSFT --output msft_snapshot.json
    python -m scripts.workflows.metrics_snapshot MSFT --ingest   # ingest first
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import execute
from scripts.workflows.cohort import industry_for_ticker


def resolve_cik(ticker: str) -> str | None:
    row = execute("SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker).first()
    return row[0] if row else None


def snapshot(ticker: str) -> dict:
    """Build full metrics snapshot for a ticker."""
    cik = resolve_cik(ticker)
    if not cik:
        return {"ticker": ticker, "error": "not_ingested"}

    result = {"ticker": ticker, "cik": cik, "industry": industry_for_ticker(ticker)}

    # Growth metrics
    try:
        from app.metrics.compute import compute_growth_metrics
        result["growth"] = compute_growth_metrics(cik)
    except Exception as e:
        result["growth"] = {"error": str(e)}

    # Extended growth
    try:
        from app.metrics.compute import compute_growth_metrics_extended
        result["growth_extended"] = compute_growth_metrics_extended(cik)
    except Exception as e:
        result["growth_extended"] = {"error": str(e)}

    # ROIC
    try:
        from app.metrics.compute import roic_series, roic_average
        series = roic_series(cik)
        result["roic_series"] = series
        result["roic_avg"] = roic_average(cik)
    except Exception as e:
        result["roic_series"] = {"error": str(e)}

    # Owner earnings
    try:
        from app.metrics.compute import owner_earnings_series
        result["owner_earnings"] = owner_earnings_series(cik)
    except Exception as e:
        result["owner_earnings"] = {"error": str(e)}

    # Coverage
    try:
        from app.metrics.compute import coverage_series
        result["coverage"] = coverage_series(cik)
    except Exception as e:
        result["coverage"] = {"error": str(e)}

    # Debt/Equity
    try:
        from app.metrics.compute import latest_debt_to_equity
        result["debt_to_equity"] = latest_debt_to_equity(cik)
    except Exception as e:
        result["debt_to_equity"] = {"error": str(e)}

    # Quality scores
    try:
        from app.metrics.compute import quality_scores
        result["quality_scores"] = quality_scores(cik)
    except Exception as e:
        result["quality_scores"] = {"error": str(e)}

    # Valuation
    try:
        from app.valuation.service import run_default_scenario
        result["valuation"] = run_default_scenario(ticker)
    except Exception as e:
        result["valuation"] = {"error": str(e)}

    # Four Ms
    try:
        from app.nlp.fourm.service import (
            compute_moat, compute_management,
            compute_balance_sheet_resilience,
            compute_margin_of_safety_recommendation,
        )
        moat = compute_moat(cik)
        mgmt = compute_management(cik)
        bs = compute_balance_sheet_resilience(cik)
        result["four_ms"] = {
            "moat": moat,
            "management": mgmt,
            "balance_sheet": bs,
        }
        if moat and mgmt and bs:
            mos = compute_margin_of_safety_recommendation(
                moat_score=moat.get("score"),
                mgmt_score=mgmt.get("score"),
                bs_score=bs.get("score"),
                growth=result.get("growth", {}),
            )
            result["four_ms"]["mos_recommendation"] = mos
    except Exception as e:
        result["four_ms"] = {"error": str(e)}

    # Flag anomalies for quick scanning
    result["anomalies"] = _detect_anomalies(result)

    return result


def _detect_anomalies(snap: dict) -> list[dict]:
    """Flag suspicious values for triage."""
    anomalies = []

    # ROIC extremes
    roic_avg = snap.get("roic_avg")
    if roic_avg is not None:
        if roic_avg > 2.0:
            anomalies.append({"field": "roic_avg", "issue": f"Extreme ROIC: {roic_avg:.0%}"})
        elif roic_avg < -1.0:
            anomalies.append({"field": "roic_avg", "issue": f"Very negative ROIC: {roic_avg:.0%}"})

    # D/E
    de = snap.get("debt_to_equity")
    if de is not None and de < 0:
        anomalies.append({"field": "debt_to_equity", "issue": f"Negative D/E: {de:.2f} (negative equity)"})

    # Valuation errors
    val = snap.get("valuation", {})
    if isinstance(val, dict) and "error" in val:
        anomalies.append({"field": "valuation", "issue": val["error"]})

    # Four Ms score ranges
    four_ms = snap.get("four_ms", {})
    for key in ("moat", "management"):
        score_data = four_ms.get(key, {})
        if isinstance(score_data, dict):
            score = score_data.get("score")
            if score is not None and (score < 0 or score > 1):
                anomalies.append({"field": f"four_ms.{key}", "issue": f"Out of [0,1] range: {score}"})

    bs_data = four_ms.get("balance_sheet", {})
    if isinstance(bs_data, dict):
        score = bs_data.get("score")
        if score is not None and (score < 0 or score > 5):
            anomalies.append({"field": "four_ms.balance_sheet", "issue": f"Out of [0,5] range: {score}"})

    return anomalies


def print_summary(snap: dict):
    """Print human-readable summary."""
    ticker = snap["ticker"]
    industry = snap.get("industry", "unknown")

    if "error" in snap:
        print(f"{ticker}: {snap['error']}")
        return

    print(f"\n{ticker} ({industry})")
    print("=" * 60)

    # Growth
    growth = snap.get("growth", {})
    if not isinstance(growth, dict) or "error" in growth:
        print(f"  Growth: ERROR")
    else:
        for k in ["eps_cagr_5y", "rev_cagr_5y", "eps_cagr_10y", "rev_cagr_10y"]:
            v = growth.get(k)
            print(f"  {k}: {v:.1%}" if v is not None else f"  {k}: None")

    # ROIC
    print(f"  ROIC avg: {snap.get('roic_avg')}")
    print(f"  D/E: {snap.get('debt_to_equity')}")

    # Valuation
    val = snap.get("valuation", {})
    if isinstance(val, dict) and "results" in val:
        r = val["results"]
        print(f"  Sticker: ${r.get('sticker', '?'):,.0f}" if r.get("sticker") else "  Sticker: None")
        print(f"  MOS: ${r.get('mos_price', '?'):,.0f}" if r.get("mos_price") else "  MOS: None")

    # Anomalies
    anomalies = snap.get("anomalies", [])
    if anomalies:
        print(f"\n  ANOMALIES ({len(anomalies)}):")
        for a in anomalies:
            print(f"    - {a['field']}: {a['issue']}")
    else:
        print(f"\n  No anomalies detected.")


def main():
    parser = argparse.ArgumentParser(description="Full metrics snapshot for a ticker")
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument("--ingest", action="store_true", help="Ingest from SEC before snapshot")
    parser.add_argument("--output", help="Write JSON to file")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    if args.ingest:
        print(f"Ingesting {ticker}...")
        from app.ingest.sec import ingest_companyfacts_richer_by_ticker
        ingest_companyfacts_richer_by_ticker(ticker)

    snap = snapshot(ticker)
    print_summary(snap)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(snap, f, indent=2, default=str)
        print(f"\nJSON written to {args.output}")

    return 1 if snap.get("anomalies") else 0


if __name__ == "__main__":
    sys.exit(main())
