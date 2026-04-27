#!/usr/bin/env python3
"""Integration test: run the harness on AAPL for sprint 01 (business_profile).

Usage:
    cd backend
    python -m app.nlp.research_agent.harness.run_aapl

Requires ANTHROPIC_API_KEY in the root .env or environment.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load .env from project root
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[5]
load_dotenv(project_root / ".env")

from app.nlp.research_agent.harness.llm_client import AnthropicLLMClient
from app.nlp.research_agent.harness.orchestrator import run_all_sprints

# --- Sample data (cached agent-bundle for AAPL) ---
# In production this comes from the /agent-bundle API endpoint.
# For this integration test we use a representative snapshot.

AAPL_AGENT_BUNDLE = {
    "company": {
        "cik": "0000320193",
        "ticker": "AAPL",
        "name": "Apple Inc",
        "sic_code": 3571,
        "sic_description": "ELECTRONIC COMPUTERS",
        "industry_category": "technology",
        "industry_notes": [
            "SaaS/cloud metrics (ARR, NRR, RPO) may not apply to hardware-centric revenue",
            "Consider R&D capitalization and amortization patterns",
        ],
        "fiscal_year_end_month": 9,
    },
    "metrics": {
        "growths": {
            "revenue_cagr": 0.08,
            "eps_cagr": 0.11,
        },
        "growths_extended": {
            "rev_cagr_1y": 0.02,
            "rev_cagr_3y": 0.06,
            "rev_cagr_5y": 0.08,
            "rev_cagr_10y": 0.11,
            "eps_cagr_1y": 0.09,
            "eps_cagr_3y": 0.08,
            "eps_cagr_5y": 0.11,
            "eps_cagr_10y": 0.16,
        },
        "roic_avg_10y": 0.34,
        "debt_to_equity": 1.73,
        "fcf_growth": 0.07,
        "revenue_volatility": 0.08,
        "roic_persistence_score": 5,
        "latest_operating_margin": 0.30,
        "latest_fcf_margin": 0.26,
        "latest_cash_conversion": 1.05,
        "roe_avg": 1.47,
    },
    "quality_scores": {
        "gross_margin_trend": "stable",
        "share_dilution": "buyback",
        "roic_persistence": 5,
        "net_debt_trend": "stable",
    },
    "four_ms": {
        "moat": {"score": 0.82, "components": {}},
        "management": {"score": 0.71, "components": {}},
        "balance_sheet_resilience": {"score": 3.5},
        "mos_recommendation": {"recommended_mos_pct": 0.40},
    },
    "timeseries": {
        "is": [
            {"fiscal_year": 2019, "revenue": 260174000000, "eps": 2.97},
            {"fiscal_year": 2020, "revenue": 274515000000, "eps": 3.28},
            {"fiscal_year": 2021, "revenue": 365817000000, "eps": 5.61},
            {"fiscal_year": 2022, "revenue": 394328000000, "eps": 6.11},
            {"fiscal_year": 2023, "revenue": 383285000000, "eps": 6.13},
            {"fiscal_year": 2024, "revenue": 391035000000, "eps": 6.75},
        ],
    },
}

AAPL_ITEM1_TEXT = """
Apple Inc. designs, manufactures, and markets smartphones, personal computers,
tablets, wearables, and accessories worldwide. The Company also sells various
related services. The Company's products include iPhone, Mac, iPad, and Wearables,
Home and Accessories. iPhone is the Company's line of smartphones based on its iOS
operating system. Mac is the Company's line of personal computers based on its
macOS operating system. iPad is the Company's line of multi-purpose tablets based
on its iPadOS operating system. Wearables, Home and Accessories includes AirPods,
Apple TV, Apple Watch, Beats products, and HomePod.

The Company's Services include advertising, AppleCare, cloud services, digital
content, and payment services. The Company distributes its products through its
retail and online stores, and its direct sales force, as well as through third-party
cellular network carriers, wholesalers, retailers, and resellers. The Company sells
and delivers digital content and applications through the App Store, TV+ app,
Apple Arcade, Apple News+, Apple Fitness+, and Apple Music.

The Company's customers are primarily in the consumer, small and mid-sized business,
and education, enterprise and government markets. The Company sells its products and
resells third-party products in most of its major markets directly to consumers,
small and mid-sized businesses, and education, enterprise and government customers
through its retail and online stores and its direct sales force.

The Company's fiscal year is the 52- or 53-week period that ends on the last
Saturday of September.
""".strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to the root .env file.")
        sys.exit(1)

    print("=" * 60)
    print("Qualitative Agent Harness — AAPL Integration Test")
    print("Sprint: 01_business_profile")
    print("Model: Haiku 4.5")
    print("=" * 60)

    builder_llm = AnthropicLLMClient(model="haiku", api_key=api_key)
    evaluator_llm = AnthropicLLMClient(model="haiku", api_key=api_key)

    state_root = Path(__file__).parent / "state"
    print(f"\nState directory: {state_root / 'AAPL'}")
    print("Running...\n")

    manifest = run_all_sprints(
        ticker="AAPL",
        agent_bundle=AAPL_AGENT_BUNDLE,
        item1_text=AAPL_ITEM1_TEXT,
        builder_llm=builder_llm,
        evaluator_llm=evaluator_llm,
        state_root=state_root,
        sprint_names=["01_business_profile"],
    )

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(json.dumps(manifest, indent=2, default=str))

    sprint = manifest.get("sprints", {}).get("01_business_profile", {})
    status = sprint.get("status", "unknown")
    score = sprint.get("eval_score", 0)
    attempts = sprint.get("attempts", 0)
    cost = manifest.get("total_cost_usd", 0)

    print(f"\nStatus: {status}")
    print(f"Eval score: {score}/20")
    print(f"Attempts: {attempts}")
    print(f"Cost: ${cost:.4f}")

    # Print the actual builder output
    output_path = state_root / "AAPL" / "sprints" / "01_business_profile" / "builder_output.json"
    if output_path.exists():
        print("\n" + "=" * 60)
        print("BUILDER OUTPUT (business_profile.json)")
        print("=" * 60)
        print(output_path.read_text())

    eval_path = state_root / "AAPL" / "sprints" / "01_business_profile" / "eval_result.json"
    if eval_path.exists():
        print("\n" + "=" * 60)
        print("EVAL RESULT")
        print("=" * 60)
        print(eval_path.read_text())


if __name__ == "__main__":
    main()
