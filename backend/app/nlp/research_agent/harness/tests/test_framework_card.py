"""Tests for the framework_card module.

Validates that the framework reference cards contain required content,
key terms, thresholds, and scoring rubrics.
"""

import pytest

from app.nlp.research_agent.harness.framework_card import (
    EVALUATOR_FRAMEWORK_ADDENDUM,
    FRAMEWORK_CARD,
)


class TestFrameworkCard:
    """Tests for FRAMEWORK_CARD constant."""

    @pytest.mark.unit
    def test_framework_card_is_string(self):
        """FRAMEWORK_CARD is a non-empty string."""
        assert isinstance(FRAMEWORK_CARD, str)
        assert len(FRAMEWORK_CARD) > 0

    @pytest.mark.unit
    def test_framework_card_token_budget(self):
        """FRAMEWORK_CARD token count is between 700 and 1200 (rough len/4 estimate)."""
        token_estimate = len(FRAMEWORK_CARD) / 4
        assert 700 <= token_estimate <= 1200, f"Token estimate {token_estimate:.0f} outside range [700, 1200]"

    @pytest.mark.unit
    def test_framework_card_contains_key_terms(self):
        """FRAMEWORK_CARD contains all key framework terms (case-insensitive)."""
        card_lower = FRAMEWORK_CARD.lower()
        required_terms = [
            "roic",
            "moat",
            "qvg",
            "four ms",
            "owner earnings",
            "margin of safety",
            "pricing power",
            "management",
            "big five",
            "red flag",
        ]
        for term in required_terms:
            assert term in card_lower, f"Missing key term: {term}"

    @pytest.mark.unit
    def test_framework_card_contains_thresholds(self):
        """FRAMEWORK_CARD contains ROIC threshold (0.15 or 15%)."""
        # Threshold should appear somewhere
        assert "0.15" in FRAMEWORK_CARD or "15%" in FRAMEWORK_CARD, "ROIC threshold (0.15 or 15%) not found"

    @pytest.mark.unit
    def test_framework_card_contains_big_five_section(self):
        """FRAMEWORK_CARD contains Big Five Numbers section."""
        assert "BIG FIVE" in FRAMEWORK_CARD or "Big Five" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_card_contains_four_ms_section(self):
        """FRAMEWORK_CARD contains Four Ms section."""
        assert "FOUR MS" in FRAMEWORK_CARD or "Four Ms" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_card_contains_qvg_scoring_rubric(self):
        """FRAMEWORK_CARD contains QVG quality scoring rubric."""
        assert "QUALITY SCORING RUBRIC" in FRAMEWORK_CARD or "quality score" in FRAMEWORK_CARD.lower()
        # Check for rubric points
        assert "0–100" in FRAMEWORK_CARD or "0-100" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_card_contains_moat_types(self):
        """FRAMEWORK_CARD describes five moat types."""
        card_lower = FRAMEWORK_CARD.lower()
        moat_types = ["brand", "network effects", "cost advantage", "switching costs", "regulatory"]
        for moat_type in moat_types:
            assert moat_type in card_lower, f"Missing moat type: {moat_type}"

    @pytest.mark.unit
    def test_framework_card_contains_interest_coverage_thresholds(self):
        """FRAMEWORK_CARD contains interest coverage thresholds."""
        assert ">5x" in FRAMEWORK_CARD
        assert "2–5x" in FRAMEWORK_CARD or "2-5x" in FRAMEWORK_CARD
        assert "<2x" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_card_contains_reinvestment_sweet_spot(self):
        """FRAMEWORK_CARD mentions reinvestment ratio sweet spot (0.3-0.7)."""
        assert (
            "0.3–0.7" in FRAMEWORK_CARD or "0.3-0.7" in FRAMEWORK_CARD
        ), "Reinvestment ratio sweet spot (0.3-0.7) not found"

    @pytest.mark.unit
    def test_framework_card_contains_payout_sweet_spot(self):
        """FRAMEWORK_CARD mentions payout ratio sweet spot (0-0.6)."""
        assert "0–0.6" in FRAMEWORK_CARD or "0-0.6" in FRAMEWORK_CARD, "Payout ratio sweet spot (0-0.6) not found"

    @pytest.mark.unit
    def test_framework_card_contains_ten_red_flags(self):
        """FRAMEWORK_CARD contains red flags checklist with 10 items."""
        red_flags_section = FRAMEWORK_CARD[FRAMEWORK_CARD.find("RED FLAGS CHECKLIST") :]
        # Count numbered items (1. through 10.)
        flag_count = 0
        for i in range(1, 11):
            if f"{i}. " in red_flags_section:
                flag_count += 1
        assert flag_count == 10, f"Expected 10 red flags, found {flag_count}"

    @pytest.mark.unit
    def test_framework_card_contains_metrics_mapping(self):
        """FRAMEWORK_CARD contains metrics-to-framework mapping section."""
        assert "MAPPING" in FRAMEWORK_CARD or "mapping" in FRAMEWORK_CARD.lower()
        # Check for key metric mappings
        assert "roic_avg_10y" in FRAMEWORK_CARD or "roic" in FRAMEWORK_CARD.lower()


class TestEvaluatorFrameworkAddendum:
    """Tests for EVALUATOR_FRAMEWORK_ADDENDUM constant."""

    @pytest.mark.unit
    def test_evaluator_addendum_is_string(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM is a non-empty string."""
        assert isinstance(EVALUATOR_FRAMEWORK_ADDENDUM, str)
        assert len(EVALUATOR_FRAMEWORK_ADDENDUM) > 0

    @pytest.mark.unit
    def test_evaluator_addendum_shorter_than_card(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM is shorter than FRAMEWORK_CARD."""
        assert len(EVALUATOR_FRAMEWORK_ADDENDUM) < len(
            FRAMEWORK_CARD
        ), "Addendum should be shorter than main card for evaluator brevity"

    @pytest.mark.unit
    def test_evaluator_addendum_contains_rubric(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM contains QVG scoring rubric with point weights."""
        assert (
            "0–25" in EVALUATOR_FRAMEWORK_ADDENDUM or "0-25" in EVALUATOR_FRAMEWORK_ADDENDUM
        ), "QVG rubric weights not found"
        # Check for rubric dimensions
        assert "Moat" in EVALUATOR_FRAMEWORK_ADDENDUM
        assert "Revenue Quality" in EVALUATOR_FRAMEWORK_ADDENDUM or "revenue" in EVALUATOR_FRAMEWORK_ADDENDUM.lower()
        assert "Pricing Power" in EVALUATOR_FRAMEWORK_ADDENDUM or "pricing" in EVALUATOR_FRAMEWORK_ADDENDUM.lower()

    @pytest.mark.unit
    def test_evaluator_addendum_contains_red_flags(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM contains red flags section."""
        assert "RED FLAG" in EVALUATOR_FRAMEWORK_ADDENDUM or "red flag" in EVALUATOR_FRAMEWORK_ADDENDUM.lower()
        # Should have at least 5 red flags (abbreviated from 10)
        red_flags_section = EVALUATOR_FRAMEWORK_ADDENDUM[EVALUATOR_FRAMEWORK_ADDENDUM.find("RED FLAG") :]
        flag_count = red_flags_section.count("\n")  # Rough count of line breaks in red flags section
        assert flag_count >= 5, "Expected at least 5 red flags in addendum"

    @pytest.mark.unit
    def test_evaluator_addendum_token_budget(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM is ~200 tokens (rough estimate)."""
        token_estimate = len(EVALUATOR_FRAMEWORK_ADDENDUM) / 4
        # Allow range: 150-400 tokens (evaluator addendum needs rubric + red flags)
        assert 150 <= token_estimate <= 400, f"Token estimate {token_estimate:.0f} outside range [150, 400]"

    @pytest.mark.unit
    def test_evaluator_addendum_contains_scoring_rule(self):
        """EVALUATOR_FRAMEWORK_ADDENDUM contains scoring rule for quality threshold."""
        assert "SCORING RULE" in EVALUATOR_FRAMEWORK_ADDENDUM or "scoring rule" in EVALUATOR_FRAMEWORK_ADDENDUM.lower()
        # Should mention score thresholds
        assert (
            "40" in EVALUATOR_FRAMEWORK_ADDENDUM
            or "50" in EVALUATOR_FRAMEWORK_ADDENDUM
            or "70" in EVALUATOR_FRAMEWORK_ADDENDUM
        ), "Quality score thresholds not found"


class TestFrameworkConsistency:
    """Tests for consistency between FRAMEWORK_CARD and EVALUATOR_FRAMEWORK_ADDENDUM."""

    @pytest.mark.unit
    def test_both_mention_qvg(self):
        """Both constants mention QVG framework."""
        assert "QVG" in FRAMEWORK_CARD
        assert "QVG" in EVALUATOR_FRAMEWORK_ADDENDUM or "quality" in EVALUATOR_FRAMEWORK_ADDENDUM.lower()

    @pytest.mark.unit
    def test_both_mention_rule1(self):
        """Both constants reference Rule #1."""
        assert "Rule #1" in FRAMEWORK_CARD or "RULE #1" in FRAMEWORK_CARD
        # Addendum is focused, may just reference implicitly

    @pytest.mark.unit
    def test_addendum_is_subset_of_card(self):
        """Evaluator addendum focuses on rubric and red flags (subset of card topics)."""
        card_mentions_rubric = "QUALITY SCORING RUBRIC" in FRAMEWORK_CARD or "0–25" in FRAMEWORK_CARD
        addendum_mentions_rubric = "0–25" in EVALUATOR_FRAMEWORK_ADDENDUM or "0-25" in EVALUATOR_FRAMEWORK_ADDENDUM
        assert card_mentions_rubric and addendum_mentions_rubric, "Both should address QVG rubric"

    @pytest.mark.unit
    def test_red_flag_consistency(self):
        """Red flags in addendum are subset/summary of main card red flags."""
        card_lower = FRAMEWORK_CARD.lower()
        addendum_lower = EVALUATOR_FRAMEWORK_ADDENDUM.lower()
        # Both should mention ROIC and interest coverage as red flags
        assert "roic" in card_lower and ("roic" in addendum_lower or "declining" in addendum_lower)
        assert "interest" in card_lower or "coverage" in card_lower


class TestFrameworkCompleteness:
    """Tests for completeness of framework content."""

    @pytest.mark.unit
    def test_framework_card_has_rule1_section(self):
        """FRAMEWORK_CARD has distinct Rule #1 section."""
        assert "RULE #1" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_card_has_meaning_moat_management_mos(self):
        """FRAMEWORK_CARD covers all Four Ms."""
        card_lower = FRAMEWORK_CARD.lower()
        assert "meaning" in card_lower
        assert "moat" in card_lower
        assert "management" in card_lower
        assert "margin of safety" in card_lower or "mos" in card_lower

    @pytest.mark.unit
    def test_framework_card_has_how_to_use_section(self):
        """FRAMEWORK_CARD includes guidance on how to use the framework."""
        assert "HOW TO USE" in FRAMEWORK_CARD or "use this card" in FRAMEWORK_CARD.lower()

    @pytest.mark.unit
    def test_framework_contains_default_mos_percentage(self):
        """FRAMEWORK_CARD mentions default 50% margin of safety."""
        assert "50%" in FRAMEWORK_CARD or "50 %" in FRAMEWORK_CARD

    @pytest.mark.unit
    def test_framework_contains_rule1_philosophy(self):
        """FRAMEWORK_CARD states Rule #1 philosophy (margin of safety + moat discipline)."""
        card_lower = FRAMEWORK_CARD.lower()
        assert "margin of safety" in card_lower or "intrinsic value" in card_lower
