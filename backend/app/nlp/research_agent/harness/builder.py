"""Contract-driven builder for the qualitative agent harness.

Generates one JSON output per sprint. Prompts are structured for
Anthropic prompt caching: static prefix (system + agent-bundle +
Item 1 text) is identical across sprints, dynamic suffix (contract
+ prior outputs + sprint prompt) changes per sprint.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.nlp.research_agent.harness.framework_card import FRAMEWORK_CARD


class LLMCallable(Protocol):
    def __call__(self, system_prompt: str, user_prompt: str, static_context: str | None = None) -> str: ...


BUILDER_SYSTEM_PROMPT = (
    FRAMEWORK_CARD
    + "\n---\n\n"
    "You are an expert financial analyst performing qualitative research "
    "on a public company. You follow Phil Town's Rule #1 investing methodology "
    "and Katsenelson's QVG framework.\n\n"
    "## Rules\n"
    "- Base your analysis on the quantitative data and SEC filings provided.\n"
    "- Be concrete and specific. Cite figures, segments, and filing details.\n"
    "- Avoid marketing language, promotional tone, and vague assertions.\n"
    "- If information is unavailable, use \"unknown\" — never fabricate.\n"
    "- Respond with valid JSON only. No markdown wrapping, no explanation "
    "outside the JSON.\n"
)

SPRINT_PROMPTS: dict[str, str] = {
    "01_business_profile": (
        "Summarize the company's business model in 8-10 sentences for the narrative field. "
        "List: products/services, primary customers, geographies, pricing model, "
        "distribution channels, and top revenue drivers. "
        "State where revenue is recurring and why. "
        "Identify recurrence mechanisms (contracts, replacement cycles, ecosystem lock-in). "
        "Avoid marketing jargon; be concrete."
    ),
    "02_unit_economics": (
        "Analyze the company's unit economics: revenue model, pricing approach, "
        "volume drivers, gross margin drivers, fixed vs variable cost mix, "
        "operating leverage, cash conversion, working capital factors, and capex split "
        "(maintenance vs growth). Include optional metrics (LTV, CAC, payback) if "
        "available. Identify the single most impactful improvement lever."
    ),
    "03_industry": (
        "Define the industry this company operates in. Identify 3+ direct peer "
        "candidates with comparable business mix. Assess competitive forces: "
        "concentration, pricing power, customer/supplier power, substitution threat, "
        "regulatory burden, cyclicality. Provide a verdict (good/neutral/poor) "
        "on industry attractiveness."
    ),
    "04_moat": (
        "Assess the company's competitive moat across five dimensions: switching costs, "
        "network effects (none/direct/indirect), scale/cost advantage, brand, and "
        "regulatory assets. For each, state whether it is present and cite specific "
        "evidence. Rate overall moat durability 0-5. Note emerging threats to the moat."
    ),
    "05_management": (
        "Evaluate management quality: capital allocation style and track record "
        "(specific examples), incentive alignment with shareholders, governance "
        "quality, and transparency. Rate management 0-5 overall."
    ),
    "06_peers": (
        "Compare the subject company against its top 3 peers on 7 standardized "
        "criteria (moat, management, revenue_quality, pricing_power, balance_sheet, "
        "growth, risk), each scored 0-5. Include brief commentary explaining the "
        "relative positioning."
    ),
    "07_risks": (
        "Identify risks across six categories: concentration (customer/supplier), "
        "cyclicality, regulatory, FX/commodity, technology disruption, and other. "
        "List the top 5 risks with likelihood and impact. Define 5-10 monitoring "
        "triggers with specific thresholds."
    ),
    "08_thesis": (
        "Synthesize all prior analysis into a final investment thesis. State your "
        "stance (buy/hold/avoid) with explicit reasoning. Compute a quality score "
        "(0-100) using the rubric: Moat & Durability (0-25), Revenue Quality (0-15), "
        "Pricing Power (0-15), Industry Structure (0-15), Management (0-20), "
        "Balance Sheet (0-10). Provide confidence level (low/medium/high), "
        "3+ key points, and 3+ falsifiers that would disprove the thesis."
    ),
}


def build_static_prefix(agent_bundle: dict[str, Any], item1_text: str) -> str:
    """Build XML-wrapped data block for the cached system context."""
    return (
        "<financial_data>\n"
        + json.dumps(agent_bundle, indent=2, default=str)
        + "\n</financial_data>\n\n"
        "<item1_text>\n"
        + item1_text
        + "\n</item1_text>"
    )


def build_dynamic_suffix(
    contract: dict[str, Any],
    prior_outputs: dict[str, Any] | None = None,
    eval_failures: list[str] | None = None,
    attempt: int = 1,
) -> str:
    """Build the per-sprint dynamic suffix."""
    sprint_name = contract.get("sprint", "unknown")
    sprint_prompt = SPRINT_PROMPTS.get(sprint_name, "")

    schema = contract.get("output_schema", {})
    required = schema.get("required_fields", [])
    enums = schema.get("enums", {})
    array_mins = schema.get("array_minimums", {})
    str_mins = schema.get("string_minimums", {})

    parts = [f"## Sprint: {sprint_name}\n\n"]

    parts.append(f"## Task\n{sprint_prompt}\n\n")

    field_types = schema.get("field_types", {})

    parts.append("## Output Contract\n")
    parts.append(f"Required fields: {', '.join(required)}\n")
    if field_types:
        parts.append("Field types (STRICT — wrong types will fail validation):\n")
        for field, ftype in field_types.items():
            parts.append(f"- {field}: {ftype}\n")
    if enums:
        for field, allowed in enums.items():
            parts.append(f"- {field}: must be from {allowed}\n")
    if array_mins:
        for field, min_ct in array_mins.items():
            parts.append(f"- {field}: minimum {min_ct} items\n")
    if str_mins:
        for field, min_len in str_mins.items():
            parts.append(f"- {field}: minimum {min_len} characters\n")
    parts.append("- No null values. Use \"unknown\" if data is unavailable.\n")
    parts.append("- No nested objects unless field type specifies it. Use flat strings.\n")
    parts.append("- No empty strings in arrays.\n\n")

    if prior_outputs:
        parts.append("## Prior Sprint Outputs (for context)\n")
        for name, output in prior_outputs.items():
            parts.append(f"### {name}\n```json\n{json.dumps(output, indent=2, default=str)}\n```\n\n")

    if attempt > 1 and eval_failures:
        parts.append("## Previous Attempt Failed — Fix These Issues\n")
        parts.append(f"This is attempt {attempt}. Your prior output had these failures:\n")
        for failure in eval_failures:
            parts.append(f"- {failure}\n")
        parts.append("\nAddress each failure specifically in your revised output.\n\n")

    parts.append("Respond with valid JSON only.\n")

    return "".join(parts)


def parse_builder_response(raw: str) -> dict[str, Any] | None:
    """Parse the builder LLM response into a dict. Returns None on failure."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, ValueError):
        return None


@dataclass
class BuilderResult:
    """Result of a builder invocation."""
    output: dict[str, Any] | None
    raw_response: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    model: str
    duration_seconds: float
    success: bool


def build(
    contract: dict[str, Any],
    agent_bundle: dict[str, Any],
    item1_text: str,
    prior_outputs: dict[str, Any] | None = None,
    eval_failures: list[str] | None = None,
    attempt: int = 1,
    llm_call: LLMCallable | None = None,
) -> BuilderResult:
    """Invoke the builder LLM for a single sprint attempt.

    Constructs the cache-optimized prompt and calls the LLM.
    Returns a BuilderResult with parsed output or None on failure.
    """
    if llm_call is None:
        return BuilderResult(
            output=None, raw_response="", input_tokens=0,
            output_tokens=0, cached_tokens=0, model="none",
            duration_seconds=0.0, success=False,
        )

    static = build_static_prefix(agent_bundle, item1_text)
    dynamic = build_dynamic_suffix(contract, prior_outputs, eval_failures, attempt)

    model = contract.get("model_tier", "haiku")

    start = time.time()
    try:
        raw_response = llm_call(BUILDER_SYSTEM_PROMPT, dynamic, static_context=static)
    except Exception as e:
        return BuilderResult(
            output=None, raw_response=str(e), input_tokens=0,
            output_tokens=0, cached_tokens=0, model=model,
            duration_seconds=time.time() - start, success=False,
        )

    duration = time.time() - start
    parsed = parse_builder_response(raw_response)

    usage = getattr(llm_call, "last_usage", {})

    return BuilderResult(
        output=parsed,
        raw_response=raw_response,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cached_tokens=usage.get("cache_read_input_tokens", 0),
        model=model,
        duration_seconds=duration,
        success=parsed is not None,
    )
