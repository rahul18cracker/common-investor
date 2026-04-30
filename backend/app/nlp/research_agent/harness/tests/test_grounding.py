"""Tests for the grounding module — deterministic claim verification."""

import pytest

from app.nlp.research_agent.harness.grounding import (
    extract_numeric_claims,
    has_claim_signal,
    has_negated_claim,
    has_revenue_data,
    resolve_path,
    run_all_grounding_checks,
    run_grounding_check,
)

# --- resolve_path ---


class TestResolvePath:
    def test_single_key(self):
        assert resolve_path({"a": 1}, "a") == 1

    def test_nested(self):
        data = {"metrics": {"growths_extended": {"rev_cagr_5y": 0.12}}}
        assert resolve_path(data, "metrics.growths_extended.rev_cagr_5y") == 0.12

    def test_missing_key(self):
        assert resolve_path({"a": 1}, "b") is None

    def test_missing_nested(self):
        assert resolve_path({"a": {"b": 1}}, "a.c") is None

    def test_non_dict_intermediate(self):
        assert resolve_path({"a": 42}, "a.b") is None

    def test_empty_dict(self):
        assert resolve_path({}, "a") is None


# --- has_claim_signal ---


class TestHasClaimSignal:
    def test_simple_match(self):
        assert has_claim_signal("revenue is growing steadily", ["growing"])

    def test_case_insensitive(self):
        assert has_claim_signal("Revenue Growth accelerated", ["growth"])

    def test_no_match(self):
        assert not has_claim_signal("revenue was flat", ["growing", "growth"])

    def test_negated_signal_excluded(self):
        assert not has_claim_signal("revenue is not growing", ["growing"])

    def test_negation_isnt(self):
        assert not has_claim_signal("growth isn't accelerating", ["accelerating"])

    def test_negation_without(self):
        assert not has_claim_signal("without significant growth in the period", ["growth"])

    def test_negation_barely(self):
        assert not has_claim_signal("barely growing at all", ["growing"])

    def test_negation_despite(self):
        assert not has_claim_signal("despite growth in some segments", ["growth"])

    def test_negation_window_exceeded(self):
        # Negation more than 4 words before signal — not considered negated
        assert has_claim_signal(
            "they did not achieve the target but revenue is growing",
            ["growing"],
        )

    def test_multiple_signals_one_matches(self):
        assert has_claim_signal("the business is expanding", ["growing", "expanding"])

    def test_signal_as_substring(self):
        assert has_claim_signal("accelerating revenue", ["accelerating"])

    def test_empty_text(self):
        assert not has_claim_signal("", ["growing"])

    def test_empty_signals(self):
        assert not has_claim_signal("revenue is growing", [])


# --- has_negated_claim ---


class TestHasNegatedClaim:
    def test_negated(self):
        assert has_negated_claim("revenue is not growing", ["growing"])

    def test_not_negated(self):
        assert not has_negated_claim("revenue is growing", ["growing"])

    def test_lacks(self):
        assert has_negated_claim("the company lacks growth", ["growth"])


# --- extract_numeric_claims ---


class TestExtractNumericClaims:
    def test_percentage(self):
        claims = extract_numeric_claims("ROIC of 18% is strong")
        assert "18%" in claims

    def test_negative_percentage(self):
        claims = extract_numeric_claims("revenue declined -2.5% year over year")
        assert "-2.5%" in claims

    def test_dollar_amount(self):
        claims = extract_numeric_claims("revenue of $50 billion")
        assert any("50" in c for c in claims)

    def test_billion_unit(self):
        claims = extract_numeric_claims("generated 3.2 billion in cash flow")
        assert any("3.2 billion" in c for c in claims)

    def test_comma_number(self):
        claims = extract_numeric_claims("serving 1,234,567 customers")
        assert any("1,234,567" in c for c in claims)

    def test_double_digit(self):
        claims = extract_numeric_claims("double-digit revenue growth")
        assert "double-digit" in claims

    def test_single_digit(self):
        claims = extract_numeric_claims("single digit margin improvement")
        assert "single digit" in claims

    def test_no_numbers(self):
        assert extract_numeric_claims("the company sells software") == []

    def test_multiple_claims(self):
        text = "revenue grew 12% to $45 billion with double-digit margins"
        claims = extract_numeric_claims(text)
        assert len(claims) >= 3

    def test_bps(self):
        claims = extract_numeric_claims("margins expanded 150 bps")
        assert any("150 bps" in c for c in claims)


# --- has_revenue_data ---


class TestHasRevenueData:
    def test_has_data(self):
        ts = [{"fiscal_year": 2023, "revenue": 100000}]
        assert has_revenue_data(ts)

    def test_no_data(self):
        ts = [{"fiscal_year": 2023, "revenue": None}]
        assert not has_revenue_data(ts)

    def test_empty_list(self):
        assert not has_revenue_data([])

    def test_not_a_list(self):
        assert not has_revenue_data(None)
        assert not has_revenue_data("string")

    def test_mixed(self):
        ts = [
            {"fiscal_year": 2022, "revenue": None},
            {"fiscal_year": 2023, "revenue": 50000},
        ]
        assert has_revenue_data(ts)


# --- Grounding checks (contract-driven) ---


SAMPLE_AGENT_BUNDLE = {
    "company": {"ticker": "AAPL", "name": "Apple Inc"},
    "metrics": {
        "growths_extended": {
            "rev_cagr_5y": 0.08,
            "rev_cagr_1y": 0.05,
        },
        "roic_avg_10y": 0.25,
        "debt_to_equity": 1.5,
    },
    "timeseries": {
        "is": [
            {"fiscal_year": 2022, "revenue": 394000000000},
            {"fiscal_year": 2023, "revenue": 383000000000},
        ]
    },
}


def _make_growth_check(severity="hard"):
    return {
        "id": "growth_claim_not_contradicted",
        "claim_signals": ["growing", "growth", "expanding", "accelerating"],
        "claim_source": "output.narrative",
        "verify_against": "agent_bundle.metrics.growths_extended.rev_cagr_5y",
        "contradiction_rule": "claim_present AND metric < 0",
        "severity": severity,
        "description": "Growth claims must align with revenue CAGR",
    }


def _make_decline_check():
    return {
        "id": "decline_claim_not_contradicted",
        "claim_signals": ["declining", "shrinking", "contracting", "falling"],
        "claim_source": "output.narrative",
        "verify_against": "agent_bundle.metrics.growths_extended.rev_cagr_5y",
        "contradiction_rule": "claim_present AND metric > 5",
        "severity": "hard",
        "description": "Decline claims contradicted by strong positive growth",
    }


def _make_revenue_drivers_check():
    return {
        "id": "revenue_drivers_not_fabricated",
        "claim_source": "output.revenue_drivers",
        "verify_against": "agent_bundle.timeseries.is",
        "contradiction_rule": "output.revenue_drivers.length > 0 AND no revenue entries",
        "severity": "hard",
        "description": "Revenue drivers listed without supporting data",
    }


def _make_unverifiable_check():
    return {
        "id": "unverifiable_numeric_claims",
        "claim_source": "output.narrative",
        "verify_against": ["agent_bundle", "item1_text"],
        "contradiction_rule": "numeric_claim_present AND not_found_in_sources",
        "severity": "soft",
        "description": "Numeric claims not traceable to sources",
    }


class TestGrowthCheck:
    def test_growth_claim_consistent(self):
        output = {"narrative": "Apple has demonstrated consistent revenue growth over five years."}
        result = run_grounding_check(_make_growth_check(), output, SAMPLE_AGENT_BUNDLE)
        assert result["passed"]

    def test_growth_claim_contradicted(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": -0.05}}}
        output = {"narrative": "The company is growing rapidly."}
        result = run_grounding_check(_make_growth_check(), output, bundle)
        assert not result["passed"]
        assert result["severity"] == "hard"

    def test_no_growth_claim(self):
        output = {"narrative": "Apple is a technology company based in Cupertino."}
        result = run_grounding_check(_make_growth_check(), output, SAMPLE_AGENT_BUNDLE)
        assert result["passed"]

    def test_metric_missing(self):
        bundle = {"metrics": {"growths_extended": {"rev_cagr_5y": None}}}
        output = {"narrative": "Revenue growth was strong."}
        result = run_grounding_check(_make_growth_check(), output, bundle)
        assert result["passed"]
        assert "null" in result["details"].lower() or "missing" in result["details"].lower()

    def test_negated_growth_not_triggered(self):
        output = {"narrative": "The company is not growing significantly."}
        result = run_grounding_check(_make_growth_check(), output, SAMPLE_AGENT_BUNDLE)
        assert result["passed"]

    def test_zero_cagr_passes(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": 0.0}}}
        output = {"narrative": "Revenue has shown modest growth."}
        result = run_grounding_check(_make_growth_check(), output, bundle)
        assert result["passed"]


class TestDeclineCheck:
    def test_decline_consistent(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": -0.03}}}
        output = {"narrative": "Revenue has been declining for several years."}
        result = run_grounding_check(_make_decline_check(), output, bundle)
        assert result["passed"]

    def test_decline_contradicted_by_strong_growth(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": 0.15}}}
        output = {"narrative": "The company's revenue is shrinking."}
        result = run_grounding_check(_make_decline_check(), output, bundle)
        assert not result["passed"]

    def test_no_decline_claim(self):
        output = {"narrative": "Revenue was stable this year."}
        result = run_grounding_check(_make_decline_check(), output, SAMPLE_AGENT_BUNDLE)
        assert result["passed"]

    def test_moderate_positive_not_contradiction(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": 0.03}}}
        output = {"narrative": "Some segments are declining."}
        result = run_grounding_check(_make_decline_check(), output, bundle)
        assert result["passed"]


class TestRevenueDriversCheck:
    def test_drivers_with_data(self):
        output = {"revenue_drivers": ["iPhone", "Services"]}
        result = run_grounding_check(_make_revenue_drivers_check(), output, SAMPLE_AGENT_BUNDLE)
        assert result["passed"]

    def test_drivers_without_data(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "timeseries": {"is": []}}
        output = {"revenue_drivers": ["iPhone", "Services"]}
        result = run_grounding_check(_make_revenue_drivers_check(), output, bundle)
        assert not result["passed"]

    def test_no_drivers(self):
        output = {"revenue_drivers": []}
        bundle = {**SAMPLE_AGENT_BUNDLE, "timeseries": {"is": []}}
        result = run_grounding_check(_make_revenue_drivers_check(), output, bundle)
        assert result["passed"]

    def test_null_revenue_entries(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "timeseries": {"is": [{"fiscal_year": 2023, "revenue": None}]}}
        output = {"revenue_drivers": ["Cloud"]}
        result = run_grounding_check(_make_revenue_drivers_check(), output, bundle)
        assert not result["passed"]


class TestUnverifiableNumerics:
    def test_all_verifiable(self):
        output = {"narrative": "Revenue was $394 billion in 2022."}
        item1 = "Total net revenue was $394 billion for fiscal year 2022."
        result = run_grounding_check(_make_unverifiable_check(), output, SAMPLE_AGENT_BUNDLE, item1)
        assert result["passed"]

    def test_unverifiable_claim(self):
        output = {"narrative": "Revenue grew 42% driven by AI products."}
        result = run_grounding_check(_make_unverifiable_check(), output, SAMPLE_AGENT_BUNDLE, "")
        assert not result["passed"]
        assert result["severity"] == "soft"

    def test_no_numeric_claims(self):
        output = {"narrative": "Apple designs and sells consumer electronics."}
        result = run_grounding_check(_make_unverifiable_check(), output, SAMPLE_AGENT_BUNDLE, "")
        assert result["passed"]


class TestUnknownCheckId:
    def test_unknown_id_skipped(self):
        check = {"id": "future_check_xyz", "severity": "hard"}
        result = run_grounding_check(check, {}, {})
        assert result["passed"]
        assert "skipped" in result["details"].lower()


# --- run_all_grounding_checks ---


class TestRunAllGroundingChecks:
    def test_all_pass(self):
        output = {
            "narrative": "Apple is a technology company that sells iPhones and services.",
            "revenue_drivers": ["iPhone", "Services"],
        }
        checks = [_make_growth_check(), _make_decline_check(), _make_revenue_drivers_check()]
        result = run_all_grounding_checks(checks, output, SAMPLE_AGENT_BUNDLE)
        assert result["pass"]
        assert result["contradictions_found"] == 0

    def test_hard_contradiction_fails(self):
        bundle = {**SAMPLE_AGENT_BUNDLE, "metrics": {"growths_extended": {"rev_cagr_5y": -0.10}}}
        output = {
            "narrative": "The company is growing rapidly.",
            "revenue_drivers": ["iPhone"],
        }
        checks = [_make_growth_check(), _make_revenue_drivers_check()]
        result = run_all_grounding_checks(checks, output, bundle)
        assert not result["pass"]
        assert result["contradictions_found"] == 1

    def test_soft_flag_still_passes(self):
        output = {
            "narrative": "Revenue grew 99% this year.",
            "revenue_drivers": ["iPhone"],
        }
        checks = [_make_unverifiable_check()]
        result = run_all_grounding_checks(checks, output, SAMPLE_AGENT_BUNDLE, "")
        assert result["pass"]
        assert result["soft_flags"] == 1

    def test_empty_checks(self):
        result = run_all_grounding_checks([], {}, {})
        assert result["pass"]
        assert result["contradictions_found"] == 0

    def test_multiple_hard_failures(self):
        bundle = {
            **SAMPLE_AGENT_BUNDLE,
            "metrics": {"growths_extended": {"rev_cagr_5y": -0.10}},
            "timeseries": {"is": []},
        }
        output = {
            "narrative": "Revenue is expanding rapidly.",
            "revenue_drivers": ["Product A", "Product B"],
        }
        checks = [_make_growth_check(), _make_revenue_drivers_check()]
        result = run_all_grounding_checks(checks, output, bundle)
        assert not result["pass"]
        assert result["contradictions_found"] == 2
