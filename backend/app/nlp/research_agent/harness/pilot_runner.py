#!/usr/bin/env python3
"""Pilot runner for the qualitative agent harness.

Run the full qualitative agent pipeline on a cohort of 5 companies and collect
metrics into a CSV for calibration and evaluation.

Usage:
    cd backend
    python -m app.nlp.research_agent.harness.pilot_runner [--tickers AAPL WMT MSFT JPM SBUX] [--base-url URL]

Default mode: fetches live data from the API for each ticker sequentially.

Requires ANTHROPIC_API_KEY in the root .env or environment.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Load .env from project root
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[5]
load_dotenv(project_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_TICKERS = ["AAPL", "WMT", "MSFT", "JPM", "SBUX"]


def _get_industry(agent_bundle: dict[str, Any]) -> str:
    try:
        value = agent_bundle.get("company", {}).get("industry_category")
        return value if value else "unknown"
    except Exception:
        return "unknown"


def _collect_sprint_metrics(manifest: dict[str, Any]) -> tuple[int, int, int, int, float, int]:
    sprints = manifest.get("sprints", {})

    passed_count = 0
    degraded_count = 0
    data_incomplete_count = 0
    tainted_count = 0
    eval_scores = []
    grounding_contradictions = 0

    for sprint_name, sprint_data in sprints.items():
        status = sprint_data.get("status", "unknown")

        if status == "passed":
            passed_count += 1
            score = sprint_data.get("eval_score", 0)
            eval_scores.append(score)
        elif status == "degraded":
            degraded_count += 1
            score = sprint_data.get("eval_score", 0)
            eval_scores.append(score)
        elif status == "data_incomplete":
            data_incomplete_count += 1
        elif status in ("tainted_blocked", "tainted_suspicious"):
            tainted_count += 1

        grounding_contradictions += sprint_data.get("grounding_contradictions", 0)

    evidence_quality_avg = 0.0
    if eval_scores:
        evidence_quality_avg = sum(eval_scores) / len(eval_scores)

    return (
        passed_count,
        degraded_count,
        data_incomplete_count,
        tainted_count,
        round(evidence_quality_avg, 1),
        grounding_contradictions,
    )


def _build_csv_row(
    ticker: str,
    industry: str,
    manifest: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ticker": ticker,
        "industry": industry,
    }

    # If error or manifest is None, populate with default error values
    if error or manifest is None:
        row["status"] = error if error else "error"
        row["total_cost"] = 0.0
        row["duration_min"] = 0.0
        row["sprints_passed"] = 0
        row["sprints_degraded"] = 0
        row["sprints_data_incomplete"] = 0
        row["sprints_tainted"] = 0
        row["evidence_quality_avg"] = 0.0
        row["grounding_contradictions"] = 0
        row["cache_hit_rate"] = 0.0
        return row

    row["status"] = manifest.get("status", "unknown")
    row["total_cost"] = round(manifest.get("total_cost_usd", 0.0), 4)
    duration_sec = manifest.get("total_duration_seconds", 0)
    row["duration_min"] = round(duration_sec / 60, 2) if duration_sec else 0.0

    (
        passed,
        degraded,
        data_incomplete,
        tainted,
        quality_avg,
        grounding,
    ) = _collect_sprint_metrics(manifest)

    row["sprints_passed"] = passed
    row["sprints_degraded"] = degraded
    row["sprints_data_incomplete"] = data_incomplete
    row["sprints_tainted"] = tainted
    row["evidence_quality_avg"] = quality_avg
    row["grounding_contradictions"] = grounding
    # placeholder — cache metrics not available from manifest
    row["cache_hit_rate"] = 0.0

    return row


def _write_csv_row(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    """Write all rows to CSV, creating header only on first write."""
    if not rows:
        return

    fieldnames = [
        "ticker",
        "industry",
        "status",
        "total_cost",
        "duration_min",
        "sprints_passed",
        "sprints_degraded",
        "sprints_data_incomplete",
        "sprints_tainted",
        "evidence_quality_avg",
        "grounding_contradictions",
        "cache_hit_rate",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_summary_table(rows: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 120)
    print("PILOT CALIBRATION SUMMARY")
    print("=" * 120)

    header = (
        f"{'Ticker':<8} {'Industry':<15} {'Status':<18} {'Cost':<8} "
        f"{'Duration (min)':<15} {'Passed':<7} {'Degraded':<10} {'Quality':<8} {'Groundings':<12}"
    )
    print(header)
    print("-" * 120)

    for row in rows:
        ticker = row.get("ticker", "?")
        industry = row.get("industry", "?")[:14]
        status = row.get("status", "?")[:17]
        cost = f"${row.get('total_cost', 0.0):.4f}"
        duration = f"{row.get('duration_min', 0.0):.2f}"
        passed = str(row.get("sprints_passed", 0))
        degraded = str(row.get("sprints_degraded", 0))
        quality = f"{row.get('evidence_quality_avg', 0.0):.1f}"
        groundings = str(row.get("grounding_contradictions", 0))

        line = (
            f"{ticker:<8} {industry:<15} {status:<18} {cost:<8} "
            f"{duration:<15} {passed:<7} {degraded:<10} {quality:<8} {groundings:<12}"
        )
        print(line)

    print("=" * 120)


def main():
    parser = argparse.ArgumentParser(description="Pilot calibration runner for qualitative agent harness")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080/api/v1",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
    )

    args = parser.parse_args()

    # Validate --snapshot with multiple tickers
    if args.snapshot and len(args.tickers) > 1:
        print(
            "ERROR: --snapshot mode is not practical with multiple tickers. "
            "Snapshot can only be used with a single ticker."
        )
        sys.exit(1)

    from app.nlp.research_agent.harness.llm_client import AnthropicLLMClient
    from app.nlp.research_agent.harness.orchestrator import run_all_sprints

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to the root .env file.")
        sys.exit(1)

    print("=" * 60)
    print("Pilot Calibration Runner")
    print(f"Tickers: {', '.join(args.tickers)}")
    print(f"Base URL: {args.base_url}")
    print("=" * 60)

    builder_llm = AnthropicLLMClient(model="haiku", api_key=api_key)
    evaluator_llm = AnthropicLLMClient(model="haiku", api_key=api_key)

    state_root = Path(__file__).parent / "state"
    print(f"\nState directory: {state_root}")

    rows = []
    csv_path = state_root / "pilot_metrics.csv"

    for ticker in args.tickers:
        print(f"\n{'=' * 60}")
        print(f"Processing: {ticker}")
        print("=" * 60)

        ticker_upper = ticker.upper()
        industry = "unknown"
        manifest = None

        try:
            logger.info("Running all sprints for %s...", ticker_upper)
            manifest = run_all_sprints(
                ticker=ticker_upper,
                builder_llm=builder_llm,
                evaluator_llm=evaluator_llm,
                state_root=state_root,
                base_url=args.base_url,
            )

            # Read industry from on-disk agent_bundle
            state_dir = state_root / ticker_upper
            agent_bundle_path = state_dir / "agent_bundle.json"
            if agent_bundle_path.exists():
                try:
                    agent_bundle = json.loads(agent_bundle_path.read_text(encoding="utf-8"))
                    industry = _get_industry(agent_bundle)
                except Exception as e:
                    logger.warning("Could not extract industry for %s: %s", ticker_upper, e)
                    industry = "unknown"

            if manifest and manifest.get("status") == "fetch_failed":
                logger.error("Fetch failed for %s", ticker_upper)
                row = _build_csv_row(ticker_upper, industry, error="fetch_failed")
            else:
                row = _build_csv_row(ticker_upper, industry, manifest)

            rows.append(row)

            # Print per-ticker summary
            if manifest:
                status = manifest.get("status", "unknown")
                cost = manifest.get("total_cost_usd", 0.0)
                duration = manifest.get("total_duration_seconds", 0)
                print(f"\n{ticker_upper} Result:")
                print(f"  Status: {status}")
                print(f"  Cost: ${cost:.4f}")
                print(f"  Duration: {duration / 60:.2f} min")

                sprints = manifest.get("sprints", {})
                passed = sum(1 for s in sprints.values() if s.get("status") == "passed")
                degraded = sum(1 for s in sprints.values() if s.get("status") == "degraded")
                print(f"  Sprints: {passed} passed, {degraded} degraded")

        except Exception as e:
            logger.exception("Exception while processing %s: %s", ticker_upper, e)
            row = _build_csv_row(ticker_upper, industry, error="exception")
            rows.append(row)
            print(f"\n{ticker_upper} ERROR: {e}")

        # Write CSV after each ticker completes
        _write_csv_row(csv_path, rows)
        logger.info("Updated CSV: %s (%d rows)", csv_path, len(rows))

    # Print final summary table
    _print_summary_table(rows)
    print(f"\nFinal CSV written to: {csv_path}")


if __name__ == "__main__":
    main()
