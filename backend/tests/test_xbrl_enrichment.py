"""
Regression tests for Phase 1A XBRL enrichment (Option B from edgartools spike).

Tests the fallback summing logic for:
- SGA: sum SellingAndMarketingExpense + GeneralAndAdministrativeExpense
- total_debt: sum LongTermDebtNoncurrent + LongTermDebtCurrent
- depreciation: fall back to CF adjustment tags when not on IS
"""
import pytest
from unittest.mock import patch
from app.ingest.sec import (
    _pick_first_units,
    _annual_value,
    _sum_annual_values,
    SGA_COMPONENT_TAGS,
    DEBT_COMPONENT_TAGS,
)


pytestmark = pytest.mark.unit


def _make_facts(*tag_defs):
    """Build a minimal CompanyFacts dict from (tag_name, fy, val, form) tuples."""
    us_gaap = {}
    for tag, fy, val, form in tag_defs:
        if tag not in us_gaap:
            us_gaap[tag] = {"units": {"USD": []}}
        us_gaap[tag]["units"]["USD"].append({
            "fy": fy, "val": val, "form": form, "end": f"{fy}-12-31",
        })
    return {"facts": {"us-gaap": us_gaap}}


# =============================================================================
# SGA summing
# =============================================================================


class TestSGASumming:
    """SGA should sum selling + G&A components when combined tag is missing."""

    def test_sum_selling_and_ga(self):
        """MSFT pattern: SellingAndMarketingExpense + GeneralAndAdministrativeExpense."""
        facts = _make_facts(
            ("SellingAndMarketingExpense", 2023, 22759e6, "10-K"),
            ("GeneralAndAdministrativeExpense", 2023, 7575e6, "10-K"),
        )

        result = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", 2023)

        assert result == pytest.approx(22759e6 + 7575e6, rel=1e-6)

    def test_sum_selling_expense_variant(self):
        """Second group: SellingExpense + GeneralAndAdministrativeExpense."""
        facts = _make_facts(
            ("SellingExpense", 2023, 10000e6, "10-K"),
            ("GeneralAndAdministrativeExpense", 2023, 5000e6, "10-K"),
        )

        result = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", 2023)

        assert result == pytest.approx(15000e6, rel=1e-6)

    def test_returns_none_when_only_one_component(self):
        """If only selling exists but not G&A, sum fails — returns None."""
        facts = _make_facts(
            ("SellingAndMarketingExpense", 2023, 22759e6, "10-K"),
        )

        result = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", 2023)

        assert result is None

    def test_returns_none_when_no_components(self):
        """No SGA-related tags at all."""
        facts = _make_facts(
            ("Revenues", 2023, 100e9, "10-K"),
        )

        result = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", 2023)

        assert result is None

    def test_skips_quarterly_data(self):
        """Components with only 10-Q data should not sum."""
        facts = _make_facts(
            ("SellingAndMarketingExpense", 2023, 5000e6, "10-Q"),
            ("GeneralAndAdministrativeExpense", 2023, 2000e6, "10-Q"),
        )

        result = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", 2023)

        assert result is None


# =============================================================================
# Total debt summing
# =============================================================================


class TestTotalDebtSumming:
    """total_debt should sum LT noncurrent + current when combined tag is missing."""

    def test_sum_lt_noncurrent_and_current(self):
        """Standard pattern: LongTermDebtNoncurrent + LongTermDebtCurrent."""
        facts = _make_facts(
            ("LongTermDebtNoncurrent", 2023, 40000e6, "10-K"),
            ("LongTermDebtCurrent", 2023, 5000e6, "10-K"),
        )

        result = _sum_annual_values(facts, DEBT_COMPONENT_TAGS, "USD", 2023)

        assert result == pytest.approx(45000e6, rel=1e-6)

    def test_sum_lt_noncurrent_and_shortterm(self):
        """Alternative: LongTermDebtNoncurrent + ShortTermBorrowings."""
        facts = _make_facts(
            ("LongTermDebtNoncurrent", 2023, 40000e6, "10-K"),
            ("ShortTermBorrowings", 2023, 3000e6, "10-K"),
        )

        result = _sum_annual_values(facts, DEBT_COMPONENT_TAGS, "USD", 2023)

        assert result == pytest.approx(43000e6, rel=1e-6)

    def test_prefers_first_group(self):
        """First matching group wins (LT + Current before LT + ShortTerm)."""
        facts = _make_facts(
            ("LongTermDebtNoncurrent", 2023, 40000e6, "10-K"),
            ("LongTermDebtCurrent", 2023, 5000e6, "10-K"),
            ("ShortTermBorrowings", 2023, 3000e6, "10-K"),
        )

        result = _sum_annual_values(facts, DEBT_COMPONENT_TAGS, "USD", 2023)

        # Should use first group: LT noncurrent + current = 45B
        assert result == pytest.approx(45000e6, rel=1e-6)

    def test_returns_none_when_only_noncurrent(self):
        """If only LT noncurrent exists, no group completes — returns None."""
        facts = _make_facts(
            ("LongTermDebtNoncurrent", 2023, 40000e6, "10-K"),
        )

        result = _sum_annual_values(facts, DEBT_COMPONENT_TAGS, "USD", 2023)

        assert result is None


# =============================================================================
# Depreciation CF fallback
# =============================================================================


class TestDepreciationCFFallback:
    """Depreciation should fall back to CF adjustment tags if not on IS."""

    def test_picks_depreciation_from_cf_tags(self):
        """When depreciation is in CF adjustments but not IS."""
        facts = _make_facts(
            ("DepreciationDepletionAndAmortization", 2023, 15000e6, "10-K"),
        )

        units = _pick_first_units(facts, [
            "DepreciationDepletionAndAmortization",
            "DepreciationAndAmortization",
        ])

        assert units is not None
        val = _annual_value(units, "USD", 2023)
        assert val == pytest.approx(15000e6, rel=1e-6)

    def test_depreciation_amortization_variant(self):
        """DepreciationAndAmortization as alternative tag."""
        facts = _make_facts(
            ("DepreciationAndAmortization", 2023, 12000e6, "10-K"),
        )

        units = _pick_first_units(facts, [
            "DepreciationDepletionAndAmortization",
            "DepreciationAndAmortization",
        ])

        assert units is not None
        val = _annual_value(units, "USD", 2023)
        assert val == pytest.approx(12000e6, rel=1e-6)


# =============================================================================
# Enriched tag list coverage
# =============================================================================


class TestEnrichedTagLists:
    """Verify enriched tag lists find data that old lists missed."""

    def test_revenue_finds_revenues_tag(self):
        """XOM/NEE pattern: uses 'Revenues' not 'RevenueFromContract...'."""
        facts = _make_facts(
            ("Revenues", 2023, 344e9, "10-K"),
        )

        from app.ingest.sec import IS_TAGS
        units = _pick_first_units(facts, IS_TAGS["revenue"])

        assert units is not None
        val = _annual_value(units, "USD", 2023)
        assert val == pytest.approx(344e9, rel=1e-6)

    def test_cash_finds_cash_equivalents_short_term(self):
        """Some companies use CashCashEquivalentsAndShortTermInvestments."""
        facts = _make_facts(
            ("CashCashEquivalentsAndShortTermInvestments", 2023, 50e9, "10-K"),
        )

        from app.ingest.sec import BS_TAGS
        units = _pick_first_units(facts, BS_TAGS["cash"])

        assert units is not None

    def test_cfo_finds_continuing_operations_variant(self):
        """Some companies use the ContinuingOperations variant."""
        facts = _make_facts(
            ("NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", 2023, 60e9, "10-K"),
        )

        from app.ingest.sec import CF_TAGS
        units = _pick_first_units(facts, CF_TAGS["cfo"])

        assert units is not None

    def test_interest_expense_finds_debt_variant(self):
        """InterestAndDebtExpense variant (from concept_mappings.json)."""
        facts = _make_facts(
            ("InterestAndDebtExpense", 2023, 2500e6, "10-K"),
        )

        from app.ingest.sec import IS_TAGS
        units = _pick_first_units(facts, IS_TAGS["interest_expense"])

        assert units is not None

    def test_equity_finds_attributable_to_parent(self):
        """StockholdersEquityAttributableToParent variant."""
        facts = _make_facts(
            ("StockholdersEquityAttributableToParent", 2023, 118e9, "10-K"),
        )

        from app.ingest.sec import BS_TAGS
        units = _pick_first_units(facts, BS_TAGS["shareholder_equity"])

        assert units is not None

    def test_buybacks_finds_equity_variant(self):
        """PaymentsForRepurchaseOfEquity (broader than CommonStock)."""
        facts = _make_facts(
            ("PaymentsForRepurchaseOfEquity", 2023, 20e9, "10-K"),
        )

        from app.ingest.sec import CF_TAGS
        units = _pick_first_units(facts, CF_TAGS["buybacks"])

        assert units is not None


# =============================================================================
# _insert_statement enrichment integration
# =============================================================================


class TestInsertStatementEnrichment:
    """Test that _insert_statement applies fallback enrichment when facts provided."""

    @patch("app.ingest.sec.execute")
    def test_sga_fallback_applied(self, mock_execute):
        """SGA should be summed from components when primary tag is missing."""
        from app.ingest.sec import _insert_statement

        facts = _make_facts(
            ("SellingAndMarketingExpense", 2023, 22759e6, "10-K"),
            ("GeneralAndAdministrativeExpense", 2023, 7575e6, "10-K"),
        )
        units_cache = {"is": {k: None for k in [
            "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
            "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
        ]}}

        _insert_statement(1, 2023, "is", units_cache, facts=facts)

        call_kwargs = mock_execute.call_args[1]
        assert call_kwargs["sga"] == pytest.approx(22759e6 + 7575e6, rel=1e-6)

    @patch("app.ingest.sec.execute")
    def test_total_debt_fallback_applied(self, mock_execute):
        """total_debt should be summed from components when primary tag is missing."""
        from app.ingest.sec import _insert_statement

        facts = _make_facts(
            ("LongTermDebtNoncurrent", 2023, 40000e6, "10-K"),
            ("LongTermDebtCurrent", 2023, 5000e6, "10-K"),
        )
        units_cache = {"bs": {k: None for k in [
            "cash", "receivables", "inventory", "total_assets",
            "total_liabilities", "total_debt", "shareholder_equity",
        ]}}

        _insert_statement(1, 2023, "bs", units_cache, facts=facts)

        call_kwargs = mock_execute.call_args[1]
        assert call_kwargs["total_debt"] == pytest.approx(45000e6, rel=1e-6)

    @patch("app.ingest.sec.execute")
    def test_depreciation_cf_fallback_applied(self, mock_execute):
        """Depreciation should fall back to CF tags when IS tag is missing."""
        from app.ingest.sec import _insert_statement

        facts = _make_facts(
            ("DepreciationDepletionAndAmortization", 2023, 15000e6, "10-K"),
        )
        units_cache = {"is": {k: None for k in [
            "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
            "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
        ]}}

        _insert_statement(1, 2023, "is", units_cache, facts=facts)

        call_kwargs = mock_execute.call_args[1]
        assert call_kwargs["depreciation"] == pytest.approx(15000e6, rel=1e-6)

    @patch("app.ingest.sec.execute")
    def test_no_enrichment_without_facts(self, mock_execute):
        """When facts=None, no fallback enrichment should be attempted."""
        from app.ingest.sec import _insert_statement

        units_cache = {"is": {k: None for k in [
            "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
            "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
        ]}}

        _insert_statement(1, 2023, "is", units_cache, facts=None)

        call_kwargs = mock_execute.call_args[1]
        assert call_kwargs["sga"] is None
        assert call_kwargs["depreciation"] is None

    @patch("app.ingest.sec.execute")
    def test_enrichment_does_not_overwrite_existing(self, mock_execute):
        """When primary tag already has data, enrichment should NOT overwrite it."""
        from app.ingest.sec import _insert_statement, _pick_first_units

        # Facts with both combined and component SGA
        facts = _make_facts(
            ("SellingGeneralAndAdministrativeExpense", 2023, 30000e6, "10-K"),
            ("SellingAndMarketingExpense", 2023, 22759e6, "10-K"),
            ("GeneralAndAdministrativeExpense", 2023, 7575e6, "10-K"),
        )
        units_cache = {"is": {k: None for k in [
            "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
            "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
        ]}}
        # Set the primary SGA units from the combined tag
        units_cache["is"]["sga"] = _pick_first_units(facts, ["SellingGeneralAndAdministrativeExpense"])

        _insert_statement(1, 2023, "is", units_cache, facts=facts)

        call_kwargs = mock_execute.call_args[1]
        # Should use the combined tag value (30B), not the sum (30.3B)
        assert call_kwargs["sga"] == pytest.approx(30000e6, rel=1e-6)
