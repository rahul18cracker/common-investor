"""Tests for the state_manager module."""

import json

import pytest

from app.nlp.research_agent.harness.state_manager import (
    SPRINT_DEPENDENCIES,
    SPRINT_NAMES,
    StateManager,
)


@pytest.fixture
def sm(tmp_path):
    return StateManager("AAPL", state_root=tmp_path)


class TestInitRun:
    def test_creates_directory_tree(self, sm):
        root = sm.init_run()
        assert root.exists()
        for sprint in SPRINT_NAMES:
            assert (root / "sprints" / sprint).is_dir()
        assert (root / "final").is_dir()

    def test_creates_manifest(self, sm):
        sm.init_run()
        manifest = sm.read_manifest()
        assert manifest["ticker"] == "AAPL"
        assert manifest["status"] == "running"
        assert manifest["total_cost_usd"] == 0.0
        assert manifest["sprints"] == {}
        assert manifest["started_at"] is not None
        assert manifest["completed_at"] is None

    def test_idempotent(self, sm):
        sm.init_run()
        sm.init_run()
        assert sm.read_manifest()["ticker"] == "AAPL"

    def test_ticker_uppercased(self, tmp_path):
        sm = StateManager("aapl", state_root=tmp_path)
        root = sm.init_run()
        assert root.name == "AAPL"
        assert sm.read_manifest()["ticker"] == "AAPL"


class TestManifestLifecycle:
    def test_update_manifest_merges_keys(self, sm):
        sm.init_run()
        sm.update_manifest({"model_routing": {"01_business_profile": "haiku"}})
        manifest = sm.read_manifest()
        assert manifest["model_routing"] == {"01_business_profile": "haiku"}
        assert manifest["status"] == "running"

    def test_update_sprint_in_manifest(self, sm):
        sm.init_run()
        sprint_data = {
            "status": "passed",
            "model": "haiku",
            "attempts": 1,
            "cost_usd": 0.04,
            "duration_seconds": 45,
            "eval_score": 18,
            "grounding_contradictions": 0,
        }
        sm.update_sprint_in_manifest("01_business_profile", sprint_data)
        manifest = sm.read_manifest()
        assert manifest["sprints"]["01_business_profile"]["status"] == "passed"
        assert manifest["total_cost_usd"] == 0.04

    def test_total_cost_sums_across_sprints(self, sm):
        sm.init_run()
        sm.update_sprint_in_manifest("01_business_profile", {"cost_usd": 0.04})
        sm.update_sprint_in_manifest("02_unit_economics", {"cost_usd": 0.07})
        manifest = sm.read_manifest()
        assert abs(manifest["total_cost_usd"] - 0.11) < 1e-9

    def test_complete_run(self, sm):
        sm.init_run()
        manifest = sm.complete_run()
        assert manifest["status"] == "completed"
        assert manifest["completed_at"] is not None
        assert manifest["total_duration_seconds"] >= 0

    def test_complete_run_custom_status(self, sm):
        sm.init_run()
        manifest = sm.complete_run(status="aborted")
        assert manifest["status"] == "aborted"


class TestSprintFileIO:
    def test_write_and_read_builder_output(self, sm):
        sm.init_run()
        data = {"ticker": "AAPL", "narrative": "Apple sells iPhones."}
        sm.write_builder_output("01_business_profile", data)
        assert sm.read_builder_output("01_business_profile") == data

    def test_write_and_read_eval_result(self, sm):
        sm.init_run()
        data = {"sprint": "01_business_profile", "pass": True}
        sm.write_eval_result("01_business_profile", data)
        assert sm.read_eval_result("01_business_profile") == data

    def test_write_builder_trace(self, sm):
        sm.init_run()
        trace = {"model": "haiku", "input_tokens": 5000}
        path = sm.write_builder_trace("01_business_profile", trace)
        assert json.loads(path.read_text()) == trace

    def test_copy_contract(self, sm):
        sm.init_run()
        dst = sm.copy_contract("01_business_profile")
        assert dst.exists()
        contract = json.loads(dst.read_text())
        assert contract["sprint"] == "01_business_profile"


class TestSharedInputFiles:
    def test_agent_bundle_roundtrip(self, sm):
        sm.init_run()
        bundle = {"company": {"ticker": "AAPL"}, "metrics": {}}
        sm.write_agent_bundle(bundle)
        assert sm.read_agent_bundle() == bundle

    def test_item1_text_roundtrip(self, sm):
        sm.init_run()
        text = "Apple Inc. designs, manufactures, and markets smartphones."
        sm.write_item1_text(text)
        assert sm.read_item1_text() == text


class TestFinalOutputFiles:
    def test_write_executive_brief(self, sm):
        sm.init_run()
        md = "# AAPL Executive Brief\n\nApple is a technology company."
        path = sm.write_executive_brief(md)
        assert path.read_text() == md
        assert path.parent.name == "final"

    def test_write_quality_summary(self, sm):
        sm.init_run()
        summary = {"quality_score": 72, "confidence": "medium"}
        path = sm.write_quality_summary(summary)
        assert json.loads(path.read_text()) == summary


class TestDependencyResolution:
    def test_no_deps_for_first_sprint(self, sm):
        sm.init_run()
        assert sm.read_prior_outputs("01_business_profile") == {}

    def test_reads_available_deps(self, sm):
        sm.init_run()
        bp = {"ticker": "AAPL", "narrative": "Apple sells iPhones."}
        sm.write_builder_output("01_business_profile", bp)
        prior = sm.read_prior_outputs("02_unit_economics")
        assert "01_business_profile" in prior
        assert prior["01_business_profile"] == bp

    def test_skips_missing_deps(self, sm):
        sm.init_run()
        prior = sm.read_prior_outputs("04_moat")
        assert prior == {}

    def test_partial_deps(self, sm):
        sm.init_run()
        bp = {"ticker": "AAPL"}
        sm.write_builder_output("01_business_profile", bp)
        prior = sm.read_prior_outputs("04_moat")
        assert list(prior.keys()) == ["01_business_profile"]


class TestRunExists:
    def test_false_before_init(self, sm):
        assert not sm.run_exists()

    def test_true_after_init(self, sm):
        sm.init_run()
        assert sm.run_exists()


class TestSprintDependencies:
    def test_all_sprints_have_dependency_entry(self):
        for sprint in SPRINT_NAMES:
            assert sprint in SPRINT_DEPENDENCIES

    def test_first_sprint_has_no_deps(self):
        assert SPRINT_DEPENDENCIES["01_business_profile"] == []

    def test_thesis_depends_on_all_prior(self):
        assert len(SPRINT_DEPENDENCIES["08_thesis"]) == 7

    def test_no_circular_deps(self):
        for sprint, deps in SPRINT_DEPENDENCIES.items():
            assert sprint not in deps
