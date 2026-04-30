"""Tests for the cost_tracker module."""

import pytest

from app.nlp.research_agent.harness.cost_tracker import (
    BUDGET_HARD_LIMIT_USD,
    BUDGET_SOFT_LIMIT_USD,
    TAVILY_COST_PER_SEARCH,
    BudgetExceeded,
    CostTracker,
    LLMUsage,
    SprintCost,
)


class TestLLMUsage:
    def test_haiku_cost_no_cache(self):
        u = LLMUsage(model="haiku", input_tokens=10_000, output_tokens=1_000)
        expected = 10_000 * 0.80 / 1e6 + 1_000 * 4.00 / 1e6
        assert abs(u.cost_usd - expected) < 1e-9

    def test_haiku_cost_with_cache(self):
        u = LLMUsage(model="haiku", input_tokens=10_000, output_tokens=1_000, cached_tokens=6_000)
        non_cached = 4_000
        expected = non_cached * 0.80 / 1e6 + 1_000 * 4.00 / 1e6 + 6_000 * 0.08 / 1e6
        assert abs(u.cost_usd - expected) < 1e-9

    def test_sonnet_cost(self):
        u = LLMUsage(model="sonnet", input_tokens=8_000, output_tokens=2_000)
        expected = 8_000 * 3.00 / 1e6 + 2_000 * 15.00 / 1e6
        assert abs(u.cost_usd - expected) < 1e-9

    def test_opus_cost(self):
        u = LLMUsage(model="opus", input_tokens=5_000, output_tokens=500)
        expected = 5_000 * 15.00 / 1e6 + 500 * 75.00 / 1e6
        assert abs(u.cost_usd - expected) < 1e-9

    def test_unknown_model_returns_zero(self):
        u = LLMUsage(model="gpt-4o", input_tokens=10_000, output_tokens=1_000)
        assert u.cost_usd == 0.0

    def test_all_cached(self):
        u = LLMUsage(model="haiku", input_tokens=10_000, output_tokens=500, cached_tokens=10_000)
        expected = 500 * 4.00 / 1e6 + 10_000 * 0.08 / 1e6
        assert abs(u.cost_usd - expected) < 1e-9

    def test_zero_tokens(self):
        u = LLMUsage(model="haiku")
        assert u.cost_usd == 0.0


class TestSprintCost:
    def test_empty_sprint(self):
        sc = SprintCost(sprint_name="01_business_profile")
        assert sc.builder_cost == 0.0
        assert sc.eval_cost == 0.0
        assert sc.tavily_cost == 0.0
        assert sc.total_cost == 0.0

    def test_builder_cost(self):
        sc = SprintCost(sprint_name="01_business_profile")
        sc.builder_usages.append(LLMUsage(model="haiku", input_tokens=8_000, output_tokens=1_200))
        assert sc.builder_cost > 0
        assert sc.eval_cost == 0.0

    def test_multiple_builder_attempts(self):
        sc = SprintCost(sprint_name="01_business_profile")
        u1 = LLMUsage(model="haiku", input_tokens=8_000, output_tokens=1_000)
        u2 = LLMUsage(model="haiku", input_tokens=9_000, output_tokens=1_200)
        sc.builder_usages.extend([u1, u2])
        assert sc.builder_cost == u1.cost_usd + u2.cost_usd

    def test_tavily_cost(self):
        sc = SprintCost(sprint_name="01_business_profile", tavily_searches=3)
        assert sc.tavily_cost == 3 * TAVILY_COST_PER_SEARCH

    def test_total_combines_all(self):
        sc = SprintCost(sprint_name="01_business_profile", tavily_searches=2)
        sc.builder_usages.append(LLMUsage(model="haiku", input_tokens=8_000, output_tokens=1_000))
        sc.eval_usages.append(LLMUsage(model="haiku", input_tokens=3_000, output_tokens=500))
        assert sc.total_cost == sc.builder_cost + sc.eval_cost + sc.tavily_cost

    def test_to_dict(self):
        sc = SprintCost(sprint_name="01_business_profile", tavily_searches=1)
        sc.builder_usages.append(LLMUsage(model="haiku", input_tokens=8_000, output_tokens=1_000))
        d = sc.to_dict()
        assert d["sprint_name"] == "01_business_profile"
        assert d["tavily_searches"] == 1
        assert d["builder_tokens"]["input"] == 8_000
        assert d["builder_tokens"]["output"] == 1_000
        assert d["total_cost_usd"] > 0


class TestCostTracker:
    def test_empty_tracker(self):
        ct = CostTracker()
        assert ct.total_cost == 0.0
        assert not ct.is_soft_exceeded()
        assert not ct.is_hard_exceeded()

    def test_record_builder_usage(self):
        ct = CostTracker()
        ct.record_builder_usage("01_business_profile", "haiku", 8_000, 1_000)
        assert ct.total_cost > 0
        assert ct.sprint_cost("01_business_profile") > 0

    def test_record_eval_usage(self):
        ct = CostTracker()
        ct.record_eval_usage("01_business_profile", "haiku", 3_000, 500)
        assert ct.total_cost > 0

    def test_record_tavily_search(self):
        ct = CostTracker()
        ct.record_tavily_search("01_business_profile", count=3)
        assert ct.total_cost == 3 * TAVILY_COST_PER_SEARCH

    def test_total_across_sprints(self):
        ct = CostTracker()
        ct.record_builder_usage("01_business_profile", "haiku", 8_000, 1_000)
        ct.record_builder_usage("02_unit_economics", "haiku", 9_000, 1_200)
        cost1 = ct.sprint_cost("01_business_profile")
        cost2 = ct.sprint_cost("02_unit_economics")
        assert abs(ct.total_cost - (cost1 + cost2)) < 1e-9

    def test_soft_limit_exceeded(self):
        ct = CostTracker(soft_limit=0.01)
        ct.record_builder_usage("01_business_profile", "sonnet", 100_000, 10_000)
        assert ct.is_soft_exceeded()

    def test_hard_limit_exceeded(self):
        ct = CostTracker(hard_limit=0.01)
        ct.record_builder_usage("01_business_profile", "sonnet", 100_000, 10_000)
        assert ct.is_hard_exceeded()

    def test_check_budget_raises(self):
        ct = CostTracker(hard_limit=0.001)
        ct.record_builder_usage("01_business_profile", "sonnet", 100_000, 10_000)
        with pytest.raises(BudgetExceeded):
            ct.check_budget()

    def test_check_budget_ok(self):
        ct = CostTracker()
        ct.record_builder_usage("01_business_profile", "haiku", 1_000, 100)
        ct.check_budget()

    def test_sprint_cost_unknown_sprint(self):
        ct = CostTracker()
        assert ct.sprint_cost("nonexistent") == 0.0

    def test_multiple_attempts_same_sprint(self):
        ct = CostTracker()
        ct.record_builder_usage("01_business_profile", "haiku", 8_000, 1_000)
        ct.record_builder_usage("01_business_profile", "haiku", 9_000, 1_200)
        sprint = ct.get_or_create_sprint("01_business_profile")
        assert len(sprint.builder_usages) == 2

    def test_cached_tokens_reduce_cost(self):
        ct_no_cache = CostTracker()
        ct_no_cache.record_builder_usage("01_business_profile", "haiku", 10_000, 1_000, cached_tokens=0)
        ct_cached = CostTracker()
        ct_cached.record_builder_usage("01_business_profile", "haiku", 10_000, 1_000, cached_tokens=8_000)
        assert ct_cached.total_cost < ct_no_cache.total_cost

    def test_to_dict(self):
        ct = CostTracker()
        ct.record_builder_usage("01_business_profile", "haiku", 8_000, 1_000)
        ct.record_tavily_search("01_business_profile", 2)
        d = ct.to_dict()
        assert d["total_cost_usd"] > 0
        assert d["soft_limit_usd"] == BUDGET_SOFT_LIMIT_USD
        assert d["hard_limit_usd"] == BUDGET_HARD_LIMIT_USD
        assert "01_business_profile" in d["sprints"]

    def test_default_limits(self):
        ct = CostTracker()
        assert ct.soft_limit == BUDGET_SOFT_LIMIT_USD
        assert ct.hard_limit == BUDGET_HARD_LIMIT_USD
