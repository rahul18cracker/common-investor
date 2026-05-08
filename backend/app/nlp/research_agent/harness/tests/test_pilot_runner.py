"""Unit tests for pilot_runner metric aggregation logic."""

from __future__ import annotations

import csv
from typing import Any

import pytest

from app.nlp.research_agent.harness.pilot_runner import (
    _build_csv_row,
    _collect_sprint_metrics,
    _get_industry,
    _write_csv_row,
)


def _sprint(status: str, eval_score: int = 0, contradictions: int = 0) -> dict[str, Any]:
    return {"status": status, "eval_score": eval_score, "grounding_contradictions": contradictions}


def _manifest(
    sprints: dict[str, Any], status: str = "completed", cost: float = 0.12, duration: float = 120.0
) -> dict[str, Any]:
    return {
        "status": status,
        "total_cost_usd": cost,
        "total_duration_seconds": duration,
        "sprints": sprints,
    }


@pytest.mark.unit
class TestGetIndustry:
    def test_returns_industry_category(self):
        bundle = {"company": {"industry_category": "technology"}}
        assert _get_industry(bundle) == "technology"

    def test_missing_company_returns_unknown(self):
        assert _get_industry({}) == "unknown"

    def test_missing_industry_key_returns_unknown(self):
        assert _get_industry({"company": {}}) == "unknown"

    def test_none_value_returns_unknown(self):
        assert _get_industry({"company": {"industry_category": None}}) == "unknown"


@pytest.mark.unit
class TestCollectSprintMetrics:
    def test_all_passed(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("passed", eval_score=14, contradictions=0),
                "02_unit_economics": _sprint("passed", eval_score=12, contradictions=1),
            }
        )
        passed, degraded, incomplete, tainted, quality, groundings = _collect_sprint_metrics(manifest)
        assert passed == 2
        assert degraded == 0
        assert incomplete == 0
        assert tainted == 0
        assert quality == 13.0
        assert groundings == 1

    def test_mixed_statuses(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("passed", eval_score=14),
                "02_unit_economics": _sprint("degraded", eval_score=8),
                "03_industry": _sprint("data_incomplete"),
                "04_moat": _sprint("skipped"),
                "05_management": _sprint("no_contract"),
                "06_peers": _sprint("tainted_suspicious"),
                "07_risks": _sprint("tainted_blocked"),
            }
        )
        passed, degraded, incomplete, tainted, quality, groundings = _collect_sprint_metrics(manifest)
        assert passed == 1
        assert degraded == 1
        assert incomplete == 1
        assert tainted == 2

    def test_skipped_and_no_contract_not_counted(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("skipped"),
                "02_unit_economics": _sprint("no_contract"),
            }
        )
        passed, degraded, incomplete, tainted, quality, groundings = _collect_sprint_metrics(manifest)
        assert passed == 0
        assert degraded == 0
        assert incomplete == 0
        assert tainted == 0

    def test_evidence_quality_only_from_passed_and_degraded(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("passed", eval_score=16),
                "02_unit_economics": _sprint("degraded", eval_score=6),
                "03_industry": _sprint("data_incomplete", eval_score=99),
                "04_moat": _sprint("skipped", eval_score=99),
            }
        )
        _, _, _, _, quality, _ = _collect_sprint_metrics(manifest)
        assert quality == 11.0

    def test_no_passed_or_degraded_returns_zero_quality(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("data_incomplete"),
                "02_unit_economics": _sprint("skipped"),
            }
        )
        _, _, _, _, quality, _ = _collect_sprint_metrics(manifest)
        assert quality == 0.0

    def test_grounding_contradictions_summed(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("passed", contradictions=2),
                "02_unit_economics": _sprint("passed", contradictions=1),
                "03_industry": _sprint("degraded", contradictions=3),
            }
        )
        _, _, _, _, _, groundings = _collect_sprint_metrics(manifest)
        assert groundings == 6

    def test_empty_sprints(self):
        manifest = _manifest({})
        passed, degraded, incomplete, tainted, quality, groundings = _collect_sprint_metrics(manifest)
        assert passed == 0
        assert degraded == 0
        assert quality == 0.0
        assert groundings == 0


@pytest.mark.unit
class TestBuildCsvRow:
    def test_normal_manifest(self):
        manifest = _manifest(
            {
                "01_business_profile": _sprint("passed", eval_score=14),
                "02_unit_economics": _sprint("passed", eval_score=12),
            },
            cost=0.0235,
            duration=180.0,
        )
        row = _build_csv_row("AAPL", "technology", manifest)
        assert row["ticker"] == "AAPL"
        assert row["industry"] == "technology"
        assert row["status"] == "completed"
        assert row["total_cost"] == 0.0235
        assert row["duration_min"] == 3.0
        assert row["sprints_passed"] == 2
        assert row["sprints_degraded"] == 0
        assert row["cache_hit_rate"] == 0.0

    def test_fetch_failed_error(self):
        row = _build_csv_row("JPM", "banking", error="fetch_failed")
        assert row["status"] == "fetch_failed"
        assert row["total_cost"] == 0.0
        assert row["sprints_passed"] == 0
        assert row["evidence_quality_avg"] == 0.0

    def test_exception_error(self):
        row = _build_csv_row("WMT", "retail", error="exception")
        assert row["status"] == "exception"
        assert row["sprints_degraded"] == 0

    def test_manifest_none_uses_error_status(self):
        row = _build_csv_row("MSFT", "technology", manifest=None)
        assert row["status"] == "error"
        assert row["total_cost"] == 0.0

    def test_duration_converted_from_seconds_to_minutes(self):
        manifest = _manifest({}, duration=120.0)
        row = _build_csv_row("SBUX", "consumer", manifest)
        assert row["duration_min"] == 2.0

    def test_cost_rounded_to_four_decimal_places(self):
        manifest = _manifest({}, cost=0.123456789)
        row = _build_csv_row("AAPL", "technology", manifest)
        assert row["total_cost"] == 0.1235


@pytest.mark.unit
class TestWriteCsvRow:
    def test_writes_header_and_rows(self, tmp_path):
        csv_path = tmp_path / "pilot_metrics.csv"
        rows = [
            {
                "ticker": "AAPL",
                "industry": "technology",
                "status": "completed",
                "total_cost": 0.18,
                "duration_min": 4.2,
                "sprints_passed": 8,
                "sprints_degraded": 0,
                "sprints_data_incomplete": 0,
                "sprints_tainted": 0,
                "evidence_quality_avg": 13.5,
                "grounding_contradictions": 0,
                "cache_hit_rate": 0.0,
            }
        ]
        _write_csv_row(csv_path, rows)

        assert csv_path.exists()
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            written = list(reader)
        assert len(written) == 1
        assert written[0]["ticker"] == "AAPL"
        assert written[0]["sprints_passed"] == "8"

    def test_overwrites_on_second_call(self, tmp_path):
        csv_path = tmp_path / "pilot_metrics.csv"
        row1 = {
            "ticker": "AAPL",
            "industry": "tech",
            "status": "completed",
            "total_cost": 0.1,
            "duration_min": 1.0,
            "sprints_passed": 8,
            "sprints_degraded": 0,
            "sprints_data_incomplete": 0,
            "sprints_tainted": 0,
            "evidence_quality_avg": 13.0,
            "grounding_contradictions": 0,
            "cache_hit_rate": 0.0,
        }
        row2 = {**row1, "ticker": "WMT", "industry": "retail"}

        _write_csv_row(csv_path, [row1])
        _write_csv_row(csv_path, [row1, row2])

        with csv_path.open() as f:
            reader = csv.DictReader(f)
            written = list(reader)
        assert len(written) == 2
        assert written[1]["ticker"] == "WMT"

    def test_empty_rows_does_not_write(self, tmp_path):
        csv_path = tmp_path / "pilot_metrics.csv"
        _write_csv_row(csv_path, [])
        assert not csv_path.exists()
