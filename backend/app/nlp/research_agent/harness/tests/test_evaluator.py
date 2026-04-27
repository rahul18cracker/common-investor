"""Tests for the evaluator module — 4-layer evaluation."""

import json

import pytest

from app.nlp.research_agent.harness.evaluator import (
    build_llm_eval_prompt,
    check_cross_references,
    check_schema,
    evaluate,
    parse_llm_eval_response,
)


# --- Fixtures ---


SAMPLE_CONTRACT = {
    "sprint": "01_business_profile",
    "output_schema": {
        "required_fields": ["ticker", "name", "narrative", "products_services"],
        "field_types": {
            "ticker": "string",
            "name": "string",
            "narrative": "string",
            "products_services": "array[string]",
        },
        "no_nulls": True,
        "no_empty_strings_in_arrays": True,
        "array_minimums": {"products_services": 2},
        "enums": {
            "pricing_model": ["subscription", "usage", "one_time", "hybrid"],
        },
        "string_minimums": {"narrative": 400},
    },
    "cross_references": [
        {
            "check": "ticker_match",
            "source": "agent_bundle.company.ticker",
            "target": "output.ticker",
            "match": "case_insensitive_exact",
        },
        {
            "check": "name_match",
            "source": "agent_bundle.company.name",
            "target": "output.name",
            "match": "substring_either_direction",
        },
    ],
    "grounding_checks": [
        {
            "id": "growth_claim_not_contradicted",
            "claim_signals": ["growing", "growth"],
            "claim_source": "output.narrative",
            "verify_against": "agent_bundle.metrics.growths_extended.rev_cagr_5y",
            "contradiction_rule": "claim_present AND metric < 0",
            "severity": "hard",
            "description": "Growth claims must align with revenue CAGR",
        },
    ],
    "llm_eval_criteria": {
        "evidence_quality": {
            "weight": 5,
            "prompt": "Are claims backed by specific figures?",
            "score_5": "Every driver tied to a specific figure",
            "score_3": "Most claims specific",
            "score_1": "Mostly generic",
        },
        "completeness": {
            "weight": 5,
            "prompt": "Coverage of all major areas?",
            "score_5": "Comprehensive",
            "score_3": "Mostly covered",
            "score_1": "Major gaps",
        },
        "consistency": {
            "weight": 5,
            "prompt": "Internal consistency?",
            "score_5": "Fully consistent",
            "score_3": "Minor issues",
            "score_1": "Contradictions",
        },
        "red_flags": {
            "weight": 5,
            "prompt": "No marketing language or hallucinations?",
            "score_5": "Clean and factual",
            "score_3": "One minor issue",
            "score_1": "Marketing copy",
        },
    },
    "pass_threshold": {
        "deterministic_checks": "all_pass",
        "grounding_hard": "zero_contradictions",
        "grounding_soft": "flag_only",
        "llm_score_minimum": 12,
        "llm_score_maximum": 20,
    },
}

SAMPLE_AGENT_BUNDLE = {
    "company": {"ticker": "AAPL", "name": "Apple Inc"},
    "metrics": {
        "growths_extended": {"rev_cagr_5y": 0.08},
        "roic_avg_10y": 0.25,
    },
    "timeseries": {
        "is": [{"fiscal_year": 2023, "revenue": 383000000000}],
    },
}

GOOD_OUTPUT = {
    "ticker": "AAPL",
    "name": "Apple Inc",
    "narrative": (
        "Apple Inc. designs, manufactures, and markets smartphones, personal "
        "computers, tablets, wearables, and accessories worldwide. The company "
        "offers iPhone, Mac, iPad, and wearables as its primary hardware products. "
        "Services revenue, including the App Store, Apple Music, iCloud, and "
        "Apple TV+, represents a growing high-margin segment. Revenue is driven "
        "by iPhone sales (approximately 52% of total revenue), Services (22%), "
        "and Mac/iPad/wearables (26%). The company operates through direct retail "
        "stores, online channels, and third-party distributors globally."
    ),
    "products_services": ["iPhone", "Mac", "iPad", "Services"],
    "pricing_model": ["one_time", "subscription"],
}


# --- Layer 1: Schema checks ---


class TestCheckSchema:
    def test_valid_output(self):
        result = check_schema(GOOD_OUTPUT, SAMPLE_CONTRACT)
        assert result["schema_valid"]
        assert result["details"] == []

    def test_missing_required_field(self):
        output = {**GOOD_OUTPUT}
        del output["ticker"]
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["schema_valid"]
        assert any("ticker" in d for d in result["details"])

    def test_null_value(self):
        output = {**GOOD_OUTPUT, "ticker": None}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["no_nulls"]

    def test_wrong_type_string(self):
        output = {**GOOD_OUTPUT, "ticker": 123}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["schema_valid"]
        assert any("string" in d for d in result["details"])

    def test_wrong_type_array(self):
        output = {**GOOD_OUTPUT, "products_services": "not an array"}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["schema_valid"]

    def test_array_non_string_elements(self):
        output = {**GOOD_OUTPUT, "products_services": ["iPhone", 42]}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["schema_valid"]

    def test_array_minimum_violated(self):
        output = {**GOOD_OUTPUT, "products_services": ["iPhone"]}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["array_minimums"]

    def test_enum_violation(self):
        output = {**GOOD_OUTPUT, "pricing_model": ["invalid_model"]}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["enum_valid"]

    def test_enum_valid(self):
        result = check_schema(GOOD_OUTPUT, SAMPLE_CONTRACT)
        assert result["enum_valid"]

    def test_string_minimum_violated(self):
        output = {**GOOD_OUTPUT, "narrative": "Too short."}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert not result["schema_valid"]
        assert any("400" in d for d in result["details"])

    def test_empty_string_in_array(self):
        output = {**GOOD_OUTPUT, "products_services": ["iPhone", ""]}
        result = check_schema(output, SAMPLE_CONTRACT)
        assert any("empty strings" in d for d in result["details"])

    def test_enum_string_value(self):
        contract = {
            "output_schema": {
                "enums": {"stance": ["buy", "hold", "avoid"]},
            }
        }
        output = {"stance": "buy"}
        result = check_schema(output, contract)
        assert result["enum_valid"]

        output_bad = {"stance": "maybe"}
        result_bad = check_schema(output_bad, contract)
        assert not result_bad["enum_valid"]


# --- Layer 2: Cross-reference checks ---


class TestCheckCrossReferences:
    def test_ticker_match(self):
        result = check_cross_references(GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert result.get("ticker_match")
        assert result["details"] == []

    def test_ticker_case_insensitive(self):
        output = {**GOOD_OUTPUT, "ticker": "aapl"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert result.get("ticker_match")

    def test_ticker_mismatch(self):
        output = {**GOOD_OUTPUT, "ticker": "MSFT"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert not result.get("ticker_match")
        assert len(result["details"]) > 0

    def test_name_substring_match(self):
        output = {**GOOD_OUTPUT, "name": "Apple"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert result.get("name_match")

    def test_name_reverse_substring(self):
        output = {**GOOD_OUTPUT, "name": "Apple Inc (AAPL)"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert result.get("name_match")

    def test_name_mismatch(self):
        output = {**GOOD_OUTPUT, "name": "Microsoft Corp"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert not result.get("name_match")

    def test_missing_source_value_passes(self):
        bundle = {"company": {}}
        result = check_cross_references(GOOD_OUTPUT, bundle, SAMPLE_CONTRACT)
        assert result.get("ticker_match")

    def test_missing_target_value_passes(self):
        output = {"narrative": "text only"}
        result = check_cross_references(output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert result.get("ticker_match")


# --- Layer 4: LLM eval prompt & parsing ---


class TestBuildLLMEvalPrompt:
    def test_contains_builder_output(self):
        prompt = build_llm_eval_prompt(GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert "AAPL" in prompt
        assert "iPhone" in prompt

    def test_contains_criteria(self):
        prompt = build_llm_eval_prompt(GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert "evidence_quality" in prompt
        assert "completeness" in prompt

    def test_contains_response_format(self):
        prompt = build_llm_eval_prompt(GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT)
        assert '"score"' in prompt


class TestParseLLMEvalResponse:
    def test_valid_response(self):
        raw = json.dumps({
            "evidence_quality": {"score": 4, "notes": "Good specifics."},
            "completeness": {"score": 5, "notes": "All covered."},
            "consistency": {"score": 4, "notes": "Mostly aligned."},
            "red_flags": {"score": 5, "notes": "Clean output."},
            "failures": [],
        })
        result = parse_llm_eval_response(raw, SAMPLE_CONTRACT)
        assert result["overall"] == 18
        assert result["pass"]
        assert result["failures"] == []

    def test_below_threshold(self):
        raw = json.dumps({
            "evidence_quality": {"score": 2, "notes": "Vague."},
            "completeness": {"score": 3, "notes": "Gaps."},
            "consistency": {"score": 2, "notes": "Issues."},
            "red_flags": {"score": 2, "notes": "Marketing tone."},
            "failures": ["Vague revenue drivers"],
        })
        result = parse_llm_eval_response(raw, SAMPLE_CONTRACT)
        assert result["overall"] == 9
        assert not result["pass"]

    def test_markdown_wrapped_response(self):
        raw = '```json\n{"evidence_quality": {"score": 4, "notes": ""}, "completeness": {"score": 4, "notes": ""}, "consistency": {"score": 4, "notes": ""}, "red_flags": {"score": 4, "notes": ""}, "failures": []}\n```'
        result = parse_llm_eval_response(raw, SAMPLE_CONTRACT)
        assert result["overall"] == 16
        assert result["pass"]

    def test_invalid_json(self):
        result = parse_llm_eval_response("not json at all", SAMPLE_CONTRACT)
        assert not result["pass"]
        assert result["overall"] == 0

    def test_score_clamped(self):
        raw = json.dumps({
            "evidence_quality": {"score": 99, "notes": ""},
            "completeness": {"score": -5, "notes": ""},
            "consistency": {"score": 3, "notes": ""},
            "red_flags": {"score": 4, "notes": ""},
            "failures": [],
        })
        result = parse_llm_eval_response(raw, SAMPLE_CONTRACT)
        assert result["evidence_quality"]["score"] == 5
        assert result["completeness"]["score"] == 0


# --- Full evaluate() ---


def _mock_llm_pass(system_prompt: str, user_prompt: str) -> str:
    return json.dumps({
        "evidence_quality": {"score": 4, "notes": "Good."},
        "completeness": {"score": 4, "notes": "Complete."},
        "consistency": {"score": 4, "notes": "Consistent."},
        "red_flags": {"score": 4, "notes": "Clean."},
        "failures": [],
    })


def _mock_llm_fail(system_prompt: str, user_prompt: str) -> str:
    return json.dumps({
        "evidence_quality": {"score": 1, "notes": "Vague."},
        "completeness": {"score": 2, "notes": "Gaps."},
        "consistency": {"score": 1, "notes": "Contradictions."},
        "red_flags": {"score": 1, "notes": "Marketing copy."},
        "failures": ["Multiple issues found"],
    })


def _mock_llm_error(system_prompt: str, user_prompt: str) -> str:
    raise RuntimeError("API timeout")


class TestEvaluate:
    def test_full_pass(self):
        result = evaluate(
            GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=_mock_llm_pass,
        )
        assert result["pass"]
        assert result["sprint"] == "01_business_profile"
        assert result["deterministic_checks"]["schema_valid"]
        assert result["grounding_checks"]["pass"]
        assert result["llm_evaluation"]["pass"]
        assert result["duration_seconds"] >= 0

    def test_schema_failure_skips_llm(self):
        bad_output = {**GOOD_OUTPUT}
        del bad_output["ticker"]
        result = evaluate(
            bad_output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=_mock_llm_pass,
        )
        assert not result["pass"]
        assert not result["deterministic_checks"]["schema_valid"]
        assert result["llm_evaluation"]["overall"] == 0
        assert "Skipped" in result["llm_evaluation"]["failures"][0]

    def test_xref_failure_skips_llm(self):
        bad_output = {**GOOD_OUTPUT, "ticker": "MSFT"}
        result = evaluate(
            bad_output, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=_mock_llm_pass,
        )
        assert not result["pass"]
        assert len(result["cross_reference_checks"]["details"]) > 0

    def test_grounding_failure_skips_llm(self):
        bundle = {
            **SAMPLE_AGENT_BUNDLE,
            "metrics": {"growths_extended": {"rev_cagr_5y": -0.10}},
        }
        output = {**GOOD_OUTPUT, "narrative": GOOD_OUTPUT["narrative"].replace(
            "represents a growing", "represents a growing"
        )}
        result = evaluate(
            output, bundle, SAMPLE_CONTRACT,
            llm_call=_mock_llm_pass,
        )
        assert not result["pass"]
        assert not result["grounding_checks"]["pass"]

    def test_llm_failure_overall_fails(self):
        result = evaluate(
            GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=_mock_llm_fail,
        )
        assert not result["pass"]
        assert not result["llm_evaluation"]["pass"]

    def test_no_llm_callable(self):
        result = evaluate(
            GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=None,
        )
        assert not result["pass"]
        assert "No LLM" in result["llm_evaluation"]["failures"][0]

    def test_llm_exception_handled(self):
        result = evaluate(
            GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            llm_call=_mock_llm_error,
        )
        assert not result["pass"]
        assert "LLM call failed" in result["llm_evaluation"]["failures"][0]

    def test_empty_contract(self):
        result = evaluate(
            {"ticker": "AAPL"}, {}, {},
            llm_call=_mock_llm_pass,
        )
        assert result["deterministic_checks"]["schema_valid"]

    def test_grounding_with_item1(self):
        result = evaluate(
            GOOD_OUTPUT, SAMPLE_AGENT_BUNDLE, SAMPLE_CONTRACT,
            item1_text="Apple Inc designs and markets consumer electronics.",
            llm_call=_mock_llm_pass,
        )
        assert result["pass"]
