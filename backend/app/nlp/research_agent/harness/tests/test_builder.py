"""Tests for the builder module — contract-driven LLM generator."""

import json

import pytest

from app.nlp.research_agent.harness.builder import (
    BUILDER_SYSTEM_PROMPT,
    SPRINT_PROMPTS,
    BuilderResult,
    build,
    build_dynamic_suffix,
    build_static_prefix,
    parse_builder_response,
)


# --- Fixtures ---

SAMPLE_CONTRACT = {
    "sprint": "01_business_profile",
    "model_tier": "haiku",
    "output_schema": {
        "required_fields": ["ticker", "name", "narrative", "products_services"],
        "enums": {"pricing_model": ["subscription", "usage", "one_time", "hybrid"]},
        "array_minimums": {"products_services": 2},
        "string_minimums": {"narrative": 400},
    },
}

SAMPLE_BUNDLE = {
    "company": {"ticker": "AAPL", "name": "Apple Inc"},
    "metrics": {"roic_avg_10y": 0.25},
}

SAMPLE_ITEM1 = "Apple Inc. designs, manufactures, and markets smartphones and personal computers."

GOOD_JSON_RESPONSE = json.dumps({
    "ticker": "AAPL",
    "name": "Apple Inc",
    "narrative": "A" * 500,
    "products_services": ["iPhone", "Mac"],
    "pricing_model": ["one_time", "subscription"],
})


# --- build_static_prefix ---


class TestBuildStaticPrefix:
    def test_contains_agent_bundle(self):
        prefix = build_static_prefix(SAMPLE_BUNDLE, SAMPLE_ITEM1)
        assert "AAPL" in prefix
        assert "roic_avg_10y" in prefix

    def test_contains_item1_text(self):
        prefix = build_static_prefix(SAMPLE_BUNDLE, SAMPLE_ITEM1)
        assert "designs, manufactures" in prefix

    def test_contains_section_headers(self):
        prefix = build_static_prefix(SAMPLE_BUNDLE, SAMPLE_ITEM1)
        assert "Quantitative Data" in prefix
        assert "Item 1" in prefix


# --- build_dynamic_suffix ---


class TestBuildDynamicSuffix:
    def test_contains_sprint_name(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "01_business_profile" in suffix

    def test_contains_sprint_prompt(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "business model" in suffix

    def test_contains_required_fields(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "ticker" in suffix
        assert "narrative" in suffix

    def test_contains_enum_constraints(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "subscription" in suffix

    def test_contains_array_minimums(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "minimum 2" in suffix

    def test_contains_string_minimums(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "400 characters" in suffix

    def test_no_nulls_instruction(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "No null" in suffix

    def test_with_prior_outputs(self):
        prior = {"01_business_profile": {"ticker": "AAPL", "narrative": "..."}}
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT, prior_outputs=prior)
        assert "Prior Sprint Outputs" in suffix
        assert "01_business_profile" in suffix

    def test_without_prior_outputs(self):
        suffix = build_dynamic_suffix(SAMPLE_CONTRACT)
        assert "Prior Sprint Outputs" not in suffix

    def test_retry_context(self):
        failures = ["Missing field: geographies", "Narrative too short"]
        suffix = build_dynamic_suffix(
            SAMPLE_CONTRACT, eval_failures=failures, attempt=2
        )
        assert "attempt 2" in suffix
        assert "Missing field: geographies" in suffix
        assert "Narrative too short" in suffix

    def test_first_attempt_no_retry_context(self):
        failures = ["Some failure"]
        suffix = build_dynamic_suffix(
            SAMPLE_CONTRACT, eval_failures=failures, attempt=1
        )
        assert "Previous Attempt Failed" not in suffix

    def test_unknown_sprint_still_works(self):
        contract = {**SAMPLE_CONTRACT, "sprint": "99_future"}
        suffix = build_dynamic_suffix(contract)
        assert "99_future" in suffix


# --- parse_builder_response ---


class TestParseBuilderResponse:
    def test_valid_json(self):
        result = parse_builder_response('{"ticker": "AAPL"}')
        assert result == {"ticker": "AAPL"}

    def test_markdown_wrapped(self):
        raw = '```json\n{"ticker": "AAPL"}\n```'
        result = parse_builder_response(raw)
        assert result == {"ticker": "AAPL"}

    def test_invalid_json(self):
        assert parse_builder_response("not json") is None

    def test_json_array_rejected(self):
        assert parse_builder_response('[1, 2, 3]') is None

    def test_empty_string(self):
        assert parse_builder_response("") is None

    def test_whitespace_padded(self):
        result = parse_builder_response('  \n{"a": 1}\n  ')
        assert result == {"a": 1}

    def test_triple_backtick_no_lang(self):
        raw = '```\n{"ticker": "AAPL"}\n```'
        result = parse_builder_response(raw)
        assert result == {"ticker": "AAPL"}


# --- SPRINT_PROMPTS ---


class TestSprintPrompts:
    def test_all_eight_sprints_have_prompts(self):
        expected = [
            "01_business_profile", "02_unit_economics", "03_industry",
            "04_moat", "05_management", "06_peers", "07_risks", "08_thesis",
        ]
        for sprint in expected:
            assert sprint in SPRINT_PROMPTS, f"Missing prompt for {sprint}"
            assert len(SPRINT_PROMPTS[sprint]) > 50

    def test_business_profile_prompt_content(self):
        prompt = SPRINT_PROMPTS["01_business_profile"]
        assert "business model" in prompt
        assert "recurring" in prompt

    def test_thesis_prompt_mentions_rubric(self):
        prompt = SPRINT_PROMPTS["08_thesis"]
        assert "quality score" in prompt.lower() or "0-100" in prompt


# --- build() ---


def _mock_llm_good(system_prompt: str, user_prompt: str) -> str:
    return GOOD_JSON_RESPONSE


def _mock_llm_bad_json(system_prompt: str, user_prompt: str) -> str:
    return "This is not JSON at all, sorry."


def _mock_llm_error(system_prompt: str, user_prompt: str) -> str:
    raise RuntimeError("Connection timeout")


class TestBuild:
    def test_successful_build(self):
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            llm_call=_mock_llm_good,
        )
        assert result.success
        assert result.output is not None
        assert result.output["ticker"] == "AAPL"
        assert result.model == "haiku"
        assert result.duration_seconds >= 0

    def test_bad_json_response(self):
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            llm_call=_mock_llm_bad_json,
        )
        assert not result.success
        assert result.output is None
        assert result.raw_response == "This is not JSON at all, sorry."

    def test_llm_exception(self):
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            llm_call=_mock_llm_error,
        )
        assert not result.success
        assert result.output is None
        assert "Connection timeout" in result.raw_response

    def test_no_llm_callable(self):
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            llm_call=None,
        )
        assert not result.success
        assert result.model == "none"

    def test_with_prior_outputs(self):
        prior = {"01_business_profile": {"ticker": "AAPL"}}
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            prior_outputs=prior, llm_call=_mock_llm_good,
        )
        assert result.success

    def test_retry_attempt(self):
        failures = ["Narrative too short"]
        result = build(
            SAMPLE_CONTRACT, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            eval_failures=failures, attempt=2, llm_call=_mock_llm_good,
        )
        assert result.success

    def test_model_from_contract(self):
        contract = {**SAMPLE_CONTRACT, "model_tier": "sonnet"}
        result = build(
            contract, SAMPLE_BUNDLE, SAMPLE_ITEM1,
            llm_call=_mock_llm_good,
        )
        assert result.model == "sonnet"


class TestBuilderSystemPrompt:
    def test_contains_methodology(self):
        assert "Rule #1" in BUILDER_SYSTEM_PROMPT
        assert "QVG" in BUILDER_SYSTEM_PROMPT

    def test_contains_json_instruction(self):
        assert "valid JSON" in BUILDER_SYSTEM_PROMPT

    def test_contains_unknown_instruction(self):
        assert "unknown" in BUILDER_SYSTEM_PROMPT
