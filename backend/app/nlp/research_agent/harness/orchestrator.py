"""Sprint orchestrator for the qualitative agent harness.

Drives the build -> evaluate -> retry loop for one or more sprints.
Coordinates state_manager, cost_tracker, builder, and evaluator.
Enforces budget and timeout guards. Writes all state to disk.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

from app.nlp.research_agent.harness.builder import build
from app.nlp.research_agent.harness.cost_tracker import (
    BudgetExceeded,
    CostTracker,
)
from app.nlp.research_agent.harness.evaluator import evaluate
from app.nlp.research_agent.harness.state_manager import (
    SPRINT_NAMES,
    StateManager,
)
from app.nlp.research_agent.harness.data_fetcher import DataFetcher
from app.nlp.research_agent.harness.data_validator import (
    validate_agent_bundle,
    validate_item1_text,
    check_sprint_readiness,
)
from app.nlp.research_agent.harness.sanitizer import (
    sanitize_agent_bundle,
    sanitize_prior_outputs,
    sanitize_text,
)

logger = logging.getLogger(__name__)

# Sprint dependency graph: each sprint's required predecessors
SPRINT_DEPENDENCIES: dict[str, list[str]] = {
    "01_business_profile": [],
    "02_unit_economics": ["01_business_profile"],
    "03_industry": ["01_business_profile"],
    "04_moat": ["01_business_profile", "02_unit_economics"],
    "05_management": ["01_business_profile"],
    "06_peers": ["03_industry"],
    "07_risks": ["04_moat", "05_management"],
    "08_thesis": ["04_moat", "05_management", "06_peers", "07_risks"],
}

RUN_TIMEOUT_SECONDS = 900  # 15 minutes


def run_sprint(
    sprint_name: str,
    state: StateManager,
    cost_tracker: CostTracker,
    builder_llm: Callable[[str, str], str],
    evaluator_llm: Callable[[str, str], str],
    skip_retries: bool = False,
) -> dict[str, Any]:
    """Run a single sprint: build -> evaluate -> retry loop.

    Returns the sprint result dict (written to manifest).
    """
    contract = state.read_json(state.sprint_dir(sprint_name) / "contract.json")
    max_retries = 0 if skip_retries else contract.get("max_retries", 2)
    max_attempts = max_retries + 1

    agent_bundle = state.read_agent_bundle()
    item1_text = state.read_item1_text()
    prior_outputs = state.read_prior_outputs(sprint_name)

    sprint_start = time.time()
    eval_failures: list[str] = []
    last_eval_result: dict[str, Any] = {}
    model_routing: dict[str, str] = {}

    for attempt in range(1, max_attempts + 1):
        # Escalate to sonnet on final attempt if prior haiku attempts all failed
        effective_model = contract.get("model_tier", "haiku")
        if attempt == max_attempts and attempt > 1 and effective_model == "haiku":
            effective_model = "sonnet"
            logger.info("Sprint %s: escalating to sonnet on final attempt", sprint_name)

        # Use with_model if available (AnthropicLLMClient), otherwise use llm_call directly
        actual_llm = getattr(builder_llm, "with_model", lambda m: builder_llm)(effective_model)
        model_routing[f"attempt_{attempt}"] = effective_model

        # Build
        builder_result = build(
            contract=contract,
            agent_bundle=agent_bundle,
            item1_text=item1_text,
            prior_outputs=prior_outputs,
            eval_failures=eval_failures if attempt > 1 else None,
            attempt=attempt,
            llm_call=actual_llm,
        )

        cost_tracker.record_builder_usage(
            sprint_name,
            builder_result.model,
            builder_result.input_tokens,
            builder_result.output_tokens,
            builder_result.cached_tokens,
        )

        if not builder_result.success or builder_result.output is None:
            eval_failures = [f"Builder failed to produce valid JSON (attempt {attempt})"]
            state.write_builder_trace(sprint_name, {
                "model": builder_result.model,
                "input_tokens": builder_result.input_tokens,
                "output_tokens": builder_result.output_tokens,
                "cached_tokens": builder_result.cached_tokens,
                "duration_seconds": builder_result.duration_seconds,
                "attempt": attempt,
                "error": True,
                "raw_response_preview": builder_result.raw_response[:500],
            })
            logger.warning(
                "Sprint %s attempt %d: builder failed", sprint_name, attempt
            )
            continue

        # Write builder output
        state.write_builder_output(sprint_name, builder_result.output)

        # Write builder trace
        state.write_builder_trace(sprint_name, {
            "model": builder_result.model,
            "input_tokens": builder_result.input_tokens,
            "output_tokens": builder_result.output_tokens,
            "cached_tokens": builder_result.cached_tokens,
            "duration_seconds": builder_result.duration_seconds,
            "attempt": attempt,
        })

        # Evaluate
        eval_result = evaluate(
            builder_output=builder_result.output,
            agent_bundle=agent_bundle,
            contract=contract,
            item1_text=item1_text,
            llm_call=evaluator_llm,
        )
        last_eval_result = eval_result

        cost_tracker.record_eval_usage(
            sprint_name,
            "haiku",
            0,
            0,
        )

        # Write eval result
        state.write_eval_result(sprint_name, eval_result)

        if eval_result["pass"]:
            duration = time.time() - sprint_start
            sprint_data = {
                "status": "passed",
                "model": builder_result.model,
                "attempts": attempt,
                "cost_usd": cost_tracker.sprint_cost(sprint_name),
                "duration_seconds": round(duration, 2),
                "eval_score": eval_result.get("llm_evaluation", {}).get("overall", 0),
                "grounding_contradictions": eval_result.get(
                    "grounding_checks", {}
                ).get("contradictions_found", 0),
                "model_routing": model_routing,
            }
            state.update_sprint_in_manifest(sprint_name, sprint_data)
            logger.info(
                "Sprint %s passed on attempt %d (score: %d)",
                sprint_name, attempt,
                sprint_data["eval_score"],
            )
            return sprint_data

        # Collect failures for retry
        eval_failures = _collect_failures(eval_result)
        logger.info(
            "Sprint %s attempt %d failed: %s",
            sprint_name, attempt, eval_failures,
        )

    # All attempts exhausted — mark degraded
    duration = time.time() - sprint_start
    sprint_data = {
        "status": "degraded",
        "model": contract.get("model_tier", "haiku"),
        "attempts": max_attempts,
        "cost_usd": cost_tracker.sprint_cost(sprint_name),
        "duration_seconds": round(duration, 2),
        "eval_score": last_eval_result.get("llm_evaluation", {}).get("overall", 0),
        "grounding_contradictions": last_eval_result.get(
            "grounding_checks", {}
        ).get("contradictions_found", 0),
        "failure_reasons": eval_failures,
        "model_routing": model_routing,
    }
    state.update_sprint_in_manifest(sprint_name, sprint_data)
    logger.warning("Sprint %s degraded after %d attempts", sprint_name, max_attempts)
    return sprint_data


def run_all_sprints(
    ticker: str,
    agent_bundle: dict[str, Any] | None = None,
    item1_text: str | None = None,
    builder_llm: Callable[[str, str], str] | None = None,
    evaluator_llm: Callable[[str, str], str] | None = None,
    state_root: Path | None = None,
    sprint_names: list[str] | None = None,
    base_url: str = "http://localhost:8080/api/v1",
) -> dict[str, Any]:
    """Run the full pipeline for a ticker.

    Returns the final manifest.
    """
    # Step 1: Fetch data if not provided
    if agent_bundle is None or item1_text is None:
        fetcher = DataFetcher(base_url=base_url)
        fetch_result = fetcher.fetch_all(ticker)
        if not fetch_result.success:
            errors = "\n  - ".join(fetch_result.errors)
            logger.error("Could not fetch live data:\n  - %s", errors)
            return {"status": "fetch_failed", "errors": fetch_result.errors}
        agent_bundle = fetch_result.agent_bundle
        item1_text = fetch_result.item1_text

    # Step 2: Validate schema
    bundle_issues = validate_agent_bundle(agent_bundle)
    item1_issues = validate_item1_text(item1_text)
    if bundle_issues or item1_issues:
        all_issues = bundle_issues + item1_issues
        logger.error("Data validation failed: %s", all_issues)
        return {"status": "validation_failed", "issues": all_issues}

    # Step 3: Sanitize
    sanitized_bundle, bundle_flagged = sanitize_agent_bundle(agent_bundle)
    item1_result = sanitize_text(item1_text, max_length=30000, field_path="item1_text")

    taint_flags: list[dict] = []
    if bundle_flagged:
        taint_flags.extend([{"source": "bundle", "action": r.action, "details": r.details} for r in bundle_flagged])
    if item1_result.action == "blocked":
        logger.error("Item1 text hard-blocked by sanitizer. Aborting run.")
        return {"status": "tainted_blocked", "taint_details": item1_result.details}
    if item1_result.action == "suspicious":
        taint_flags.append({"source": "item1_text", "action": "suspicious", "details": item1_result.details})

    sanitized_item1 = item1_result.sanitized_text

    # Step 4: Write sanitized data to disk
    state = StateManager(ticker, state_root=state_root)
    state.init_run()
    state.write_agent_bundle(sanitized_bundle)
    state.write_item1_text(sanitized_item1)
    if taint_flags:
        state.update_manifest({"taint_flags": taint_flags})

    cost_tracker = CostTracker()
    sprints_to_run = sprint_names or SPRINT_NAMES
    run_start = time.time()

    for sprint_name in sprints_to_run:
        # Per-sprint data readiness gate
        readiness = check_sprint_readiness(sprint_name, sanitized_bundle, sanitized_item1)
        if not readiness.ready:
            logger.warning(
                "Sprint %s skipped: missing data fields: %s",
                sprint_name, readiness.missing_fields,
            )
            state.update_sprint_in_manifest(sprint_name, {
                "status": "data_incomplete",
                "missing_fields": readiness.missing_fields,
                "warnings": readiness.warnings,
            })
            continue
        if readiness.warnings:
            logger.info("Sprint %s data warnings: %s", sprint_name, readiness.warnings)

        # Copy frozen contract
        state.copy_contract(sprint_name)

        # Budget check
        skip_retries = cost_tracker.is_soft_exceeded()
        try:
            cost_tracker.check_budget()
        except BudgetExceeded:
            logger.error("Hard budget exceeded at sprint %s, aborting", sprint_name)
            _mark_remaining_skipped(state, sprint_name, sprints_to_run)
            return state.complete_run(status="budget_exceeded")

        # Timeout check
        elapsed = time.time() - run_start
        if elapsed > RUN_TIMEOUT_SECONDS:
            logger.error("Run timeout at sprint %s (%.0fs)", sprint_name, elapsed)
            _mark_remaining_skipped(state, sprint_name, sprints_to_run)
            return state.complete_run(status="timeout")

        run_sprint(
            sprint_name=sprint_name,
            state=state,
            cost_tracker=cost_tracker,
            builder_llm=builder_llm,
            evaluator_llm=evaluator_llm,
            skip_retries=skip_retries,
        )

    manifest = state.complete_run(status="completed")
    manifest["total_cost_usd"] = cost_tracker.total_cost
    state.update_manifest({"total_cost_usd": cost_tracker.total_cost})
    return state.read_manifest()


def resume_from_sprint(
    ticker: str,
    sprint_name: str,
    builder_llm: Callable[[str, str], str],
    evaluator_llm: Callable[[str, str], str],
    state_root: Path | None = None,
    cascade: bool = False,
) -> dict[str, Any]:
    """Re-run one sprint (or sprint + all downstream) using existing on-disk state.

    Validates that all dependencies have status 'passed' before proceeding.
    Fresh CostTracker — budget reflects only the resumed spend.
    """
    state = StateManager(ticker, state_root=state_root)
    manifest = state.read_manifest()

    # Validate dependencies are passed
    deps = SPRINT_DEPENDENCIES.get(sprint_name, [])
    for dep in deps:
        dep_status = manifest.get("sprints", {}).get(dep, {}).get("status")
        if dep_status != "passed":
            raise ValueError(
                f"Cannot restart {sprint_name}: dependency {dep} has status '{dep_status}'"
            )

    # Determine scope
    if cascade:
        sprints_to_run = _downstream_sprints(sprint_name)
    else:
        sprints_to_run = [sprint_name]

    # Clear old artifacts for each sprint to re-run
    for name in sprints_to_run:
        _clear_sprint_artifacts(state, name)

    cost_tracker = CostTracker()
    for name in sprints_to_run:
        state.copy_contract(name)
        run_sprint(name, state, cost_tracker, builder_llm, evaluator_llm)

    return state.read_manifest()


def _collect_failures(eval_result: dict[str, Any]) -> list[str]:
    """Extract actionable failure messages from an eval result."""
    failures: list[str] = []

    det = eval_result.get("deterministic_checks", {})
    failures.extend(det.get("details", []))

    xref = eval_result.get("cross_reference_checks", {})
    failures.extend(xref.get("details", []))

    grounding = eval_result.get("grounding_checks", {})
    for detail in grounding.get("details", []):
        if isinstance(detail, dict) and not detail.get("passed", True):
            failures.append(detail.get("details", "Grounding check failed"))

    llm = eval_result.get("llm_evaluation", {})
    failures.extend(llm.get("failures", []))

    return failures


def _mark_remaining_skipped(
    state: StateManager,
    current_sprint: str,
    sprints_to_run: list[str],
) -> None:
    """Mark all sprints from current onward as skipped in the manifest."""
    found = False
    for sprint in sprints_to_run:
        if sprint == current_sprint:
            found = True
        if found:
            state.update_sprint_in_manifest(sprint, {"status": "skipped"})


def _downstream_sprints(start_sprint: str) -> list[str]:
    """Return start_sprint plus all sprints that depend on it (directly or transitively)."""
    result = []
    start_idx = SPRINT_NAMES.index(start_sprint) if start_sprint in SPRINT_NAMES else -1
    if start_idx == -1:
        return [start_sprint]
    return SPRINT_NAMES[start_idx:]


def _clear_sprint_artifacts(state: StateManager, sprint_name: str) -> None:
    """Remove builder output, eval result, and traces for a sprint so it re-runs fresh."""
    import shutil
    sprint_dir = state.sprint_dir(sprint_name)
    for filename in ["builder_output.json", "eval_result.json", "builder_trace.json"]:
        artifact = sprint_dir / filename
        if artifact.exists():
            artifact.unlink()
