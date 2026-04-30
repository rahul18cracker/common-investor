"""Deterministic grounding checks for the qualitative agent harness.

Layer 3 of evaluation: extracts claims from builder output and verifies
them against agent-bundle quantitative data. Catches hallucinations
where valid JSON contains factually wrong analysis.
"""

from __future__ import annotations

import re
from typing import Any


def resolve_path(data: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a dotted path like 'metrics.growths_extended.rev_cagr_5y' against a nested dict.

    Returns None if any segment is missing.
    """
    current = data
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


NEGATION_WINDOW = 4

NEGATION_WORDS = frozenset(
    [
        "not",
        "no",
        "isn't",
        "isnt",
        "aren't",
        "arent",
        "wasn't",
        "wasnt",
        "hasn't",
        "hasnt",
        "without",
        "lack",
        "lacks",
        "lacking",
        "neither",
        "never",
        "barely",
        "hardly",
        "unlikely",
        "despite",
    ]
)


def has_claim_signal(text: str, signals: list[str]) -> bool:
    """Check if any signal word appears in text without a preceding negation."""
    text_lower = text.lower()
    words = text_lower.split()
    for signal in signals:
        signal_lower = signal.lower()
        for i, word in enumerate(words):
            if signal_lower in word:
                window_start = max(0, i - NEGATION_WINDOW)
                preceding = words[window_start:i]
                if not any(w in NEGATION_WORDS for w in preceding):
                    return True
    return False


def has_negated_claim(text: str, signals: list[str]) -> bool:
    """Check if signal words appear but are negated."""
    text_lower = text.lower()
    words = text_lower.split()
    for signal in signals:
        signal_lower = signal.lower()
        for i, word in enumerate(words):
            if signal_lower in word:
                window_start = max(0, i - NEGATION_WINDOW)
                preceding = words[window_start:i]
                if any(w in NEGATION_WORDS for w in preceding):
                    return True
    return False


_NUMERIC_PATTERN = re.compile(
    r"""
    (?:
        -?\d+(?:\.\d+)?%                  # percentages: 18%, -2.5%
        | \$\s*-?\d+(?:\.\d+)?            # dollar amounts: $50, $3.2
        | -?\d+(?:\.\d+)?\s*(?:billion|million|trillion|bps)  # units
        | -?\d+(?:,\d{3})+(?:\.\d+)?      # comma-separated: 1,234,567
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_QUALITATIVE_NUMBERS = {
    "double-digit": (10, 99),
    "double digit": (10, 99),
    "single-digit": (1, 9),
    "single digit": (1, 9),
    "triple-digit": (100, 999),
    "triple digit": (100, 999),
}


def extract_numeric_claims(text: str) -> list[str]:
    """Extract numeric expressions from text.

    Returns raw string matches (e.g. '18%', '$50 billion', 'double-digit').
    """
    claims = _NUMERIC_PATTERN.findall(text)
    text_lower = text.lower()
    for qual in _QUALITATIVE_NUMBERS:
        if qual in text_lower:
            claims.append(qual)
    return claims


def has_revenue_data(timeseries_is: Any) -> bool:
    """Check whether the income statement timeseries contains any revenue entries."""
    if not isinstance(timeseries_is, list):
        return False
    for entry in timeseries_is:
        if isinstance(entry, dict) and entry.get("revenue") is not None:
            return True
    return False


def run_grounding_check(
    check: dict[str, Any],
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    item1_text: str = "",
) -> dict[str, Any]:
    """Run a single grounding check from the contract.

    Returns a result dict with: id, passed, severity, details.
    """
    check_id = check["id"]
    severity = check.get("severity", "hard")

    if check_id == "growth_claim_not_contradicted":
        return _check_claim_vs_metric(
            check_id=check_id,
            severity=severity,
            text=_get_text_from_output(builder_output, check.get("claim_source", "")),
            signals=check.get("claim_signals", []),
            metric_path=check.get("verify_against", ""),
            agent_bundle=agent_bundle,
            contradiction_test=lambda metric: metric < 0,
            description=check.get("description", ""),
        )

    if check_id == "decline_claim_not_contradicted":
        return _check_claim_vs_metric(
            check_id=check_id,
            severity=severity,
            text=_get_text_from_output(builder_output, check.get("claim_source", "")),
            signals=check.get("claim_signals", []),
            metric_path=check.get("verify_against", ""),
            agent_bundle=agent_bundle,
            contradiction_test=lambda metric: metric > 0.05,
            description=check.get("description", ""),
        )

    if check_id == "revenue_drivers_not_fabricated":
        return _check_revenue_drivers(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "unverifiable_numeric_claims":
        return _check_unverifiable_numerics(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            item1_text=item1_text,
            description=check.get("description", ""),
        )

    return {
        "id": check_id,
        "passed": True,
        "severity": severity,
        "details": f"Unknown check id '{check_id}', skipped",
    }


def run_all_grounding_checks(
    checks: list[dict[str, Any]],
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    item1_text: str = "",
) -> dict[str, Any]:
    """Run all grounding checks and return aggregate result.

    Returns:
        {
            "pass": bool (true if zero hard contradictions),
            "contradictions_found": int (hard only),
            "soft_flags": int,
            "details": [per-check results]
        }
    """
    results = []
    hard_contradictions = 0
    soft_flags = 0

    for check in checks:
        result = run_grounding_check(check, builder_output, agent_bundle, item1_text)
        results.append(result)
        if not result["passed"]:
            if result["severity"] == "hard":
                hard_contradictions += 1
            else:
                soft_flags += 1

    return {
        "pass": hard_contradictions == 0,
        "contradictions_found": hard_contradictions,
        "soft_flags": soft_flags,
        "details": results,
    }


# --- Internal helpers ---


def _get_text_from_output(builder_output: dict[str, Any], claim_source: str) -> str:
    """Extract text content from builder output given a dotted path like 'output.narrative'."""
    path = claim_source.replace("output.", "", 1) if claim_source.startswith("output.") else claim_source
    value = resolve_path(builder_output, path)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value) if value is not None else ""


def _check_claim_vs_metric(
    check_id: str,
    severity: str,
    text: str,
    signals: list[str],
    metric_path: str,
    agent_bundle: dict[str, Any],
    contradiction_test: Any,
    description: str,
) -> dict[str, Any]:
    """Check if claim signals in text contradict a metric value."""
    path = metric_path.replace("agent_bundle.", "", 1) if metric_path.startswith("agent_bundle.") else metric_path
    metric_value = resolve_path(agent_bundle, path)

    if metric_value is None:
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": f"Metric at '{metric_path}' is null/missing, check skipped",
        }

    claim_present = has_claim_signal(text, signals)
    if not claim_present:
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": "No matching claim signals found in text",
        }

    if contradiction_test(metric_value):
        return {
            "id": check_id,
            "passed": False,
            "severity": severity,
            "details": (
                f"Contradiction: text contains {signals} signals "
                f"but metric '{metric_path}' = {metric_value}. {description}"
            ),
        }

    return {
        "id": check_id,
        "passed": True,
        "severity": severity,
        "details": "Claim signals present and consistent with metric data",
    }


def _check_revenue_drivers(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    drivers = builder_output.get("revenue_drivers", [])
    timeseries_is = resolve_path(agent_bundle, "timeseries.is")

    if not drivers:
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": "No revenue drivers listed, nothing to verify",
        }

    if has_revenue_data(timeseries_is):
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": "Revenue drivers listed and revenue data exists in agent-bundle",
        }

    return {
        "id": check_id,
        "passed": False,
        "severity": severity,
        "details": (
            f"Revenue drivers listed ({len(drivers)} items) but no revenue data "
            f"found in agent-bundle timeseries. {description}"
        ),
    }


def _check_unverifiable_numerics(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    item1_text: str,
    description: str,
) -> dict[str, Any]:
    narrative = builder_output.get("narrative", "")
    claims = extract_numeric_claims(narrative)

    if not claims:
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": "No numeric claims found in narrative",
        }

    bundle_str = str(agent_bundle).lower()
    source_text = bundle_str + " " + item1_text.lower()

    unverifiable = []
    for claim in claims:
        claim_core = claim.strip().lstrip("$").rstrip("%")
        claim_core = claim_core.replace(",", "").strip()
        if claim_core and claim_core not in source_text:
            unverifiable.append(claim)

    if not unverifiable:
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": f"All {len(claims)} numeric claims traceable to sources",
        }

    return {
        "id": check_id,
        "passed": False,
        "severity": severity,
        "details": (
            f"{len(unverifiable)} of {len(claims)} numeric claims not found in "
            f"agent-bundle or Item 1 text: {unverifiable}. {description}"
        ),
    }
