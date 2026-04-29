"""Four-layer evaluator for the qualitative agent harness.

Validates builder output against a pre-negotiated contract:
  L1: Deterministic schema checks (free)
  L2: Cross-reference checks (free)
  L3: Grounding checks (free, delegates to grounding.py)
  L4: LLM adversarial evaluation (~$0.003)

Layers 1-3 run first and short-circuit on failure — no LLM cost
wasted on structurally invalid output.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Protocol

from app.nlp.research_agent.harness.framework_card import EVALUATOR_FRAMEWORK_ADDENDUM
from app.nlp.research_agent.harness.grounding import (
    resolve_path,
    run_all_grounding_checks,
)


# --- LLM callable protocol (for dependency injection in tests) ---


class LLMCallable(Protocol):
    def __call__(self, system_prompt: str, user_prompt: str, static_context: str | None = None) -> str: ...


# --- Layer 1: Schema validation ---


def check_schema(
    builder_output: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Validate builder output against contract schema rules."""
    schema = contract.get("output_schema", {})
    failures: list[str] = []

    required = schema.get("required_fields", [])
    for field in required:
        if field not in builder_output:
            failures.append(f"Missing required field: {field}")

    if schema.get("no_nulls"):
        for key, val in builder_output.items():
            if val is None:
                failures.append(f"Null value for field: {key}")

    field_types = schema.get("field_types", {})
    for field, expected_type in field_types.items():
        if field not in builder_output:
            continue
        val = builder_output[field]
        if val is None:
            continue
        if expected_type == "string" and not isinstance(val, str):
            failures.append(f"Field '{field}' should be string, got {type(val).__name__}")
        elif expected_type == "array[string]":
            if not isinstance(val, list):
                failures.append(f"Field '{field}' should be array, got {type(val).__name__}")
            elif not all(isinstance(v, str) for v in val):
                failures.append(f"Field '{field}' contains non-string elements")

    if schema.get("no_empty_strings_in_arrays"):
        for field, val in builder_output.items():
            if isinstance(val, list):
                if any(isinstance(v, str) and v.strip() == "" for v in val):
                    failures.append(f"Field '{field}' contains empty strings")

    minimums = schema.get("array_minimums", {})
    for field, min_len in minimums.items():
        val = builder_output.get(field, [])
        if isinstance(val, list) and len(val) < min_len:
            failures.append(f"Field '{field}' has {len(val)} items, minimum is {min_len}")

    enums = schema.get("enums", {})
    for field, allowed in enums.items():
        val = builder_output.get(field)
        if isinstance(val, list):
            for item in val:
                if item not in allowed:
                    failures.append(
                        f"Field '{field}' contains invalid value '{item}', "
                        f"allowed: {allowed}"
                    )
        elif isinstance(val, str) and val not in allowed:
            failures.append(
                f"Field '{field}' has invalid value '{val}', allowed: {allowed}"
            )

    str_mins = schema.get("string_minimums", {})
    for field, min_len in str_mins.items():
        val = builder_output.get(field, "")
        if isinstance(val, str) and len(val) < min_len:
            failures.append(
                f"Field '{field}' is {len(val)} chars, minimum is {min_len}"
            )

    return {
        "schema_valid": len(failures) == 0,
        "no_nulls": not any("Null value" in f for f in failures),
        "array_minimums": not any("minimum is" in f for f in failures),
        "enum_valid": not any("invalid value" in f for f in failures),
        "details": failures,
    }


# --- Layer 2: Cross-reference checks ---


def check_cross_references(
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate builder output against agent-bundle cross-references."""
    xrefs = contract.get("cross_references", [])
    failures: list[str] = []
    results: dict[str, bool] = {}

    for xref in xrefs:
        check_name = xref.get("check", "")
        match_type = xref.get("match", "")

        source_path = xref.get("source", "").replace("agent_bundle.", "", 1)
        target_path = xref.get("target", "").replace("output.", "", 1)

        source_val = resolve_path(agent_bundle, source_path)
        target_val = resolve_path(builder_output, target_path)

        if source_val is None or target_val is None:
            results[check_name] = True
            continue

        source_str = str(source_val)
        target_str = str(target_val)

        if match_type == "case_insensitive_exact":
            passed = source_str.lower() == target_str.lower()
        elif match_type == "substring_either_direction":
            passed = (
                source_str.lower() in target_str.lower()
                or target_str.lower() in source_str.lower()
            )
        else:
            passed = source_str == target_str

        results[check_name] = passed
        if not passed:
            failures.append(
                f"Cross-reference '{check_name}' failed: "
                f"source='{source_str}', target='{target_str}'"
            )

    return {
        **results,
        "details": failures,
    }


# --- Layer 4: LLM adversarial evaluation ---

EVALUATOR_SYSTEM_PROMPT = (
    EVALUATOR_FRAMEWORK_ADDENDUM
    + "\n---\n\n"
    "You are a skeptical investment analyst reviewing a colleague's work. "
    "Your job is to find errors, unsupported claims, and gaps. "
    "Score harshly — a mediocre analysis that passes is worse than a good "
    "one that fails and gets revised.\n\n"
    "You MUST respond with valid JSON only. No markdown, no explanation "
    "outside the JSON structure."
)


def build_llm_eval_prompt(
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    contract: dict[str, Any],
) -> str:
    """Build the user prompt for the LLM evaluator."""
    criteria = contract.get("llm_eval_criteria", {})
    sprint = contract.get("sprint", "unknown")

    criteria_text = ""
    for name, spec in criteria.items():
        if isinstance(spec, dict):
            criteria_text += (
                f"\n### {name} (0-{spec.get('weight', 5)})\n"
                f"Question: {spec.get('prompt', '')}\n"
                f"5/5: {spec.get('score_5', '')}\n"
                f"3/5: {spec.get('score_3', '')}\n"
                f"1/5: {spec.get('score_1', '')}\n"
            )

    return (
        f"## Evaluate this {sprint} output\n\n"
        f"### Builder output:\n```json\n{json.dumps(builder_output, indent=2)}\n```\n\n"
        f"### Agent-bundle summary (quantitative data):\n"
        f"Company: {agent_bundle.get('company', {}).get('ticker', 'unknown')}\n"
        f"Metrics: {json.dumps(agent_bundle.get('metrics', {}), indent=2, default=str)}\n\n"
        f"## Scoring criteria:{criteria_text}\n\n"
        f"## Required response format:\n"
        f"```json\n"
        f'{{\n'
        f'  "evidence_quality": {{"score": <0-5>, "notes": "<1-2 sentences>"}},\n'
        f'  "completeness": {{"score": <0-5>, "notes": "<1-2 sentences>"}},\n'
        f'  "consistency": {{"score": <0-5>, "notes": "<1-2 sentences>"}},\n'
        f'  "red_flags": {{"score": <0-5>, "notes": "<1-2 sentences>"}},\n'
        f'  "failures": ["<specific failure if any>"]\n'
        f'}}\n'
        f"```\n"
    )


def parse_llm_eval_response(raw: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Parse the LLM evaluator response into structured scores."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return _default_llm_eval(error=f"Failed to parse LLM response: {raw[:200]}")

    criteria = contract.get("llm_eval_criteria", {})
    threshold = contract.get("pass_threshold", {})
    min_score = threshold.get("llm_score_minimum", 12)
    max_score = threshold.get("llm_score_maximum", 20)

    result: dict[str, Any] = {}
    overall = 0

    for name, spec in criteria.items():
        weight = spec.get("weight", 5) if isinstance(spec, dict) else 5
        dim = parsed.get(name, {})
        score = dim.get("score", 0) if isinstance(dim, dict) else 0
        score = max(0, min(weight, score))
        notes = dim.get("notes", "") if isinstance(dim, dict) else ""
        result[name] = {"score": score, "max": weight, "notes": notes}
        overall += score

    failures = parsed.get("failures", [])
    if not isinstance(failures, list):
        failures = []

    result["overall"] = overall
    result["max"] = max_score
    result["pass"] = overall >= min_score
    result["failures"] = failures
    return result


def _default_llm_eval(error: str = "") -> dict[str, Any]:
    return {
        "evidence_quality": {"score": 0, "max": 5, "notes": error},
        "completeness": {"score": 0, "max": 5, "notes": ""},
        "consistency": {"score": 0, "max": 5, "notes": ""},
        "red_flags": {"score": 0, "max": 5, "notes": ""},
        "overall": 0,
        "max": 20,
        "pass": False,
        "failures": [error] if error else [],
    }


# --- Main evaluator ---


def evaluate(
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    contract: dict[str, Any],
    item1_text: str = "",
    llm_call: LLMCallable | None = None,
) -> dict[str, Any]:
    """Run all four evaluation layers and return structured eval_result.

    If llm_call is None, Layer 4 is skipped (useful for testing L1-L3
    in isolation or when deterministic layers already fail).
    """
    start = time.time()
    sprint = contract.get("sprint", "unknown")

    # L1: Schema
    schema_result = check_schema(builder_output, contract)
    schema_pass = schema_result["schema_valid"]

    # L2: Cross-references
    xref_result = check_cross_references(builder_output, agent_bundle, contract)
    xref_pass = len(xref_result.get("details", [])) == 0

    # L3: Grounding
    grounding_checks = contract.get("grounding_checks", [])
    grounding_result = run_all_grounding_checks(
        grounding_checks, builder_output, agent_bundle, item1_text
    )

    # Determine if deterministic layers pass
    threshold = contract.get("pass_threshold", {})
    deterministic_pass = schema_pass and xref_pass
    grounding_pass = grounding_result["pass"]

    # L4: LLM evaluation (skip if deterministic layers failed or no LLM provided)
    if deterministic_pass and grounding_pass and llm_call is not None:
        prompt = build_llm_eval_prompt(builder_output, agent_bundle, contract)
        try:
            raw_response = llm_call(EVALUATOR_SYSTEM_PROMPT, prompt)
            llm_result = parse_llm_eval_response(raw_response, contract)
        except Exception as e:
            llm_result = _default_llm_eval(error=f"LLM call failed: {e}")
    elif not deterministic_pass or not grounding_pass:
        llm_result = _default_llm_eval(
            error="Skipped: deterministic checks failed"
        )
    else:
        llm_result = _default_llm_eval(error="No LLM callable provided")

    # Overall pass
    overall_pass = deterministic_pass and grounding_pass and llm_result.get("pass", False)

    duration = time.time() - start

    return {
        "sprint": sprint,
        "pass": overall_pass,
        "deterministic_checks": schema_result,
        "cross_reference_checks": xref_result,
        "grounding_checks": {
            "pass": grounding_result["pass"],
            "contradictions_found": grounding_result["contradictions_found"],
            "soft_flags": grounding_result.get("soft_flags", 0),
            "details": grounding_result["details"],
        },
        "llm_evaluation": llm_result,
        "duration_seconds": round(duration, 3),
    }
