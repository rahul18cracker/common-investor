"""Three-tier text sanitizer for prompt injection detection and cleanup.

Tiers:
  T1: Regex patterns (hard-block + soft suspicious)
  T2: DeBERTa model (optional, if available)
  T3: Haiku (stub only; not yet implemented)
"""

from __future__ import annotations

import logging
import re
import string
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import T2 classifier
try:
    from app.nlp.research_agent.harness._injection_classifier import (
        classify_injection,
    )

    _T2_AVAILABLE = True
except ImportError:
    _T2_AVAILABLE = False
    logger.debug("DeBERTa T2 classifier not available")


# ============================================================================
# TIER 1: REGEX PATTERNS
# ============================================================================

INJECTION_HARD_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\byou\s+are\s+now\s+a\b",
    r"```\s*system",
    r"<\s*/?\s*system\s*>",
    r"\bIMPORTANT\s*:\s*override\b",
    r"\bACT\s+AS\b.{0,20}\bAI\b",
    r"\bDAN\s+mode\b",
    r"\bjailbreak\b",
]

SEC_WHITELIST_PATTERNS = [
    r"\boverride\s+\w+\s+agreement\b",
    r"\bignore\s+\w+\s+covenant\b",
    r"\bsystem\w*\s+risk\b",
    r"\binstruction\s+\d+",
    r"\bdisregard\s+prior\s+period\b",
    r"\byou\s+are\s+now\s+required\s+to\b",
    r"\bsupersede[sd]?\b",
]

# Compile patterns for efficiency
_HARD_PATTERNS_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_HARD_PATTERNS]
_WHITELIST_PATTERNS_RE = [re.compile(p, re.IGNORECASE) for p in SEC_WHITELIST_PATTERNS]


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class SanitizeResult:
    """Result of sanitizing a single text value."""

    clean: bool  # True if text passed all tiers without block/suspicious
    tainted: bool  # True if suspicious or blocked
    action: str  # "pass" | "blocked" | "suspicious"
    tier_fired: Optional[str]  # "T1_regex" | "T2_deberta" | "T3_haiku" | None
    confidence: float  # 1.0 for regex, model score for T2/T3
    details: list[str] = field(default_factory=list)  # what matched, where
    sanitized_text: str = ""  # text after T1 cleanup


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _strip_control_chars(text: str) -> str:
    """Strip ASCII control characters (0-31, 127); preserve unicode and printable ASCII."""
    return "".join(c for c in text if ord(c) >= 32 and ord(c) != 127 or c in "\n\t\r")


def _strip_html_tags(text: str) -> str:
    """Remove simple HTML tags via regex."""
    return re.sub(r"<[^>]+>", "", text)


def _clean_text(text: str, max_length: int) -> str:
    """Apply T1 cleanup: control char strip, HTML removal, truncation."""
    text = _strip_control_chars(text)
    text = _strip_html_tags(text)
    if len(text) > max_length:
        text = text[:max_length]
    return text


def _check_t1_patterns(text: str) -> tuple[Optional[str], list[str]]:
    """
    Check T1 regex patterns.

    Returns:
        (pattern_name or None, [details])
        pattern_name is "hard_block" if any hard pattern matched.
    """
    details = []

    for i, pattern in enumerate(_HARD_PATTERNS_RE):
        if pattern.search(text):
            details.append(f"Hard pattern {i}: {INJECTION_HARD_PATTERNS[i]}")
            return "hard_block", details

    return None, details


def _check_whitelist(text: str) -> bool:
    """Check if text matches any SEC whitelist pattern."""
    for pattern in _WHITELIST_PATTERNS_RE:
        if pattern.search(text):
            return True
    return False


def _classify_with_haiku(text: str) -> SanitizeResult:
    """
    Placeholder for T3 Haiku review.

    T3 is not yet implemented. For now, log and return suspicious pass-through.
    In future, this would escalate to Claude Haiku for nuanced review.
    """
    logger.debug("T3 Haiku not yet implemented; flagging for manual review")
    return SanitizeResult(
        clean=False,
        tainted=True,
        action="suspicious",
        tier_fired="T3_haiku_stub",
        confidence=0.5,
        details=["T3 Haiku not yet implemented — flagged for manual review"],
        sanitized_text=text,
    )


# ============================================================================
# PUBLIC API
# ============================================================================


def sanitize_text(text: str, max_length: int = 30000, field_path: str = "") -> SanitizeResult:
    """
    Sanitize a single text string through three tiers.

    Args:
        text: Input text to sanitize.
        max_length: Maximum allowed length (default 30000).
        field_path: Optional path for logging (e.g., 'company.name').

    Returns:
        SanitizeResult with action, tier_fired, details, and sanitized_text.
    """
    # Always apply T1 cleanup first
    sanitized = _clean_text(text, max_length)

    # TIER 1: Regex (always active) — check both raw and sanitized to catch HTML-wrapped injection
    hard_pattern, t1_details = _check_t1_patterns(text)
    if not hard_pattern:
        hard_pattern, t1_details = _check_t1_patterns(sanitized)

    if hard_pattern:
        # Check if whitelist also matches
        if _check_whitelist(text):
            # Both hard pattern and whitelist match -> suspicious
            logger.warning(f"T1 suspicious (whitelisted): {field_path}")
            return SanitizeResult(
                clean=False,
                tainted=True,
                action="suspicious",
                tier_fired="T1_regex",
                confidence=0.9,
                details=t1_details + ["SEC whitelist pattern also matched"],
                sanitized_text=sanitized,
            )
        else:
            # Hard pattern only -> blocked
            logger.warning(f"T1 blocked: {field_path}")
            return SanitizeResult(
                clean=False,
                tainted=True,
                action="blocked",
                tier_fired="T1_regex",
                confidence=1.0,
                details=t1_details,
                sanitized_text=sanitized,
            )

    # No hard pattern matched; proceed to T2 if available
    if not _T2_AVAILABLE:
        logger.debug(f"T1 pass (T2 unavailable): {field_path}")
        return SanitizeResult(
            clean=True,
            tainted=False,
            action="pass",
            tier_fired=None,
            confidence=1.0,
            details=["Passed T1 regex; T2 unavailable"],
            sanitized_text=sanitized,
        )

    # TIER 2: DeBERTa (optional)
    try:
        score, label = classify_injection(sanitized)
    except Exception as e:
        logger.error(f"T2 classification error: {e}")
        score, label = 0.0, "benign"

    # T2 thresholds: >=0.95 -> blocked, >=0.80 -> suspicious
    if label == "injection" and score >= 0.95 and not _check_whitelist(text):
        logger.warning(f"T2 blocked (score={score:.3f}): {field_path}")
        return SanitizeResult(
            clean=False,
            tainted=True,
            action="blocked",
            tier_fired="T2_deberta",
            confidence=score,
            details=[f"DeBERTa high-confidence injection (score={score:.3f})"],
            sanitized_text=sanitized,
        )

    if label == "injection" and score >= 0.80:
        # If whitelist matches, escalate to T3
        if _check_whitelist(text):
            logger.info(f"T2 suspicious + whitelist: escalating to T3: {field_path}")
            return _classify_with_haiku(text)

        logger.warning(f"T2 suspicious (score={score:.3f}): {field_path}")
        return SanitizeResult(
            clean=False,
            tainted=True,
            action="suspicious",
            tier_fired="T2_deberta",
            confidence=score,
            details=[f"DeBERTa moderate injection confidence (score={score:.3f})"],
            sanitized_text=sanitized,
        )

    # Passed T2 (or benign classification)
    logger.debug(f"T2 pass (score={score:.3f}): {field_path}")
    return SanitizeResult(
        clean=True,
        tainted=False,
        action="pass",
        tier_fired=None,
        confidence=1.0,
        details=[f"Passed T1 and T2 (DeBERTa score={score:.3f})"],
        sanitized_text=sanitized,
    )


def sanitize_agent_bundle(bundle: dict) -> tuple[dict, list[SanitizeResult]]:
    """
    Recursively sanitize all string values in an agent bundle dict.

    Numbers, bools, lists, nested dicts pass through unchanged.
    Strings are sanitized. If a string is blocked, the corresponding
    bundle key is set to '[BLOCKED]'.

    Args:
        bundle: Dictionary (may have nested dicts).

    Returns:
        tuple: (sanitized_bundle, list_of_flagged_results)
               Flagged list contains only non-pass results (blocked/suspicious).
    """
    sanitized = {}
    flagged = []

    def _recurse(obj: object, path: str) -> object:
        if isinstance(obj, str):
            result = sanitize_text(obj, field_path=path)
            if result.action != "pass":
                flagged.append(result)
            if result.action == "blocked":
                return "[BLOCKED]"
            return result.sanitized_text
        elif isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                new_dict[k] = _recurse(v, new_path)
            return new_dict
        elif isinstance(obj, list):
            # Recurse into list items but keep as list
            return [_recurse(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        else:
            # Numbers, bools, None, etc. pass through
            return obj

    sanitized = _recurse(bundle, "")
    return sanitized, flagged


def sanitize_prior_outputs(outputs: dict[str, dict]) -> tuple[dict[str, dict], list[SanitizeResult]]:
    """
    Sanitize all string values in prior sprint outputs before feeding to next sprint.

    Args:
        outputs: Dict mapping sprint_name to sprint_output_dict.

    Returns:
        tuple: (sanitized_outputs, list_of_flagged_results)
    """
    sanitized = {}
    flagged = []

    for sprint_name, sprint_output in outputs.items():
        path = f"sprint.{sprint_name}"
        sanitized_output, flagged_for_sprint = sanitize_agent_bundle(sprint_output)
        sanitized[sprint_name] = sanitized_output
        flagged.extend(flagged_for_sprint)

    return sanitized, flagged
