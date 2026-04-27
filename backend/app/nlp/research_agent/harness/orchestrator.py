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

logger = logging.getLogger(__name__)

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

    for attempt in range(1, max_attempts + 1):
        # Build
        builder_result = build(
            contract=contract,
            agent_bundle=agent_bundle,
            item1_text=item1_text,
            prior_outputs=prior_outputs,
            eval_failures=eval_failures if attempt > 1 else None,
            attempt=attempt,
            llm_call=builder_llm,
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
    }
    state.update_sprint_in_manifest(sprint_name, sprint_data)
    logger.warning("Sprint %s degraded after %d attempts", sprint_name, max_attempts)
    return sprint_data


def run_all_sprints(
    ticker: str,
    agent_bundle: dict[str, Any],
    item1_text: str,
    builder_llm: Callable[[str, str], str],
    evaluator_llm: Callable[[str, str], str],
    state_root: Path | None = None,
    sprint_names: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full pipeline for a ticker.

    Returns the final manifest.
    """
    state = StateManager(ticker, state_root=state_root)
    state.init_run()

    state.write_agent_bundle(agent_bundle)
    state.write_item1_text(item1_text)

    cost_tracker = CostTracker()
    sprints_to_run = sprint_names or SPRINT_NAMES
    run_start = time.time()

    for sprint_name in sprints_to_run:
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
