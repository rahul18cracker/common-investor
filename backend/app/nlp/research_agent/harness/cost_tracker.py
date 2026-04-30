"""Cost tracking for the qualitative agent harness.

Tracks LLM token costs (input, output, cached) and Tavily search costs
per sprint. Provides budget guard checks (soft limit, hard abort).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Anthropic pricing per 1M tokens (as of 2026-04)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "haiku": {
        "input_per_1m": 0.80,
        "output_per_1m": 4.00,
        "cached_input_per_1m": 0.08,
    },
    "sonnet": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
        "cached_input_per_1m": 0.30,
    },
    "opus": {
        "input_per_1m": 15.00,
        "output_per_1m": 75.00,
        "cached_input_per_1m": 1.50,
    },
}

TAVILY_COST_PER_SEARCH = 0.01

BUDGET_SOFT_LIMIT_USD = 0.50
BUDGET_HARD_LIMIT_USD = 0.75


class BudgetExceeded(Exception):
    """Raised when the hard budget limit is hit."""


@dataclass
class LLMUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        pricing = MODEL_PRICING.get(self.model)
        if not pricing:
            return 0.0
        non_cached_input = max(0, self.input_tokens - self.cached_tokens)
        return (
            non_cached_input * pricing["input_per_1m"] / 1_000_000
            + self.output_tokens * pricing["output_per_1m"] / 1_000_000
            + self.cached_tokens * pricing["cached_input_per_1m"] / 1_000_000
        )


@dataclass
class SprintCost:
    sprint_name: str
    builder_usages: list[LLMUsage] = field(default_factory=list)
    eval_usages: list[LLMUsage] = field(default_factory=list)
    tavily_searches: int = 0

    @property
    def builder_cost(self) -> float:
        return sum(u.cost_usd for u in self.builder_usages)

    @property
    def eval_cost(self) -> float:
        return sum(u.cost_usd for u in self.eval_usages)

    @property
    def tavily_cost(self) -> float:
        return self.tavily_searches * TAVILY_COST_PER_SEARCH

    @property
    def total_cost(self) -> float:
        return self.builder_cost + self.eval_cost + self.tavily_cost

    def to_dict(self) -> dict:
        return {
            "sprint_name": self.sprint_name,
            "builder_cost_usd": round(self.builder_cost, 6),
            "eval_cost_usd": round(self.eval_cost, 6),
            "tavily_cost_usd": round(self.tavily_cost, 6),
            "total_cost_usd": round(self.total_cost, 6),
            "tavily_searches": self.tavily_searches,
            "builder_tokens": {
                "input": sum(u.input_tokens for u in self.builder_usages),
                "output": sum(u.output_tokens for u in self.builder_usages),
                "cached": sum(u.cached_tokens for u in self.builder_usages),
            },
            "eval_tokens": {
                "input": sum(u.input_tokens for u in self.eval_usages),
                "output": sum(u.output_tokens for u in self.eval_usages),
                "cached": sum(u.cached_tokens for u in self.eval_usages),
            },
        }


class CostTracker:
    """Tracks cumulative cost across sprints for a single run."""

    def __init__(
        self,
        soft_limit: float = BUDGET_SOFT_LIMIT_USD,
        hard_limit: float = BUDGET_HARD_LIMIT_USD,
    ):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self._sprints: dict[str, SprintCost] = {}

    def get_or_create_sprint(self, sprint_name: str) -> SprintCost:
        if sprint_name not in self._sprints:
            self._sprints[sprint_name] = SprintCost(sprint_name=sprint_name)
        return self._sprints[sprint_name]

    def record_builder_usage(
        self,
        sprint_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        sprint = self.get_or_create_sprint(sprint_name)
        sprint.builder_usages.append(
            LLMUsage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
            )
        )

    def record_eval_usage(
        self,
        sprint_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        sprint = self.get_or_create_sprint(sprint_name)
        sprint.eval_usages.append(
            LLMUsage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
            )
        )

    def record_tavily_search(self, sprint_name: str, count: int = 1) -> None:
        sprint = self.get_or_create_sprint(sprint_name)
        sprint.tavily_searches += count

    @property
    def total_cost(self) -> float:
        return sum(s.total_cost for s in self._sprints.values())

    def is_soft_exceeded(self) -> bool:
        return self.total_cost > self.soft_limit

    def is_hard_exceeded(self) -> bool:
        return self.total_cost > self.hard_limit

    def check_budget(self) -> None:
        """Raise BudgetExceeded if the hard limit is hit."""
        if self.is_hard_exceeded():
            raise BudgetExceeded(f"Hard budget limit ${self.hard_limit:.2f} exceeded: " f"${self.total_cost:.4f} spent")

    def sprint_cost(self, sprint_name: str) -> float:
        sprint = self._sprints.get(sprint_name)
        return sprint.total_cost if sprint else 0.0

    def to_dict(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "soft_limit_usd": self.soft_limit,
            "hard_limit_usd": self.hard_limit,
            "soft_exceeded": self.is_soft_exceeded(),
            "hard_exceeded": self.is_hard_exceeded(),
            "sprints": {name: sc.to_dict() for name, sc in self._sprints.items()},
        }
