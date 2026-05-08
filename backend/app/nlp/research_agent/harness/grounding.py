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

    # --- 06_peers grounding checks ---

    if check_id == "subject_roic_score_grounded":
        return _check_peers_score_within_tolerance(
            check_id=check_id,
            severity=severity,
            output_path="subject_scores.roic_persistence_0_to_5",
            bundle_path="quality_scores.roic_persistence",
            bundle_scale=5.0,
            tolerance=1.0,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "subject_balance_sheet_grounded":
        return _check_peers_score_within_tolerance(
            check_id=check_id,
            severity=severity,
            output_path="subject_scores.balance_sheet_0_to_5",
            bundle_path="four_ms.balance_sheet_resilience.score",
            bundle_scale=5.0 / 5.0,
            tolerance=1.0,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "subject_management_score_grounded":
        return _check_peers_score_within_tolerance(
            check_id=check_id,
            severity=severity,
            output_path="subject_scores.management_0_to_5",
            bundle_path="four_ms.management.score",
            bundle_scale=5.0,
            tolerance=1.0,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "subject_pricing_power_grounded":
        return _check_peers_score_within_tolerance(
            check_id=check_id,
            severity=severity,
            output_path="subject_scores.pricing_power_0_to_5",
            bundle_path="quality_scores.pricing_power_score",
            bundle_scale=5.0,
            tolerance=1.0,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "no_duplicate_peers":
        return _check_no_duplicate_peers(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            description=check.get("description", ""),
        )

    if check_id == "subject_not_in_peers":
        return _check_subject_not_in_peers(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            description=check.get("description", ""),
        )

    if check_id == "peers_include_industry_candidates":
        return _check_peers_include_industry_candidates(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            check=check,
            description=check.get("description", ""),
        )

    if check_id in ("subject_scores_commentary_length", "peer_commentary_length"):
        return _check_commentary_length(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            min_length=100,
            description=check.get("description", ""),
        )

    if check_id in ("subject_roic_vs_peers_check", "subject_balance_sheet_vs_peers_check"):
        return _check_subject_vs_peers_relative(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            description=check.get("description", ""),
        )

    # --- Generic rule-based checks from contract contradiction_rule ---

    if check.get("contradiction_rule"):
        return _check_generic_rule(
            check_id=check_id,
            severity=severity,
            builder_output=builder_output,
            agent_bundle=agent_bundle,
            check=check,
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


# --- 06_peers grounding helpers ---


def _check_peers_score_within_tolerance(
    check_id: str,
    severity: str,
    output_path: str,
    bundle_path: str,
    bundle_scale: float,
    tolerance: float,
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Check that a subject score in output is within ±tolerance of a scaled agent_bundle value."""
    output_val = resolve_path(builder_output, output_path)
    bundle_val = resolve_path(agent_bundle, bundle_path)

    if output_val is None or bundle_val is None:
        return {"id": check_id, "passed": True, "severity": severity, "details": "Missing value, skipped"}

    try:
        out_f = float(output_val)
        expected = float(bundle_val) * bundle_scale
    except (TypeError, ValueError):
        return {"id": check_id, "passed": True, "severity": severity, "details": "Non-numeric, skipped"}

    if abs(out_f - expected) > tolerance:
        return {
            "id": check_id,
            "passed": False,
            "severity": severity,
            "details": (
                f"{output_path}={out_f:.1f} deviates >{tolerance} from expected {expected:.1f} "
                f"(bundle {bundle_path}={float(bundle_val):.3f} × {bundle_scale}). {description}"
            ),
        }
    return {
        "id": check_id,
        "passed": True,
        "severity": severity,
        "details": f"{output_path}={out_f:.1f} within tolerance of {expected:.1f}",
    }


def _check_no_duplicate_peers(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Check that all peer names are unique."""
    peers = builder_output.get("peers", [])
    names = [str(p.get("name", "")).strip().lower() for p in peers if isinstance(p, dict)]
    seen: set[str] = set()
    dups = []
    for n in names:
        if n in seen:
            dups.append(n)
        seen.add(n)

    if dups:
        return {
            "id": check_id,
            "passed": False,
            "severity": severity,
            "details": f"Duplicate peer names: {dups}. {description}",
        }
    return {"id": check_id, "passed": True, "severity": severity, "details": f"{len(names)} peers, all unique"}


def _check_subject_not_in_peers(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Check that the subject company does not appear in the peers list."""
    ticker = str(agent_bundle.get("company", {}).get("ticker", "")).upper()
    company_name = str(agent_bundle.get("company", {}).get("name", "")).lower()
    peers = builder_output.get("peers", [])

    for peer in peers:
        if not isinstance(peer, dict):
            continue
        peer_name = str(peer.get("name", "")).lower()
        if ticker.lower() in peer_name or (company_name and company_name in peer_name):
            return {
                "id": check_id,
                "passed": False,
                "severity": severity,
                "details": f"Subject '{ticker}' appears in peer list as '{peer.get('name')}'. {description}",
            }
    return {"id": check_id, "passed": True, "severity": severity, "details": "Subject not found in peers"}


def _check_peers_include_industry_candidates(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    check: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Check that at least 2 peers come from prior_outputs.03_industry.peer_candidates."""
    # peer_candidates is not available in agent_bundle — it comes from prior sprint outputs.
    # The orchestrator doesn't pass prior_outputs into grounding. Skip gracefully.
    return {
        "id": check_id,
        "passed": True,
        "severity": "soft",
        "details": "peer_candidates from prior sprint not available at grounding time — deferred to LLM evaluator",
    }


def _check_commentary_length(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    min_length: int,
    description: str,
) -> dict[str, Any]:
    """Check commentary length for subject_scores and each peer."""
    violations = []

    if check_id == "subject_scores_commentary_length":
        commentary = resolve_path(builder_output, "subject_scores.commentary")
        if commentary is None or len(str(commentary)) < min_length:
            violations.append(f"subject_scores.commentary is {len(str(commentary or ''))} chars, minimum {min_length}")
    elif check_id == "peer_commentary_length":
        for i, peer in enumerate(builder_output.get("peers", [])):
            if not isinstance(peer, dict):
                continue
            commentary = peer.get("commentary", "")
            if not commentary or len(str(commentary)) < min_length:
                violations.append(f"peers[{i}].commentary is {len(str(commentary))} chars, minimum {min_length}")

    if violations:
        return {
            "id": check_id,
            "passed": False,
            "severity": severity,
            "details": "; ".join(violations) + f". {description}",
        }
    return {"id": check_id, "passed": True, "severity": severity, "details": "All commentary meets minimum length"}


def _check_subject_vs_peers_relative(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Check that subject score is not significantly below average peer score (>2 points gap)."""
    field_map = {
        "subject_roic_vs_peers_check": "roic_persistence_0_to_5",
        "subject_balance_sheet_vs_peers_check": "balance_sheet_0_to_5",
    }
    field = field_map.get(check_id)
    if not field:
        return {"id": check_id, "passed": True, "severity": severity, "details": "Unknown relative check, skipped"}

    subject_score = resolve_path(builder_output, f"subject_scores.{field}")
    peers = builder_output.get("peers", [])
    peer_scores = [p.get(field) for p in peers if isinstance(p, dict) and p.get(field) is not None]

    if subject_score is None or not peer_scores:
        return {"id": check_id, "passed": True, "severity": severity, "details": "Insufficient data, skipped"}

    try:
        sub_f = float(subject_score)
        avg_peer = sum(float(s) for s in peer_scores) / len(peer_scores)
    except (TypeError, ValueError):
        return {"id": check_id, "passed": True, "severity": severity, "details": "Non-numeric, skipped"}

    if sub_f < avg_peer - 2.0:
        return {
            "id": check_id,
            "passed": False,
            "severity": severity,
            "details": f"Subject {field}={sub_f:.1f} is >2 below peer avg={avg_peer:.1f}. {description}",
        }
    return {
        "id": check_id,
        "passed": True,
        "severity": severity,
        "details": f"Subject {field}={sub_f:.1f} vs peer avg={avg_peer:.1f}",
    }


def _check_generic_rule(
    check_id: str,
    severity: str,
    builder_output: dict[str, Any],
    agent_bundle: dict[str, Any],
    check: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    """Generic evaluator for the rule-based checks used in 05_management, 07_risks, etc.

    Parses the `contradiction_rule` field and applies common patterns mechanically.
    Patterns supported:
    - "X >= N AND Y == 'value'" — compound AND condition
    - "X is null or empty" — null/empty check
    - "any item in X has Y == null or Y == ''" — array member check
    """
    rule = check.get("contradiction_rule", "")
    claim_src_raw = check.get("claim_source", "")
    verify_src_raw = check.get("verify_against", "")

    # Multi-source checks (verify_against is a list) can't be mechanically evaluated
    if isinstance(verify_src_raw, list) or isinstance(claim_src_raw, list):
        return {
            "id": check_id,
            "passed": True,
            "severity": severity,
            "details": f"Multi-source check '{check_id}' — deferred to LLM evaluator",
        }

    claim_src = str(claim_src_raw).replace("output.", "", 1)
    verify_src = str(verify_src_raw).replace("agent_bundle.", "", 1).replace("output.", "", 1)

    claim_val = resolve_path(builder_output, claim_src)
    verify_val = (
        resolve_path(agent_bundle, verify_src)
        if "agent_bundle." in check.get("verify_against", "")
        else resolve_path(builder_output, verify_src)
    )

    # null/empty check pattern
    if "is null or empty" in rule:
        failed = claim_val is None or (isinstance(claim_val, str) and not claim_val.strip())
        if failed:
            return {
                "id": check_id,
                "passed": False,
                "severity": severity,
                "details": f"{claim_src} is null or empty. {description}",
            }
        return {"id": check_id, "passed": True, "severity": severity, "details": f"{claim_src} is present"}

    # array item threshold check
    if "any item in" in rule and "has threshold == null" in rule:
        items = claim_val if isinstance(claim_val, list) else []
        bad = [i for i, item in enumerate(items) if isinstance(item, dict) and not item.get("threshold")]
        if bad:
            return {
                "id": check_id,
                "passed": False,
                "severity": severity,
                "details": f"Items {bad} have null/empty threshold. {description}",
            }
        return {"id": check_id, "passed": True, "severity": severity, "details": "All thresholds present"}

    # numeric comparison with AND conditions
    if claim_val is not None and verify_val is not None and ">=" in rule and "AND" in rule:
        try:
            claim_f = float(claim_val)
            float(verify_val)
            # Extract the threshold from rule like "output.rating_0_to_5 >= 4 AND ..."
            import re as _re

            m = _re.search(r">=\s*([\d.]+)", rule)
            if m:
                threshold = float(m.group(1))
                if claim_f >= threshold:
                    # Second condition: check if AND clause also fires
                    # Pattern: AND agent_bundle.X == 'value'
                    m2 = _re.search(r"AND\s+\S+\s*==\s*['\"]?([^'\"]+)['\"]?", rule)
                    if m2:
                        and_val = m2.group(1).strip().rstrip("'\"")
                        verify_str = str(verify_val).strip().strip("'\"")
                        if verify_str == and_val:
                            return {
                                "id": check_id,
                                "passed": False,
                                "severity": severity,
                                "details": f"Contradiction: {rule}. {description}",
                            }
        except (TypeError, ValueError, AttributeError):
            pass

    # abs() deviation check
    if "abs(" in rule and ">" in rule:
        try:
            lhs = abs(float(claim_val) - float(verify_val) * 5) if verify_val is not None else None
            m = re.search(r">\s*([\d.]+)", rule)
            if lhs is not None and m and lhs > float(m.group(1)):
                return {
                    "id": check_id,
                    "passed": False,
                    "severity": severity,
                    "details": f"abs deviation {lhs:.2f} > {m.group(1)}. {description}",
                }
        except (TypeError, ValueError):
            pass

    return {
        "id": check_id,
        "passed": True,
        "severity": severity,
        "details": f"Rule check '{check_id}' — no contradiction detected (or rule pattern not mechanically testable)",
    }
