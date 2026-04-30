from __future__ import annotations

import re
from dataclasses import dataclass, field


def validate_agent_bundle(bundle: dict) -> list[str]:
    """Returns list of issue strings. Empty list = valid."""
    issues = []

    # Check if bundle is a dict
    if not isinstance(bundle, dict):
        return ["agent_bundle is not a dict"]

    # Check required top-level keys
    required_keys = ["company", "metrics", "timeseries"]
    for key in required_keys:
        if key not in bundle:
            issues.append(f"Missing required key: {key}")

    if issues:  # Return early if missing required keys
        return issues

    # Check company fields
    company = bundle.get("company", {})
    if not isinstance(company, dict):
        issues.append("company is not a dict")
    else:
        required_company_fields = ["cik", "ticker", "name"]
        for field in required_company_fields:
            if field not in company:
                issues.append(f"Missing company field: {field}")

    # Check metrics has growth data
    metrics = bundle.get("metrics", {})
    if not isinstance(metrics, dict):
        issues.append("metrics is not a dict")
    else:
        has_growth = False

        # Check growths
        if "growths" in metrics and metrics["growths"] is not None:
            growths = metrics["growths"]
            if isinstance(growths, dict):
                for value in growths.values():
                    if value is not None and isinstance(value, (int, float)):
                        has_growth = True
                        break

        # Check growths_extended
        if not has_growth and "growths_extended" in metrics and metrics["growths_extended"] is not None:
            growths_extended = metrics["growths_extended"]
            if isinstance(growths_extended, dict):
                for value in growths_extended.values():
                    if value is not None and isinstance(value, (int, float)):
                        has_growth = True
                        break

        if not has_growth:
            issues.append("metrics has no growth data")

    # Check timeseries.is has revenue entries
    timeseries = bundle.get("timeseries", {})
    if not isinstance(timeseries, dict):
        issues.append("timeseries is not a dict")
    else:
        is_data = timeseries.get("is", [])
        if not isinstance(is_data, list):
            issues.append("timeseries.is is not a list")
        else:
            has_revenue = False
            for entry in is_data:
                if isinstance(entry, dict) and "revenue" in entry:
                    has_revenue = True
                    break
            if not has_revenue:
                issues.append("timeseries.is has no revenue entries")

    return issues


def validate_item1_text(text: str) -> list[str]:
    """Returns list of issue strings. Empty list = valid."""
    issues = []

    # Check if text is a string
    if not isinstance(text, str):
        return ["item1_text is not a string"]

    # Check if empty
    if len(text) == 0:
        return ["item1_text is empty"]

    # Check minimum length
    if len(text) < 100:
        issues.append(f"item1_text too short ({len(text)} chars, min 100)")

    # Check for HTML tags
    if re.search(r"<[^>]+>", text):
        issues.append("item1_text contains HTML tags")

    return issues


SPRINT_DATA_REQUIREMENTS = {
    "01_business_profile": {
        "agent_bundle": ["company.ticker", "company.name", "timeseries.is"],
        "item1_text": True,
    },
    "02_unit_economics": {
        "agent_bundle": ["metrics.latest_operating_margin", "metrics.latest_fcf_margin", "timeseries.is"],
        "item1_text": True,
    },
    "03_industry": {
        "agent_bundle": ["company.sic_code", "company.industry_category", "timeseries.is"],
        "item1_text": True,
    },
    "04_moat": {
        "agent_bundle": ["four_ms.moat", "metrics.roic_avg_10y", "quality_scores"],
        "item1_text": True,
    },
    "05_management": {
        "agent_bundle": ["four_ms.management", "quality_scores.share_count_trend"],
        "item1_text": False,
    },
    "06_peers": {
        "agent_bundle": ["company.ticker", "company.industry_category", "timeseries.is"],
        "item1_text": False,
    },
    "07_risks": {
        "agent_bundle": ["company.ticker", "timeseries.is", "four_ms"],
        "item1_text": True,
    },
    "08_thesis": {
        "agent_bundle": ["company.ticker", "metrics", "four_ms", "quality_scores"],
        "item1_text": True,
    },
}


@dataclass
class SprintReadiness:
    ready: bool
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _resolve_nested_path(obj: dict, path: str) -> tuple[bool, any]:
    """
    Resolve a dot-notation path in a nested dict.
    Returns (found, value) where found=True if path exists and value is not None.
    """
    keys = path.split(".")
    current = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]

    # Check if the final value is not None
    if current is None:
        return False, None

    return True, current


def check_sprint_readiness(
    sprint_name: str,
    bundle: dict,
    item1_text: str | None,
) -> SprintReadiness:
    """Check if a sprint has all required data."""
    if sprint_name not in SPRINT_DATA_REQUIREMENTS:
        return SprintReadiness(
            ready=False,
            missing_fields=[f"Unknown sprint: {sprint_name}"],
            warnings=[],
        )

    requirements = SPRINT_DATA_REQUIREMENTS[sprint_name]
    missing_fields = []
    warnings = []

    # Check agent_bundle fields
    for field_path in requirements["agent_bundle"]:
        found, value = _resolve_nested_path(bundle, field_path)
        if not found:
            missing_fields.append(field_path)

    # Check item1_text requirement
    if requirements["item1_text"]:
        if item1_text is None or (isinstance(item1_text, str) and len(item1_text) == 0):
            missing_fields.append("item1_text missing or empty")

    # Check warnings for timeseries.is
    if "timeseries.is" in requirements["agent_bundle"]:
        found, is_data = _resolve_nested_path(bundle, "timeseries.is")
        if found and isinstance(is_data, list):
            if len(is_data) < 5:
                warnings.append(f"Only {len(is_data)} years of timeseries data (5+ recommended)")

    ready = len(missing_fields) == 0

    return SprintReadiness(
        ready=ready,
        missing_fields=missing_fields,
        warnings=warnings,
    )
