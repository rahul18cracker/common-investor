"""
Phase F: Performance Benchmarks for Metrics and Four Ms Computations

These tests measure execution time of key computation functions to establish
baseline performance and detect regressions. They are marked as 'slow' to
exclude from regular test runs.

Usage:
    pytest tests/test_performance_benchmarks.py -v --durations=0
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from typing import List, Dict


# =============================================================================
# Test Fixtures - Mock data for consistent benchmarking
# =============================================================================

def _generate_mock_is_series(years: int = 15) -> List[tuple]:
    """Generate mock income statement series for benchmarking."""
    base_year = 2010
    base_revenue = 100_000_000_000  # $100B
    base_eps = 5.0
    base_ebit = 15_000_000_000  # $15B
    
    return [
        (
            base_year + i,
            base_revenue * (1.05 ** i),  # 5% annual growth
            base_eps * (1.08 ** i),       # 8% EPS growth
            base_ebit * (1.06 ** i),      # 6% EBIT growth
        )
        for i in range(years)
    ]


def _generate_mock_cf_bs_rows(years: int = 15) -> List[Dict]:
    """Generate mock cash flow and balance sheet data for benchmarking."""
    base_year = 2010
    base_cfo = 20_000_000_000
    base_capex = 8_000_000_000
    base_debt = 50_000_000_000
    base_equity = 100_000_000_000
    base_cash = 30_000_000_000
    
    return [
        {
            "fy": base_year + i,
            "cfo": base_cfo * (1.04 ** i),
            "capex": base_capex * (1.03 ** i),
            "shares": 1_000_000_000,
            "ebit": 15_000_000_000 * (1.06 ** i),
            "taxes": 3_000_000_000 * (1.06 ** i),
            "debt": base_debt * (0.98 ** i),  # Decreasing debt
            "equity": base_equity * (1.05 ** i),
            "cash": base_cash * (1.02 ** i),
            "revenue": 100_000_000_000 * (1.05 ** i),
        }
        for i in range(years)
    ]


# =============================================================================
# Unit Function Benchmarks
# =============================================================================

class TestCAGRPerformance:
    """Benchmark CAGR calculation performance."""
    
    def test_cagr_single_calculation_speed(self):
        """CAGR should complete in microseconds."""
        from app.metrics.compute import cagr
        
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            cagr(100, 200, 5)
        elapsed = time.perf_counter() - start
        
        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 10, f"CAGR too slow: {avg_time_us:.2f}µs per call"
    
    def test_window_cagr_calculation_speed(self):
        """Window CAGR should complete quickly even with 15 years of data."""
        from app.metrics.compute import _calculate_window_cagr
        
        years = list(range(2010, 2025))
        values = [100 * (1.05 ** i) for i in range(15)]
        
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            _calculate_window_cagr(years, values, 10)
        elapsed = time.perf_counter() - start
        
        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 100, f"Window CAGR too slow: {avg_time_us:.2f}µs per call"


class TestSeriesComputationPerformance:
    """Benchmark series computation functions with mocked DB."""
    
    @patch('app.metrics.compute._fetch_is_series')
    def test_growth_metrics_computation_speed(self, mock_fetch):
        """Growth metrics should compute quickly."""
        from app.metrics.compute import compute_growth_metrics
        
        mock_fetch.return_value = _generate_mock_is_series(15)
        
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            compute_growth_metrics("0000320193")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 5, f"Growth metrics too slow: {avg_time_ms:.2f}ms per call"
    
    @patch('app.metrics.compute._fetch_is_series')
    def test_margin_stability_computation_speed(self, mock_fetch):
        """Margin stability should compute quickly."""
        from app.metrics.compute import margin_stability
        
        mock_fetch.return_value = _generate_mock_is_series(15)
        
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            margin_stability("0000320193")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 5, f"Margin stability too slow: {avg_time_ms:.2f}ms per call"
    
    @patch('app.metrics.compute._fetch_cf_bs_for_roic')
    def test_roic_series_computation_speed(self, mock_fetch):
        """ROIC series should compute quickly."""
        from app.metrics.compute import roic_series
        
        mock_fetch.return_value = _generate_mock_cf_bs_rows(15)
        
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            roic_series("0000320193")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 5, f"ROIC series too slow: {avg_time_ms:.2f}ms per call"


class TestFourMsPerformance:
    """Benchmark Four Ms computation functions."""
    
    @patch('app.nlp.fourm.service.roic_series')
    @patch('app.nlp.fourm.service.margin_stability')
    @patch('app.nlp.fourm.service.gross_margin_series')
    @patch('app.nlp.fourm.service.roic_persistence_score')
    def test_compute_moat_speed(self, mock_persist, mock_gm, mock_margin, mock_roic):
        """Moat computation should complete quickly."""
        from app.nlp.fourm.service import compute_moat
        
        mock_roic.return_value = [{"fy": 2020 + i, "roic": 0.15 + 0.01 * i} for i in range(5)]
        mock_margin.return_value = 0.85
        mock_gm.return_value = [{"fy": 2020 + i, "gross_margin": 0.35 + 0.005 * i} for i in range(10)]
        mock_persist.return_value = 4
        
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            compute_moat("0000320193")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 10, f"Moat computation too slow: {avg_time_ms:.2f}ms per call"
    
    @patch('app.nlp.fourm.service.coverage_series')
    @patch('app.nlp.fourm.service.latest_debt_to_equity')
    @patch('app.nlp.fourm.service.net_debt_series')
    def test_balance_sheet_resilience_speed(self, mock_nd, mock_de, mock_cov):
        """Balance sheet resilience should compute quickly."""
        from app.nlp.fourm.service import compute_balance_sheet_resilience
        
        mock_cov.return_value = [{"fy": 2020 + i, "coverage": 8.0 + i} for i in range(5)]
        mock_de.return_value = 0.4
        mock_nd.return_value = [{"fy": 2020 + i, "net_debt": 50e9 * (0.95 ** i)} for i in range(5)]
        
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            compute_balance_sheet_resilience("0000320193")
        elapsed = time.perf_counter() - start
        
        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 10, f"Balance sheet resilience too slow: {avg_time_ms:.2f}ms per call"


class TestHelperFunctionPerformance:
    """Benchmark helper functions added in Phase F."""
    
    def test_weighted_average_speed(self):
        """Weighted average helper should be very fast."""
        from app.nlp.fourm.service import _weighted_average
        
        scores = [0.8, 0.6, 0.9, 0.7, 0.85]
        weights = [0.3, 0.2, 0.25, 0.15, 0.1]
        
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            _weighted_average(scores, weights)
        elapsed = time.perf_counter() - start
        
        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 5, f"Weighted average too slow: {avg_time_us:.2f}µs per call"
    
    def test_normalize_score_speed(self):
        """Normalize score should be fast."""
        from app.nlp.fourm.service import _normalize_score
        
        tuples = [
            (0.18, 0.1, 0.25),
            (0.75, 0.4, 0.9),
            (0.85, 0.3, 0.9),
        ]
        
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            _normalize_score(tuples)
        elapsed = time.perf_counter() - start
        
        avg_time_us = (elapsed / iterations) * 1_000_000
        assert avg_time_us < 10, f"Normalize score too slow: {avg_time_us:.2f}µs per call"


# =============================================================================
# Memory Usage Tests (informational)
# =============================================================================

class TestMemoryUsage:
    """Test memory efficiency of data structures."""
    
    def test_series_memory_efficiency(self):
        """Series data should not consume excessive memory."""
        import sys
        
        # Generate a large series (50 years of data)
        large_series = [
            {"fy": 1970 + i, "value": 100.0 * (1.05 ** i)}
            for i in range(50)
        ]
        
        size_bytes = sys.getsizeof(large_series)
        # Each dict is ~200 bytes, 50 items should be < 15KB
        assert size_bytes < 15000, f"Series too large: {size_bytes} bytes"
