from __future__ import annotations

import pytest

from app.nlp.research_agent.harness.data_validator import (
    SprintReadiness,
    check_sprint_readiness,
    validate_agent_bundle,
    validate_item1_text,
)


@pytest.mark.unit
class TestValidateAgentBundle:
    """Test schema validation for agent bundles."""

    def test_valid_bundle_passes(self):
        """Valid bundle with all required fields passes."""
        bundle = {
            "company": {
                "cik": "0000789019",
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
            },
            "metrics": {
                "growths": {
                    "revenue_cagr_10y": 0.095,
                }
            },
            "timeseries": {
                "is": [
                    {"revenue": 100000},
                    {"revenue": 110000},
                ]
            },
        }
        assert validate_agent_bundle(bundle) == []

    def test_non_dict_input(self):
        """Non-dict input returns appropriate error."""
        assert validate_agent_bundle("not a dict") == ["agent_bundle is not a dict"]
        assert validate_agent_bundle(123) == ["agent_bundle is not a dict"]
        assert validate_agent_bundle([]) == ["agent_bundle is not a dict"]

    def test_missing_top_level_key(self):
        """Missing required top-level key returns error."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {"growths": {"revenue_cagr_10y": 0.1}},
        }
        issues = validate_agent_bundle(bundle)
        assert "Missing required key: timeseries" in issues

    def test_missing_company_field(self):
        """Missing company fields return errors."""
        bundle = {
            "company": {
                "cik": "123",
                "ticker": "AAPL",
                # Missing name
            },
            "metrics": {"growths": {"revenue_cagr_10y": 0.1}},
            "timeseries": {"is": [{"revenue": 100}]},
        }
        issues = validate_agent_bundle(bundle)
        assert "Missing company field: name" in issues

    def test_no_growth_data_at_all(self):
        """Missing both growths and growths_extended returns error."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {},
            "timeseries": {"is": [{"revenue": 100}]},
        }
        issues = validate_agent_bundle(bundle)
        assert "metrics has no growth data" in issues

    def test_growths_with_all_none_values(self):
        """growths present but all None values returns error."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {"growths": {"revenue_cagr_10y": None, "fcf_cagr_10y": None}},
            "timeseries": {"is": [{"revenue": 100}]},
        }
        issues = validate_agent_bundle(bundle)
        assert "metrics has no growth data" in issues

    def test_growths_extended_only_passes(self):
        """Bundle with growths_extended (no growths) still passes growth check."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {"growths_extended": {"fcf_cagr_5y": 0.08}},
            "timeseries": {"is": [{"revenue": 100}]},
        }
        issues = validate_agent_bundle(bundle)
        assert "metrics has no growth data" not in issues

    def test_timeseries_is_empty(self):
        """Empty timeseries.is returns error."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {"growths": {"revenue_cagr_10y": 0.1}},
            "timeseries": {"is": []},
        }
        issues = validate_agent_bundle(bundle)
        assert "timeseries.is has no revenue entries" in issues

    def test_timeseries_is_no_revenue(self):
        """timeseries.is without revenue entries returns error."""
        bundle = {
            "company": {"cik": "123", "ticker": "AAPL", "name": "Apple"},
            "metrics": {"growths": {"revenue_cagr_10y": 0.1}},
            "timeseries": {"is": [{"net_income": 100}, {"net_income": 110}]},
        }
        issues = validate_agent_bundle(bundle)
        assert "timeseries.is has no revenue entries" in issues


@pytest.mark.unit
class TestValidateItem1Text:
    """Test validation for Item 1 text content."""

    def test_valid_text_passes(self):
        """Valid text (>= 100 chars, no HTML) passes."""
        text = "This is a valid text block that contains enough characters to pass the minimum length check. It is over 100 characters."
        assert validate_item1_text(text) == []

    def test_non_string_input(self):
        """Non-string input returns error."""
        assert validate_item1_text(123) == ["item1_text is not a string"]
        assert validate_item1_text(None) == ["item1_text is not a string"]
        assert validate_item1_text(["text"]) == ["item1_text is not a string"]

    def test_empty_string(self):
        """Empty string returns error."""
        assert validate_item1_text("") == ["item1_text is empty"]

    def test_text_too_short(self):
        """Text shorter than 100 chars returns error."""
        text = "Short text"
        issues = validate_item1_text(text)
        assert any("too short" in issue for issue in issues)

    def test_html_tags_present(self):
        """Text with HTML tags returns error."""
        text = "This is valid long text with HTML tags that should be caught. <div>HTML content</div> " + "x" * 50
        issues = validate_item1_text(text)
        assert any("HTML tags" in issue for issue in issues)

    def test_multiple_issues(self):
        """Text with multiple issues returns all issues."""
        text = "Short <p>with</p> html"
        issues = validate_item1_text(text)
        assert len(issues) >= 2
        assert any("too short" in issue for issue in issues)
        assert any("HTML tags" in issue for issue in issues)


@pytest.mark.unit
class TestCheckSprintReadiness:
    """Test sprint readiness validation."""

    def _make_valid_bundle(self):
        """Helper to create a valid bundle with comprehensive data."""
        return {
            "company": {
                "cik": "0000789019",
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
                "sic_code": "7372",
                "industry_category": "software",
            },
            "metrics": {
                "latest_operating_margin": 0.42,
                "latest_fcf_margin": 0.30,
                "roic_avg_10y": 0.25,
            },
            "four_ms": {
                "moat": 0.8,
                "management": 0.7,
            },
            "quality_scores": {
                "share_count_trend": -0.02,
            },
            "timeseries": {
                "is": [
                    {"revenue": 100},
                    {"revenue": 110},
                    {"revenue": 120},
                    {"revenue": 130},
                    {"revenue": 140},
                    {"revenue": 150},
                ]
            },
        }

    def test_known_sprint_all_data_present(self):
        """Known sprint with all data present returns ready=True."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text content here" * 10  # Enough chars
        result = check_sprint_readiness("01_business_profile", bundle, item1_text)
        assert result.ready is True
        assert result.missing_fields == []

    def test_known_sprint_missing_bundle_field(self):
        """Known sprint with missing bundle field returns ready=False."""
        bundle = self._make_valid_bundle()
        del bundle["company"]["ticker"]
        item1_text = "Valid text content here" * 10
        result = check_sprint_readiness("01_business_profile", bundle, item1_text)
        assert result.ready is False
        assert "company.ticker" in result.missing_fields

    def test_known_sprint_item1_text_required_but_none(self):
        """Sprint requiring item1_text but given None returns ready=False."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("01_business_profile", bundle, None)
        assert result.ready is False
        assert "item1_text missing or empty" in result.missing_fields

    def test_known_sprint_item1_text_required_but_empty(self):
        """Sprint requiring item1_text but given empty string returns ready=False."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("01_business_profile", bundle, "")
        assert result.ready is False
        assert "item1_text missing or empty" in result.missing_fields

    def test_sprint_item1_text_not_required_none_ok(self):
        """Sprint where item1_text not required tolerates None."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("05_management", bundle, None)
        assert result.ready is True
        assert "item1_text" not in " ".join(result.missing_fields).lower() or result.missing_fields == []

    def test_timeseries_is_fewer_than_5_years_warning(self):
        """timeseries.is with < 5 entries triggers warning but stays ready=True."""
        bundle = self._make_valid_bundle()
        bundle["timeseries"]["is"] = [
            {"revenue": 100},
            {"revenue": 110},
            {"revenue": 120},
        ]
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("01_business_profile", bundle, item1_text)
        assert result.ready is True  # Warning, not blocker
        assert len(result.warnings) > 0
        assert any("3 years" in w for w in result.warnings)

    def test_unknown_sprint_name(self):
        """Unknown sprint name returns ready=False with appropriate error."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("99_unknown_sprint", bundle, "text")
        assert result.ready is False
        assert any("Unknown sprint" in field for field in result.missing_fields)

    def test_sprint_02_unit_economics(self):
        """Sprint 02 requires specific metrics fields."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("02_unit_economics", bundle, item1_text)
        assert result.ready is True

    def test_sprint_02_missing_margin(self):
        """Sprint 02 fails if missing latest_operating_margin."""
        bundle = self._make_valid_bundle()
        del bundle["metrics"]["latest_operating_margin"]
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("02_unit_economics", bundle, item1_text)
        assert result.ready is False
        assert "metrics.latest_operating_margin" in result.missing_fields

    def test_sprint_03_industry(self):
        """Sprint 03 requires industry fields."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("03_industry", bundle, item1_text)
        assert result.ready is True

    def test_sprint_04_moat(self):
        """Sprint 04 requires moat and roic fields."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("04_moat", bundle, item1_text)
        assert result.ready is True

    def test_sprint_05_management(self):
        """Sprint 05 does not require item1_text."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("05_management", bundle, None)
        assert result.ready is True

    def test_sprint_06_peers_no_item1_text_required(self):
        """Sprint 06 does not require item1_text."""
        bundle = self._make_valid_bundle()
        result = check_sprint_readiness("06_peers", bundle, None)
        assert result.ready is True

    def test_sprint_07_risks(self):
        """Sprint 07 requires four_ms."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("07_risks", bundle, item1_text)
        assert result.ready is True

    def test_sprint_08_thesis(self):
        """Sprint 08 requires comprehensive data."""
        bundle = self._make_valid_bundle()
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("08_thesis", bundle, item1_text)
        assert result.ready is True

    def test_nested_field_resolution(self):
        """Nested fields are resolved correctly via dot notation."""
        bundle = {
            "company": {"ticker": "AAPL", "name": "Apple"},
            "metrics": {"latest_operating_margin": 0.3},
            "four_ms": {"moat": 0.7},
            "quality_scores": {"share_count_trend": 0.0},
            "timeseries": {"is": [{"revenue": 100}]},
        }
        item1_text = "Valid text" * 20
        # Sprint 05 requires four_ms.management and quality_scores.share_count_trend
        result = check_sprint_readiness("05_management", bundle, item1_text)
        assert result.ready is False
        assert "four_ms.management" in result.missing_fields

    def test_none_value_treated_as_missing(self):
        """None values for required fields are treated as missing."""
        bundle = self._make_valid_bundle()
        bundle["company"]["ticker"] = None
        item1_text = "Valid text" * 20
        result = check_sprint_readiness("01_business_profile", bundle, item1_text)
        assert result.ready is False
        assert "company.ticker" in result.missing_fields
