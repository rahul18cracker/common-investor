"""
Phase 1D — Step 2: Analyze all ingested stress-test companies.

Runs every metric, valuation, and Four Ms function against each company
and flags anomalies: None values where data should exist, extreme outliers,
and industry-specific problems.

Usage:
    # From backend directory, inside Docker:
    docker compose exec api python -m scripts.stress_test_analyze

    # Save report to file:
    docker compose exec api python -m scripts.stress_test_analyze --output /app/docs/industry-test-results.md

    # Analyze a single ticker:
    docker compose exec api python -m scripts.stress_test_analyze --ticker JPM
"""

import argparse
import json
import sys
import os
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.stress_test_ingest import STRESS_TEST_TICKERS

from app.db.session import execute
from app.metrics.compute import (
    roic_series,
    owner_earnings_series,
    coverage_series,
    compute_growth_metrics,
    compute_growth_metrics_extended,
    gross_margin_series,
    revenue_volatility,
    roic_persistence_score,
    net_debt_series,
    share_count_trend,
    latest_debt_to_equity,
    roic_average,
    margin_stability,
    timeseries_all,
    quality_scores,
)
from app.nlp.fourm.service import (
    compute_moat,
    compute_management,
    compute_balance_sheet_resilience,
    compute_margin_of_safety_recommendation,
)
from app.valuation.service import run_default_scenario


# --- Thresholds for flagging anomalies ---
ANOMALY_THRESHOLDS = {
    "roic_extreme_high": 2.0,     # ROIC > 200% is suspicious
    "roic_extreme_low": -1.0,     # ROIC < -100%
    "de_negative": 0.0,           # Negative D/E = negative equity
    "coverage_extreme": 500.0,    # Coverage > 500x is suspicious
    "moat_score_range": (0.0, 1.0),
    "mgmt_score_range": (0.0, 1.0),
    "bs_score_range": (0.0, 5.0),
    "mos_rec_range": (0.3, 0.7),
}


def resolve_cik(ticker: str) -> str | None:
    """Look up CIK for a ticker."""
    row = execute(
        "SELECT cik FROM company WHERE upper(ticker)=upper(:t)", t=ticker
    ).first()
    return row[0] if row else None


def count_years(cik: str) -> int:
    """Count years of IS data for a company."""
    row = execute(
        "SELECT COUNT(DISTINCT si.fy) FROM statement_is si "
        "JOIN filing f ON si.filing_id=f.id WHERE f.cik=:cik",
        cik=cik,
    ).first()
    return int(row[0]) if row else 0


def check_ingestion_completeness(cik: str) -> dict:
    """Check how many IS/BS/CF fields are populated for the latest year."""
    is_row = execute(
        "SELECT revenue, cogs, gross_profit, sga, rnd, depreciation, ebit, "
        "interest_expense, taxes, net_income, eps_diluted, shares_diluted "
        "FROM statement_is si JOIN filing f ON si.filing_id=f.id "
        "WHERE f.cik=:cik ORDER BY si.fy DESC LIMIT 1",
        cik=cik,
    ).first()

    bs_row = execute(
        "SELECT cash, receivables, inventory, total_assets, total_liabilities, "
        "total_debt, shareholder_equity "
        "FROM statement_bs bs JOIN filing f ON bs.filing_id=f.id "
        "WHERE f.cik=:cik ORDER BY bs.fy DESC LIMIT 1",
        cik=cik,
    ).first()

    cf_row = execute(
        "SELECT cfo, capex, buybacks, dividends, acquisitions "
        "FROM statement_cf cf JOIN filing f ON cf.filing_id=f.id "
        "WHERE f.cik=:cik ORDER BY cf.fy DESC LIMIT 1",
        cik=cik,
    ).first()

    is_fields = ["revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
                 "ebit", "interest_expense", "taxes", "net_income", "eps_diluted",
                 "shares_diluted"]
    bs_fields = ["cash", "receivables", "inventory", "total_assets",
                 "total_liabilities", "total_debt", "shareholder_equity"]
    cf_fields = ["cfo", "capex", "buybacks", "dividends", "acquisitions"]

    def check_row(row, fields):
        if not row:
            return {f: "NO_DATA" for f in fields}
        return {f: ("OK" if row[i] is not None else "NULL") for i, f in enumerate(fields)}

    result = {}
    result.update(check_row(is_row, is_fields))
    result.update(check_row(bs_row, bs_fields))
    result.update(check_row(cf_row, cf_fields))
    return result


def check_negative_equity(cik: str) -> list[int]:
    """Return fiscal years with negative shareholder equity."""
    rows = execute(
        "SELECT bs.fy, bs.shareholder_equity "
        "FROM statement_bs bs JOIN filing f ON bs.filing_id=f.id "
        "WHERE f.cik=:cik AND bs.shareholder_equity IS NOT NULL "
        "ORDER BY bs.fy ASC",
        cik=cik,
    ).fetchall()
    return [int(r[0]) for r in rows if r[1] is not None and float(r[1]) < 0]


def analyze_company(ticker: str, cik: str) -> dict:
    """Run all analyses on a single company and collect findings."""
    findings = {
        "ticker": ticker,
        "cik": cik,
        "years_of_data": count_years(cik),
        "issues": [],
        "warnings": [],
        "metrics": {},
    }

    # 1. Ingestion completeness
    completeness = check_ingestion_completeness(cik)
    null_fields = [f for f, v in completeness.items() if v == "NULL"]
    no_data_fields = [f for f, v in completeness.items() if v == "NO_DATA"]
    findings["ingestion"] = {
        "populated": len([v for v in completeness.values() if v == "OK"]),
        "null_fields": null_fields,
        "no_data": no_data_fields,
        "total_fields": len(completeness),
    }
    if no_data_fields:
        findings["issues"].append(f"No data rows for: {no_data_fields}")
    if null_fields:
        findings["warnings"].append(f"NULL in latest year: {null_fields}")

    # 2. Negative equity check
    neg_eq_years = check_negative_equity(cik)
    findings["negative_equity_years"] = neg_eq_years
    if neg_eq_years:
        findings["issues"].append(f"Negative equity in years: {neg_eq_years}")

    # 3. ROIC series
    try:
        roics = roic_series(cik)
        roic_vals = [x["roic"] for x in roics if x["roic"] is not None]
        findings["metrics"]["roic_count"] = len(roic_vals)
        if roic_vals:
            findings["metrics"]["roic_min"] = min(roic_vals)
            findings["metrics"]["roic_max"] = max(roic_vals)
            findings["metrics"]["roic_avg"] = sum(roic_vals) / len(roic_vals)
            if max(roic_vals) > ANOMALY_THRESHOLDS["roic_extreme_high"]:
                findings["issues"].append(
                    f"ROIC extreme high: {max(roic_vals):.2%} (>200%)")
            if min(roic_vals) < ANOMALY_THRESHOLDS["roic_extreme_low"]:
                findings["issues"].append(
                    f"ROIC extreme low: {min(roic_vals):.2%} (<-100%)")
    except Exception as e:
        findings["issues"].append(f"ROIC series failed: {e}")

    # 4. Growth metrics
    try:
        growth = compute_growth_metrics(cik)
        findings["metrics"]["growth"] = growth
        # Check the zero-growth-as-falsy bug
        for key, val in growth.items():
            if val == 0.0:
                findings["warnings"].append(
                    f"Growth metric {key} = 0.0 (will be treated as None by or-chain bug)")
    except Exception as e:
        findings["issues"].append(f"Growth metrics failed: {e}")

    # 5. Debt/Equity
    try:
        de = latest_debt_to_equity(cik)
        findings["metrics"]["debt_to_equity"] = de
        if de is not None and de < 0:
            findings["issues"].append(f"Negative D/E ratio: {de:.2f} (negative equity)")
    except Exception as e:
        findings["issues"].append(f"D/E ratio failed: {e}")

    # 6. Coverage
    try:
        cov = coverage_series(cik)
        cov_vals = [x["coverage"] for x in cov if x["coverage"] is not None]
        if cov_vals:
            findings["metrics"]["coverage_latest"] = cov_vals[-1]
            if abs(cov_vals[-1]) > ANOMALY_THRESHOLDS["coverage_extreme"]:
                findings["warnings"].append(
                    f"Extreme coverage ratio: {cov_vals[-1]:.1f}x")
    except Exception as e:
        findings["issues"].append(f"Coverage series failed: {e}")

    # 7. Owner earnings
    try:
        oe = owner_earnings_series(cik)
        oe_vals = [x["owner_earnings"] for x in oe if x["owner_earnings"] is not None]
        if oe_vals:
            findings["metrics"]["owner_earnings_latest"] = oe_vals[-1]
            findings["metrics"]["owner_earnings_positive"] = all(v > 0 for v in oe_vals)
    except Exception as e:
        findings["issues"].append(f"Owner earnings failed: {e}")

    # 8. Gross margin
    try:
        gm = gross_margin_series(cik)
        gm_vals = [x["gross_margin"] for x in gm if x["gross_margin"] is not None]
        if gm_vals:
            findings["metrics"]["gross_margin_latest"] = gm_vals[-1]
        else:
            findings["warnings"].append("No gross margin data available")
    except Exception as e:
        findings["issues"].append(f"Gross margin failed: {e}")

    # 9. Four Ms scoring
    try:
        moat = compute_moat(cik)
        findings["metrics"]["moat_score"] = moat.get("score")
        if moat.get("score") is not None:
            lo, hi = ANOMALY_THRESHOLDS["moat_score_range"]
            if not (lo <= moat["score"] <= hi):
                findings["issues"].append(
                    f"Moat score out of range: {moat['score']:.3f}")
    except Exception as e:
        findings["issues"].append(f"Moat scoring failed: {e}")

    try:
        mgmt = compute_management(cik)
        findings["metrics"]["mgmt_score"] = mgmt.get("score")
        if mgmt.get("score") is not None:
            lo, hi = ANOMALY_THRESHOLDS["mgmt_score_range"]
            if not (lo <= mgmt["score"] <= hi):
                findings["issues"].append(
                    f"Management score out of range: {mgmt['score']:.3f}")
    except Exception as e:
        findings["issues"].append(f"Management scoring failed: {e}")

    try:
        bs = compute_balance_sheet_resilience(cik)
        findings["metrics"]["bs_resilience_score"] = bs.get("score")
        if bs.get("score") is not None:
            lo, hi = ANOMALY_THRESHOLDS["bs_score_range"]
            if not (lo <= bs["score"] <= hi):
                findings["issues"].append(
                    f"Balance sheet score out of range: {bs['score']:.3f}")
    except Exception as e:
        findings["issues"].append(f"Balance sheet scoring failed: {e}")

    try:
        mos = compute_margin_of_safety_recommendation(cik)
        findings["metrics"]["mos_recommended"] = mos.get("recommended_mos")
        if mos.get("recommended_mos") is not None:
            lo, hi = ANOMALY_THRESHOLDS["mos_rec_range"]
            if not (lo <= mos["recommended_mos"] <= hi):
                findings["issues"].append(
                    f"MOS recommendation out of range: {mos['recommended_mos']:.3f}")
    except Exception as e:
        findings["issues"].append(f"MOS recommendation failed: {e}")

    # 10. Valuation
    try:
        val = run_default_scenario(ticker)
        findings["metrics"]["sticker_price"] = val["results"]["sticker"]
        findings["metrics"]["mos_price"] = val["results"]["mos_price"]
        findings["metrics"]["ten_cap"] = val["results"]["ten_cap_price"]
        findings["metrics"]["payback_years"] = val["results"]["payback_years"]
        findings["metrics"]["growth_used"] = val["inputs"]["g"]
    except ValueError as e:
        findings["warnings"].append(f"Valuation skipped: {e}")
    except Exception as e:
        findings["issues"].append(f"Valuation failed: {e}")

    return findings


def format_report(all_findings: dict) -> str:
    """Generate markdown report from findings."""
    lines = [
        "# Phase 1D: Multi-Industry Stress Test Results",
        "",
        "> Auto-generated by `scripts/stress_test_analyze.py`",
        "",
        "---",
        "",
    ]

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Industry | Ticker | Years | Issues | Warnings | ROIC Avg | D/E | Moat | Valuation |")
    lines.append("|----------|--------|-------|--------|----------|----------|-----|------|-----------|")

    for category, info in STRESS_TEST_TICKERS.items():
        for ticker in info["tickers"]:
            f = all_findings.get(ticker)
            if not f:
                lines.append(f"| {category} | {ticker} | - | NOT INGESTED | - | - | - | - | - |")
                continue

            roic_avg = f["metrics"].get("roic_avg")
            roic_str = f"{roic_avg:.1%}" if roic_avg is not None else "N/A"
            de = f["metrics"].get("debt_to_equity")
            de_str = f"{de:.2f}" if de is not None else "N/A"
            moat = f["metrics"].get("moat_score")
            moat_str = f"{moat:.2f}" if moat is not None else "N/A"
            sticker = f["metrics"].get("sticker_price")
            val_str = f"${sticker:,.0f}" if sticker is not None else "N/A"

            issue_count = len(f["issues"])
            warn_count = len(f["warnings"])
            issue_marker = f"**{issue_count}**" if issue_count > 0 else "0"
            warn_marker = f"{warn_count}" if warn_count > 0 else "0"

            lines.append(
                f"| {category} | {ticker} | {f['years_of_data']} | "
                f"{issue_marker} | {warn_marker} | {roic_str} | {de_str} | "
                f"{moat_str} | {val_str} |"
            )

    # Detailed findings per category
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Findings by Industry")
    lines.append("")

    for category, info in STRESS_TEST_TICKERS.items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append(f"**Expected:** {info['expect']}")
        lines.append("")

        for ticker in info["tickers"]:
            f = all_findings.get(ticker)
            if not f:
                lines.append(f"#### {ticker} — NOT INGESTED")
                lines.append("")
                continue

            lines.append(f"#### {ticker}")
            lines.append(f"- Years of data: {f['years_of_data']}")

            # Ingestion
            ing = f["ingestion"]
            lines.append(f"- Fields populated: {ing['populated']}/{ing['total_fields']}")
            if ing["null_fields"]:
                lines.append(f"- Missing fields: {', '.join(ing['null_fields'])}")

            # Negative equity
            if f["negative_equity_years"]:
                lines.append(f"- **NEGATIVE EQUITY** in years: {f['negative_equity_years']}")

            # Key metrics
            m = f["metrics"]
            if "roic_avg" in m:
                lines.append(f"- ROIC: avg={m.get('roic_avg', 'N/A'):.1%}, "
                            f"min={m.get('roic_min', 'N/A'):.1%}, "
                            f"max={m.get('roic_max', 'N/A'):.1%}")
            if "debt_to_equity" in m and m["debt_to_equity"] is not None:
                lines.append(f"- Debt/Equity: {m['debt_to_equity']:.2f}")
            if "moat_score" in m and m["moat_score"] is not None:
                lines.append(f"- Moat score: {m['moat_score']:.3f}")
            if "sticker_price" in m:
                lines.append(f"- Sticker: ${m['sticker_price']:,.2f}, "
                            f"MOS: ${m.get('mos_price', 0):,.2f}")
            if "growth_used" in m:
                lines.append(f"- Growth rate used: {m['growth_used']:.1%}")

            # Issues
            if f["issues"]:
                lines.append("")
                lines.append("**Issues:**")
                for issue in f["issues"]:
                    lines.append(f"- {issue}")

            # Warnings
            if f["warnings"]:
                lines.append("")
                lines.append("**Warnings:**")
                for warn in f["warnings"]:
                    lines.append(f"- {warn}")

            lines.append("")

    # Conclusions
    lines.append("---")
    lines.append("")
    lines.append("## Bug Confirmation")
    lines.append("")
    lines.append("### BUG-1: Zero Growth as Falsy")
    zero_growth_tickers = []
    for ticker, f in all_findings.items():
        for w in f.get("warnings", []):
            if "or-chain bug" in w:
                zero_growth_tickers.append(ticker)
                break
    if zero_growth_tickers:
        lines.append(f"**CONFIRMED** for: {', '.join(zero_growth_tickers)}")
    else:
        lines.append("Not triggered in this run (no companies had exactly 0.0 growth)")

    lines.append("")
    lines.append("### BUG-3: Negative Equity")
    neg_eq_tickers = [t for t, f in all_findings.items() if f.get("negative_equity_years")]
    if neg_eq_tickers:
        lines.append(f"**CONFIRMED** for: {', '.join(neg_eq_tickers)}")
        for t in neg_eq_tickers:
            f = all_findings[t]
            roic_max = f["metrics"].get("roic_max")
            if roic_max and roic_max > 1.0:
                lines.append(f"- {t}: ROIC max = {roic_max:.1%} (inflated by negative equity)")
    else:
        lines.append("Not triggered (no negative equity companies ingested yet)")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append("Based on findings above, proceed to Phase 1A (Data Correctness) to fix confirmed bugs.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Phase 1D: Analyze stress test companies")
    parser.add_argument("--ticker", type=str, default=None,
                        help="Analyze a single ticker instead of all")
    parser.add_argument("--output", type=str, default=None,
                        help="Write markdown report to file")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON findings instead of markdown")
    args = parser.parse_args()

    # Determine which tickers to analyze
    if args.ticker:
        tickers_to_analyze = [args.ticker.upper()]
    else:
        tickers_to_analyze = []
        for info in STRESS_TEST_TICKERS.values():
            tickers_to_analyze.extend(info["tickers"])

    print(f"Analyzing {len(tickers_to_analyze)} companies...\n")

    all_findings = {}
    for ticker in tickers_to_analyze:
        cik = resolve_cik(ticker)
        if not cik:
            print(f"  {ticker}: NOT FOUND in DB (skipping)")
            continue

        print(f"  {ticker} (CIK {cik})...", end=" ", flush=True)
        findings = analyze_company(ticker, cik)
        all_findings[ticker] = findings

        issue_count = len(findings["issues"])
        warn_count = len(findings["warnings"])
        status = "OK" if issue_count == 0 else f"{issue_count} ISSUES"
        if warn_count > 0:
            status += f", {warn_count} warnings"
        print(status)

    # Output results
    if args.json:
        # Make findings JSON-serializable
        print(json.dumps(all_findings, indent=2, default=str))
    else:
        report = format_report(all_findings)
        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"\nReport written to {args.output}")
        else:
            print("\n" + report)

    # Exit summary
    total_issues = sum(len(f["issues"]) for f in all_findings.values())
    total_warnings = sum(len(f["warnings"]) for f in all_findings.values())
    print(f"\n{'='*60}")
    print(f"  Total: {len(all_findings)} companies analyzed")
    print(f"  Issues: {total_issues}  |  Warnings: {total_warnings}")
    print(f"{'='*60}")

    if total_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
