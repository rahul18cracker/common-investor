"""Tests for the orchestrator module — build/eval/retry loop integration."""

import json

import pytest

from app.nlp.research_agent.harness.cost_tracker import CostTracker
from app.nlp.research_agent.harness.orchestrator import (
    _collect_failures,
    run_all_sprints,
    run_sprint,
)
from app.nlp.research_agent.harness.state_manager import StateManager


# --- Fixtures ---

SAMPLE_AGENT_BUNDLE = {
    "company": {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc"},
    "metrics": {
        "growths_extended": {"rev_cagr_5y": 0.08},
        "roic_avg_10y": 0.25,
        "latest_operating_margin": 0.30,
        "latest_fcf_margin": 0.26,
    },
    "timeseries": {
        "is": [{"fiscal_year": 2023, "revenue": 383000000000}],
    },
}

SAMPLE_ITEM1 = (
    "Apple Inc. designs, manufactures, and markets smartphones, personal computers, "
    "tablets, wearables, and accessories worldwide. The Company also sells various "
    "related services including subscriptions and support."
)

GOOD_BUILDER_OUTPUT = {
    "ticker": "AAPL",
    "name": "Apple Inc",
    "reporting_currency": "USD",
    "products_services": ["iPhone", "Mac", "iPad", "Services"],
    "customer_segments": ["consumers", "enterprise"],
    "geographies": ["Americas", "Europe", "Greater China"],
    "pricing_model": ["one_time", "subscription"],
    "revenue_drivers": ["iPhone sales", "Services revenue", "Mac sales"],
    "recurrence_mechanisms": ["ecosystem", "contracts"],
    "distribution_channels": ["retail stores", "online", "carriers"],
    "narrative": (
        "Apple Inc. designs, manufactures, and markets smartphones, personal "
        "computers, tablets, wearables, and accessories worldwide. The company "
        "offers iPhone, Mac, iPad, and wearables as its primary hardware products. "
        "Services revenue, including the App Store, Apple Music, iCloud, and "
        "Apple TV+, represents a growing high-margin segment. Revenue is driven "
        "primarily by iPhone sales (approximately 52% of total revenue), Services "
        "(22%), and Mac/iPad/wearables (26%). The company operates through direct "
        "retail stores, online channels, and third-party distributors globally. "
        "Recurrence is driven by the Apple ecosystem lock-in and multi-year "
        "carrier contracts for iPhone. Pricing model is primarily one-time "
        "hardware sales with growing subscription services revenue."
    ),
}


def _make_builder_llm(output=None, fail_first_n=0):
    """Create a mock builder LLM that returns JSON output."""
    call_count = [0]
    response = output or GOOD_BUILDER_OUTPUT

    def mock_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
        call_count[0] += 1
        if call_count[0] <= fail_first_n:
            return "not valid json"
        return json.dumps(response)

    mock_llm.call_count = call_count
    return mock_llm


def _make_evaluator_llm(pass_eval=True):
    """Create a mock evaluator LLM that returns pass/fail scores."""
    score = 4 if pass_eval else 1

    def mock_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
        return json.dumps({
            "evidence_quality": {"score": score, "notes": "test"},
            "completeness": {"score": score, "notes": "test"},
            "consistency": {"score": score, "notes": "test"},
            "red_flags": {"score": score, "notes": "test"},
            "failures": [] if pass_eval else ["Test failure"],
        })

    return mock_llm


@pytest.fixture
def state(tmp_path):
    sm = StateManager("AAPL", state_root=tmp_path)
    sm.init_run()
    sm.write_agent_bundle(SAMPLE_AGENT_BUNDLE)
    sm.write_item1_text(SAMPLE_ITEM1)
    sm.copy_contract("01_business_profile")
    return sm


# --- run_sprint ---


class TestRunSprint:
    def test_pass_on_first_attempt(self, state):
        ct = CostTracker()
        result = run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
        )
        assert result["status"] == "passed"
        assert result["attempts"] == 1
        assert result["eval_score"] == 16

        manifest = state.read_manifest()
        assert "01_business_profile" in manifest["sprints"]
        assert manifest["sprints"]["01_business_profile"]["status"] == "passed"

    def test_retry_on_builder_failure(self, state):
        ct = CostTracker()
        result = run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(fail_first_n=1),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
        )
        assert result["status"] == "passed"
        assert result["attempts"] == 2

    def test_degraded_after_all_attempts(self, state):
        ct = CostTracker()
        result = run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(fail_first_n=10),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
        )
        assert result["status"] == "degraded"
        assert result["attempts"] == 3

    def test_degraded_on_eval_failure(self, state):
        ct = CostTracker()
        result = run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=False),
        )
        assert result["status"] == "degraded"
        assert result["attempts"] == 3

    def test_skip_retries(self, state):
        ct = CostTracker()
        result = run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=False),
            skip_retries=True,
        )
        assert result["status"] == "degraded"
        assert result["attempts"] == 1

    def test_state_files_written(self, state):
        ct = CostTracker()
        run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
        )
        sprint_dir = state.sprint_dir("01_business_profile")
        assert (sprint_dir / "builder_output.json").exists()
        assert (sprint_dir / "eval_result.json").exists()
        assert (sprint_dir / "builder_trace.json").exists()

    def test_cost_tracked(self, state):
        ct = CostTracker()
        run_sprint(
            "01_business_profile", state, ct,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
        )
        assert ct.sprint_cost("01_business_profile") >= 0


# --- run_all_sprints ---


class TestRunAllSprints:
    def test_single_sprint(self, tmp_path):
        manifest = run_all_sprints(
            ticker="AAPL",
            agent_bundle=SAMPLE_AGENT_BUNDLE,
            item1_text=SAMPLE_ITEM1,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
            state_root=tmp_path,
            sprint_names=["01_business_profile"],
        )
        assert manifest["status"] == "completed"
        assert manifest["ticker"] == "AAPL"
        assert "01_business_profile" in manifest["sprints"]
        assert manifest["sprints"]["01_business_profile"]["status"] == "passed"

    def test_multiple_sprints(self, tmp_path):
        manifest = run_all_sprints(
            ticker="AAPL",
            agent_bundle=SAMPLE_AGENT_BUNDLE,
            item1_text=SAMPLE_ITEM1,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
            state_root=tmp_path,
            sprint_names=["01_business_profile", "02_unit_economics"],
        )
        assert manifest["status"] == "completed"
        assert len(manifest["sprints"]) == 2

    def test_state_directory_created(self, tmp_path):
        run_all_sprints(
            ticker="AAPL",
            agent_bundle=SAMPLE_AGENT_BUNDLE,
            item1_text=SAMPLE_ITEM1,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
            state_root=tmp_path,
            sprint_names=["01_business_profile"],
        )
        assert (tmp_path / "AAPL" / "manifest.json").exists()
        assert (tmp_path / "AAPL" / "agent_bundle.json").exists()
        assert (tmp_path / "AAPL" / "item1_text.txt").exists()

    def test_degraded_sprint_does_not_block_pipeline(self, tmp_path):
        manifest = run_all_sprints(
            ticker="AAPL",
            agent_bundle=SAMPLE_AGENT_BUNDLE,
            item1_text=SAMPLE_ITEM1,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=False),
            state_root=tmp_path,
            sprint_names=["01_business_profile", "02_unit_economics"],
        )
        assert manifest["status"] == "completed"
        assert manifest["sprints"]["01_business_profile"]["status"] == "degraded"
        assert manifest["sprints"]["02_unit_economics"]["status"] == "degraded"

    def test_completed_at_set(self, tmp_path):
        manifest = run_all_sprints(
            ticker="AAPL",
            agent_bundle=SAMPLE_AGENT_BUNDLE,
            item1_text=SAMPLE_ITEM1,
            builder_llm=_make_builder_llm(),
            evaluator_llm=_make_evaluator_llm(pass_eval=True),
            state_root=tmp_path,
            sprint_names=["01_business_profile"],
        )
        assert manifest["completed_at"] is not None
        assert manifest["total_duration_seconds"] >= 0


# --- _collect_failures ---


class TestCollectFailures:
    def test_deterministic_failures(self):
        eval_result = {
            "deterministic_checks": {"details": ["Missing field: ticker"]},
            "cross_reference_checks": {"details": []},
            "grounding_checks": {"details": []},
            "llm_evaluation": {"failures": []},
        }
        assert "Missing field: ticker" in _collect_failures(eval_result)

    def test_grounding_failures(self):
        eval_result = {
            "deterministic_checks": {"details": []},
            "cross_reference_checks": {"details": []},
            "grounding_checks": {
                "details": [
                    {"passed": False, "details": "Growth claim contradicted"},
                    {"passed": True, "details": "OK"},
                ],
            },
            "llm_evaluation": {"failures": []},
        }
        failures = _collect_failures(eval_result)
        assert "Growth claim contradicted" in failures
        assert len(failures) == 1

    def test_llm_failures(self):
        eval_result = {
            "deterministic_checks": {"details": []},
            "cross_reference_checks": {"details": []},
            "grounding_checks": {"details": []},
            "llm_evaluation": {"failures": ["Vague revenue drivers"]},
        }
        assert "Vague revenue drivers" in _collect_failures(eval_result)

    def test_empty_eval_result(self):
        assert _collect_failures({}) == []

    def test_multiple_failure_types(self):
        eval_result = {
            "deterministic_checks": {"details": ["Missing field"]},
            "cross_reference_checks": {"details": ["Ticker mismatch"]},
            "grounding_checks": {
                "details": [{"passed": False, "details": "Bad growth claim"}],
            },
            "llm_evaluation": {"failures": ["Weak evidence"]},
        }
        failures = _collect_failures(eval_result)
        assert len(failures) == 4
