"""
Comprehensive unit tests for valuation/core module.

This test suite aims for 90%+ coverage of app/valuation/core.py
Testing Rule #1 investing valuation formulas: Sticker Price, MOS, Ten Cap, Payback Time.
"""
import pytest
from app.valuation.core import (
    StickerInputs,
    StickerResult,
    sticker_and_mos,
    ten_cap_price,
    payback_time,
)


pytestmark = pytest.mark.unit


class TestStickerAndMOS:
    """Test Sticker Price and Margin of Safety calculations."""

    def test_sticker_typical_growth(self):
        """Test sticker calculation with typical 15% growth."""
        # Arrange
        inp = StickerInputs(eps0=5.00, g=0.15, pe_cap=20, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp, mos_pct=0.5)
        
        # Assert
        assert result.future_eps == pytest.approx(20.227, rel=1e-2)  # 5 * 1.15^10
        assert result.terminal_pe == 20.0  # Capped at pe_cap
        assert result.future_price == pytest.approx(404.55, rel=1e-2)
        assert result.sticker == pytest.approx(100.00, rel=1e-2)
        assert result.mos_price == pytest.approx(50.00, rel=1e-2)  # 50% MOS

    def test_sticker_high_growth_capped(self):
        """Test that growth is capped at 50%."""
        # Arrange: Request 100% growth
        inp = StickerInputs(eps0=10.00, g=1.0, pe_cap=30, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp, mos_pct=0.5)
        
        # Assert: Growth should be capped at 50%
        assert result.future_eps == pytest.approx(576.65, rel=1e-2)  # 10 * 1.5^10

    def test_sticker_negative_growth_floored(self):
        """Test that negative growth is floored at 0%."""
        # Arrange
        inp = StickerInputs(eps0=8.00, g=-0.10, pe_cap=15, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp, mos_pct=0.5)
        
        # Assert: Growth treated as 0%
        assert result.future_eps == pytest.approx(8.00, rel=1e-6)

    def test_sticker_pe_calculation(self):
        """Test that PE is calculated as min(cap, 2*g*100)."""
        # Arrange: 10% growth, PE should be 2*10 = 20
        inp = StickerInputs(eps0=5.00, g=0.10, pe_cap=30, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp)
        
        # Assert
        assert result.terminal_pe == pytest.approx(20.0, rel=1e-2)  # 2 * 0.10 * 100

    def test_sticker_pe_at_cap(self):
        """Test PE is capped at pe_cap."""
        # Arrange: 20% growth would give PE=40, but cap is 25
        inp = StickerInputs(eps0=5.00, g=0.20, pe_cap=25, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp)
        
        # Assert
        assert result.terminal_pe == 25.0  # Capped

    def test_sticker_pe_minimum_five(self):
        """Test PE has minimum of 5."""
        # Arrange: 1% growth would give PE=2, but min is 5
        inp = StickerInputs(eps0=5.00, g=0.01, pe_cap=30, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp)
        
        # Assert
        assert result.terminal_pe == pytest.approx(5.0, rel=1e-6)

    def test_sticker_different_discount_rates(self):
        """Test sticker with different discount rates."""
        # Arrange
        inp_10 = StickerInputs(eps0=5.00, g=0.15, pe_cap=20, discount=0.10)
        inp_20 = StickerInputs(eps0=5.00, g=0.15, pe_cap=20, discount=0.20)
        
        # Act
        result_10 = sticker_and_mos(inp_10)
        result_20 = sticker_and_mos(inp_20)
        
        # Assert: Lower discount = higher sticker
        assert result_10.sticker > result_20.sticker

    def test_sticker_custom_mos_percentage(self):
        """Test MOS with different percentages."""
        # Arrange
        inp = StickerInputs(eps0=10.00, g=0.15, pe_cap=20, discount=0.15)
        
        # Act
        result_30 = sticker_and_mos(inp, mos_pct=0.3)
        result_70 = sticker_and_mos(inp, mos_pct=0.7)
        
        # Assert
        assert result_30.mos_price == pytest.approx(result_30.sticker * 0.7, rel=1e-6)
        assert result_70.mos_price == pytest.approx(result_70.sticker * 0.3, rel=1e-6)

    def test_sticker_default_values(self):
        """Test that default values are applied correctly."""
        # Arrange: Only provide eps0
        inp = StickerInputs(eps0=7.50)
        
        # Act
        result = sticker_and_mos(inp)
        
        # Assert: Check defaults were used
        assert inp.g == 0.15
        assert inp.pe_cap == 20
        assert inp.discount == 0.15

    def test_sticker_zero_eps(self):
        """Test sticker with zero current EPS."""
        # Arrange
        inp = StickerInputs(eps0=0.0, g=0.15, pe_cap=20, discount=0.15)
        
        # Act
        result = sticker_and_mos(inp)
        
        # Assert
        assert result.future_eps == 0.0
        assert result.sticker == 0.0
        assert result.mos_price == 0.0


class TestTenCapPrice:
    """Test Ten Cap valuation method."""

    def test_ten_cap_typical_value(self):
        """Test Ten Cap with typical owner earnings."""
        # Arrange
        oe_per_share = 10.00
        
        # Act
        result = ten_cap_price(oe_per_share)
        
        # Assert: Ten Cap = OE / 0.10
        assert result == pytest.approx(100.00, rel=1e-6)

    def test_ten_cap_fractional_value(self):
        """Test Ten Cap with fractional earnings."""
        # Arrange
        oe_per_share = 3.75
        
        # Act
        result = ten_cap_price(oe_per_share)
        
        # Assert
        assert result == pytest.approx(37.50, rel=1e-6)

    def test_ten_cap_none_input(self):
        """Test Ten Cap returns None for None input."""
        # Arrange
        oe_per_share = None
        
        # Act
        result = ten_cap_price(oe_per_share)
        
        # Assert
        assert result is None

    def test_ten_cap_zero_earnings(self):
        """Test Ten Cap returns None for zero earnings."""
        # Arrange
        oe_per_share = 0.0
        
        # Act
        result = ten_cap_price(oe_per_share)
        
        # Assert
        assert result is None

    def test_ten_cap_negative_earnings(self):
        """Test Ten Cap returns None for negative earnings."""
        # Arrange
        oe_per_share = -5.00
        
        # Act
        result = ten_cap_price(oe_per_share)
        
        # Assert
        assert result is None


class TestPaybackTime:
    """Test Payback Time calculation."""

    def test_payback_time_immediate(self):
        """Test payback when first year covers price."""
        # Arrange: $50 price, $60 earnings, 10% growth
        
        # Act
        result = payback_time(50.0, 60.0, 0.10)
        
        # Assert
        assert result == 1

    def test_payback_time_multiple_years(self):
        """Test payback over multiple years."""
        # Arrange: $100 price, $30/year earnings, 0% growth
        
        # Act
        result = payback_time(100.0, 30.0, 0.0)
        
        # Assert: 30+30+30+30 = 120 > 100 in year 4
        assert result == 4

    def test_payback_time_with_growth(self):
        """Test payback with growing earnings."""
        # Arrange: $100 price, $25 earnings, 20% growth
        # Year 1: 25, Year 2: 30, Year 3: 36, Year 4: 43.2
        # Cumulative: 25, 55, 91, 134.2
        
        # Act
        result = payback_time(100.0, 25.0, 0.20)
        
        # Assert
        assert result == 4

    def test_payback_time_never_pays_back(self):
        """Test when investment never pays back within max years."""
        # Arrange: $1000 price, $10/year, 0% growth
        
        # Act
        result = payback_time(1000.0, 10.0, 0.0, max_years=10)
        
        # Assert: 10*10 = 100 < 1000
        assert result is None

    def test_payback_time_invalid_price(self):
        """Test with invalid purchase price."""
        # Arrange
        
        # Act & Assert
        assert payback_time(0.0, 50.0, 0.10) is None
        assert payback_time(-10.0, 50.0, 0.10) is None

    def test_payback_time_none_earnings(self):
        """Test with None earnings."""
        # Arrange
        
        # Act
        result = payback_time(100.0, None, 0.10)
        
        # Assert
        assert result is None

    def test_payback_time_zero_earnings(self):
        """Test with zero earnings."""
        # Arrange
        
        # Act
        result = payback_time(100.0, 0.0, 0.10)
        
        # Assert
        assert result is None

    def test_payback_time_negative_earnings(self):
        """Test with negative earnings."""
        # Arrange
        
        # Act
        result = payback_time(100.0, -5.0, 0.10)
        
        # Assert
        assert result is None

    def test_payback_time_negative_growth(self):
        """Test that negative growth is floored at 0%."""
        # Arrange: $100 price, $30/year, -10% growth (treated as 0%)
        
        # Act
        result = payback_time(100.0, 30.0, -0.10)
        
        # Assert: Same as 0% growth
        assert result == 4

    def test_payback_time_custom_max_years(self):
        """Test with custom max years."""
        # Arrange: Would pay back in year 5, but max is 3
        
        # Act
        result = payback_time(100.0, 25.0, 0.0, max_years=3)
        
        # Assert
        assert result is None  # Doesn't pay back within 3 years

    def test_payback_time_exact_match(self):
        """Test when cumulative exactly matches price."""
        # Arrange: $100 price, $50/year, 0% growth
        
        # Act
        result = payback_time(100.0, 50.0, 0.0)
        
        # Assert
        assert result == 2
