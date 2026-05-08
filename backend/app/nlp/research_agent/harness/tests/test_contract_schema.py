"""Contract JSON schema validation tests.

Validates all 8 sprint contract files against the expected harness schema.
These tests catch malformed contracts before they cause silent runtime failures.
"""

import json
from pathlib import Path

import pytest

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"

ALL_SPRINTS = [
    "01_business_profile",
    "02_unit_economics",
    "03_industry",
    "04_moat",
    "05_management",
    "06_peers",
    "07_risks",
    "08_thesis",
]

_REQUIRED_TOP_LEVEL = {
    "sprint",
    "version",
    "model_tier",
    "dependencies",
    "output_schema",
    "grounding_checks",
    "llm_eval_criteria",
    "pass_threshold",
}

_REQUIRED_OUTPUT_SCHEMA_KEYS = {"required_fields", "field_types"}

_REQUIRED_GROUNDING_CHECK_KEYS = {
    "id",
    "description",
    "claim_source",
    "verify_against",
    "contradiction_rule",
    "severity",
}

_REQUIRED_CROSS_REF_KEYS = {"check", "rule", "source", "target", "match"}

_VALID_MATCH_TYPES = {
    "case_insensitive_exact",
    "substring_either_direction",
    "exact",
    "directional_within_1.5",
    "directional_consistency",
    "semantic_coherence",
    "skip",
}

_REQUIRED_PASS_THRESHOLD_KEYS = {
    "deterministic_checks",
    "grounding_hard",
    "grounding_soft",
    "llm_score_minimum",
    "llm_score_maximum",
}

_NON_STANDARD_SCHEMA_KEYS = {
    "nested_schemas",
    "nested_no_nulls",
    "conditional_string_minimums",
    "integer_ranges",
}

_VALID_MODEL_TIERS = {"haiku", "sonnet", "opus"}


def _load(sprint: str) -> dict:
    path = CONTRACTS_DIR / f"{sprint}.json"
    return json.loads(path.read_text())


@pytest.mark.unit
class TestContractFilesExist:
    def test_all_contract_files_present(self):
        missing = [s for s in ALL_SPRINTS if not (CONTRACTS_DIR / f"{s}.json").exists()]
        assert not missing, f"Missing contract files: {missing}"


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestContractTopLevel:
    def test_required_top_level_keys(self, sprint):
        contract = _load(sprint)
        missing = _REQUIRED_TOP_LEVEL - set(contract.keys())
        assert not missing, f"{sprint}: missing top-level keys {missing}"

    def test_sprint_key_matches_filename(self, sprint):
        contract = _load(sprint)
        assert (
            contract.get("sprint") == sprint
        ), f"{sprint}: sprint key '{contract.get('sprint')}' does not match filename"

    def test_model_tier_valid(self, sprint):
        contract = _load(sprint)
        tier = contract.get("model_tier")
        assert tier in _VALID_MODEL_TIERS, f"{sprint}: model_tier '{tier}' not in {_VALID_MODEL_TIERS}"

    def test_dependencies_is_list(self, sprint):
        contract = _load(sprint)
        deps = contract.get("dependencies")
        assert isinstance(deps, list), f"{sprint}: dependencies must be a list"


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestOutputSchema:
    def test_required_output_schema_keys(self, sprint):
        schema = _load(sprint).get("output_schema", {})
        missing = _REQUIRED_OUTPUT_SCHEMA_KEYS - set(schema.keys())
        assert not missing, f"{sprint}: output_schema missing {missing}"

    def test_no_non_standard_schema_keys(self, sprint):
        schema = _load(sprint).get("output_schema", {})
        bad = _NON_STANDARD_SCHEMA_KEYS & set(schema.keys())
        assert not bad, (
            f"{sprint}: output_schema has non-standard keys {bad} — " "these are silently ignored by the harness"
        )

    def test_field_types_no_dot_notation(self, sprint):
        field_types = _load(sprint).get("output_schema", {}).get("field_types", {})
        dot_keys = [k for k in field_types if "." in k]
        assert not dot_keys, (
            f"{sprint}: field_types has dot-notation keys {dot_keys} — " "harness only validates top-level keys"
        )

    def test_required_fields_is_list(self, sprint):
        schema = _load(sprint).get("output_schema", {})
        rf = schema.get("required_fields")
        assert isinstance(rf, list) and len(rf) > 0, f"{sprint}: required_fields must be a non-empty list"


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestGroundingChecks:
    def test_grounding_checks_is_list(self, sprint):
        checks = _load(sprint).get("grounding_checks")
        assert isinstance(checks, list), f"{sprint}: grounding_checks must be a list"

    def test_grounding_check_required_fields(self, sprint):
        checks = _load(sprint).get("grounding_checks", [])
        for i, check in enumerate(checks):
            missing = _REQUIRED_GROUNDING_CHECK_KEYS - set(check.keys())
            assert not missing, f"{sprint}: grounding_checks[{i}] (id='{check.get('id', '?')}') " f"missing {missing}"

    def test_grounding_check_severity_valid(self, sprint):
        checks = _load(sprint).get("grounding_checks", [])
        for check in checks:
            sev = check.get("severity")
            assert sev in ("hard", "soft"), (
                f"{sprint}: grounding check '{check.get('id')}' " f"has invalid severity '{sev}'"
            )


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestCrossReferences:
    def test_cross_references_is_list(self, sprint):
        refs = _load(sprint).get("cross_references")
        assert isinstance(refs, list), f"{sprint}: cross_references must be a list"

    def test_cross_reference_required_fields(self, sprint):
        refs = _load(sprint).get("cross_references", [])
        for i, ref in enumerate(refs):
            missing = _REQUIRED_CROSS_REF_KEYS - set(ref.keys())
            assert not missing, (
                f"{sprint}: cross_references[{i}] (check='{ref.get('check', '?')}') " f"missing {missing}"
            )


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestLlmEvalCriteria:
    def test_llm_eval_criteria_is_dict(self, sprint):
        criteria = _load(sprint).get("llm_eval_criteria")
        assert isinstance(criteria, dict), f"{sprint}: llm_eval_criteria must be a dict, got {type(criteria).__name__}"

    def test_llm_eval_criteria_not_empty(self, sprint):
        criteria = _load(sprint).get("llm_eval_criteria", {})
        assert len(criteria) >= 3, f"{sprint}: llm_eval_criteria has only {len(criteria)} dimensions (min 3)"

    def test_llm_eval_criteria_required_keys(self, sprint):
        criteria = _load(sprint).get("llm_eval_criteria", {})
        for name, dim in criteria.items():
            for key in ("weight", "prompt", "score_5", "score_3", "score_1"):
                assert key in dim, f"{sprint}: llm_eval_criteria['{name}'] missing '{key}'"

    def test_llm_eval_weights_sum_to_max(self, sprint):
        contract = _load(sprint)
        criteria = contract.get("llm_eval_criteria", {})
        pt = contract.get("pass_threshold", {})
        max_score = pt.get("llm_score_maximum", 20)
        total = sum(dim.get("weight", 0) for dim in criteria.values())
        assert total == max_score, (
            f"{sprint}: llm_eval_criteria weights sum to {total}, " f"expected {max_score} (llm_score_maximum)"
        )


@pytest.mark.unit
@pytest.mark.parametrize("sprint", ALL_SPRINTS)
class TestPassThreshold:
    def test_pass_threshold_required_keys(self, sprint):
        pt = _load(sprint).get("pass_threshold", {})
        missing = _REQUIRED_PASS_THRESHOLD_KEYS - set(pt.keys())
        assert not missing, f"{sprint}: pass_threshold missing {missing}"

    def test_pass_threshold_score_bounds_valid(self, sprint):
        pt = _load(sprint).get("pass_threshold", {})
        min_score = pt.get("llm_score_minimum", 0)
        max_score = pt.get("llm_score_maximum", 20)
        assert 0 <= min_score <= max_score, f"{sprint}: invalid score bounds min={min_score} max={max_score}"
