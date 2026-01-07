"""
Integration tests for the metrics compute module
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCagr:
    """Tests for cagr function"""
    
    def test_cagr_valid_values(self):
        """Test CAGR calculation with valid values"""
        from app.metrics.compute import cagr
        
        result = cagr(100, 200, 5)
        
        assert result is not None
        assert 0.14 < result < 0.15  # ~14.87% CAGR
    
    def test_cagr_zero_years(self):
        """Test CAGR with zero years"""
        from app.metrics.compute import cagr
        
        result = cagr(100, 200, 0)
        
        assert result is None
    
    def test_cagr_negative_years(self):
        """Test CAGR with negative years"""
        from app.metrics.compute import cagr
        
        result = cagr(100, 200, -1)
        
        assert result is None
    
    def test_cagr_none_first(self):
        """Test CAGR with None first value"""
        from app.metrics.compute import cagr
        
        result = cagr(None, 200, 5)
        
        assert result is None
    
    def test_cagr_none_last(self):
        """Test CAGR with None last value"""
        from app.metrics.compute import cagr
        
        result = cagr(100, None, 5)
        
        assert result is None
    
    def test_cagr_zero_first(self):
        """Test CAGR with zero first value"""
        from app.metrics.compute import cagr
        
        result = cagr(0, 200, 5)
        
        assert result is None
    
    def test_cagr_zero_last(self):
        """Test CAGR with zero last value"""
        from app.metrics.compute import cagr
        
        result = cagr(100, 0, 5)
        
        assert result is None
    
    def test_cagr_negative_first(self):
        """Test CAGR with negative first value"""
        from app.metrics.compute import cagr
        
        result = cagr(-100, 200, 5)
        
        assert result is None


class TestCalculateWindowCagr:
    """Tests for _calculate_window_cagr function"""
    
    def test_window_cagr_valid(self):
        """Test window CAGR with valid data"""
        from app.metrics.compute import _calculate_window_cagr
        
        years = [2019, 2020, 2021, 2022, 2023]
        values = [100.0, 110.0, 120.0, 130.0, 150.0]
        
        result = _calculate_window_cagr(years, values, 5)
        
        assert result is not None
        assert result > 0
    
    def test_window_cagr_empty_years(self):
        """Test window CAGR with empty years"""
        from app.metrics.compute import _calculate_window_cagr
        
        result = _calculate_window_cagr([], [], 5)
        
        assert result is None
    
    def test_window_cagr_mismatched_lengths(self):
        """Test window CAGR with mismatched lengths"""
        from app.metrics.compute import _calculate_window_cagr
        
        years = [2019, 2020, 2021]
        values = [100.0, 110.0]
        
        result = _calculate_window_cagr(years, values, 5)
        
        assert result is None
    
    def test_window_cagr_all_none_values(self):
        """Test window CAGR with all None values"""
        from app.metrics.compute import _calculate_window_cagr
        
        years = [2019, 2020, 2021]
        values = [None, None, None]
        
        result = _calculate_window_cagr(years, values, 5)
        
        assert result is None
    
    def test_window_cagr_single_value(self):
        """Test window CAGR with single non-None value"""
        from app.metrics.compute import _calculate_window_cagr
        
        years = [2019, 2020, 2021]
        values = [None, 100.0, None]
        
        result = _calculate_window_cagr(years, values, 5)
        
        assert result is None


class TestFetchIsSeries:
    """Tests for _fetch_is_series function"""
    
    def test_fetch_is_series_success(self):
        """Test fetching income statement series"""
        from app.metrics.compute import _fetch_is_series
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 1000000, 5.0, 200000),
                (2022, 1100000, 5.5, 220000),
                (2023, 1200000, 6.0, 240000),
            ]
            
            result = _fetch_is_series("0000320193")
            
            assert len(result) == 3
            assert result[0] == (2021, 1000000.0, 5.0, 200000.0)
    
    def test_fetch_is_series_with_nulls(self):
        """Test fetching income statement series with null values"""
        from app.metrics.compute import _fetch_is_series
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 1000000, None, 200000),
                (2022, None, 5.5, None),
            ]
            
            result = _fetch_is_series("0000320193")
            
            assert len(result) == 2
            assert result[0] == (2021, 1000000.0, None, 200000.0)
            assert result[1] == (2022, None, 5.5, None)


class TestFetchCfBsForRoic:
    """Tests for _fetch_cf_bs_for_roic function"""
    
    def test_fetch_cf_bs_for_roic_success(self):
        """Test fetching cash flow and balance sheet data for ROIC"""
        from app.metrics.compute import _fetch_cf_bs_for_roic
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 100000, -20000, 1000, 50000, 10000, 200000, 500000, 50000, 1000000),
                (2022, 110000, -25000, 1000, 55000, 11000, 220000, 550000, 60000, 1100000),
            ]
            
            result = _fetch_cf_bs_for_roic("0000320193")
            
            assert len(result) == 2
            assert 'fy' in result[0]
            assert 'cfo' in result[0]


class TestComputeGrowthMetrics:
    """Tests for compute_growth_metrics function"""
    
    def test_compute_growth_metrics_success(self):
        """Test computing growth metrics with valid data"""
        from app.metrics.compute import compute_growth_metrics
        
        with patch('app.metrics.compute._fetch_is_series') as mock_fetch:
            mock_fetch.return_value = [
                (2019, 100000.0, 1.0, 10000.0),
                (2020, 110000.0, 1.1, 11000.0),
                (2021, 120000.0, 1.2, 12000.0),
                (2022, 130000.0, 1.3, 13000.0),
                (2023, 150000.0, 1.5, 15000.0),
            ]
            
            result = compute_growth_metrics("0000320193")
            
            assert "rev_cagr_5y" in result
            assert "eps_cagr_5y" in result
    
    def test_compute_growth_metrics_empty(self):
        """Test computing growth metrics with no data"""
        from app.metrics.compute import compute_growth_metrics
        
        with patch('app.metrics.compute._fetch_is_series') as mock_fetch:
            mock_fetch.return_value = []
            
            result = compute_growth_metrics("0000320193")
            
            assert result["rev_cagr_5y"] is None
            assert result["eps_cagr_5y"] is None


class TestRoicSeries:
    """Tests for roic_series function"""
    
    def test_roic_series_success(self):
        """Test computing ROIC series with valid data"""
        from app.metrics.compute import roic_series
        
        with patch('app.metrics.compute._fetch_cf_bs_for_roic') as mock_fetch:
            mock_fetch.return_value = [
                {'fy': 2021, 'cfo': 100000, 'capex': -20000, 'shares': 1000, 
                 'ebit': 50000, 'taxes': 10000, 'debt': 200000, 'equity': 500000, 
                 'cash': 50000, 'revenue': 1000000},
                {'fy': 2022, 'cfo': 110000, 'capex': -25000, 'shares': 1000, 
                 'ebit': 55000, 'taxes': 11000, 'debt': 220000, 'equity': 550000, 
                 'cash': 60000, 'revenue': 1100000},
            ]
            
            result = roic_series("0000320193")
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert "fy" in result[0]
            assert "roic" in result[0]
    
    def test_roic_series_empty(self):
        """Test computing ROIC series with no data"""
        from app.metrics.compute import roic_series
        
        with patch('app.metrics.compute._fetch_cf_bs_for_roic') as mock_fetch:
            mock_fetch.return_value = []
            
            result = roic_series("0000320193")
            
            assert isinstance(result, list)
            assert len(result) == 0


class TestOwnerEarningsSeries:
    """Tests for owner_earnings_series function"""
    
    def test_owner_earnings_series_with_data(self):
        """Test owner earnings series with valid data"""
        from app.metrics.compute import owner_earnings_series
        
        with patch('app.metrics.compute._fetch_cf_bs_for_roic') as mock_fetch:
            mock_fetch.return_value = [
                {'fy': 2021, 'cfo': 100000, 'capex': -20000, 'shares': 1000, 
                 'ebit': 50000, 'taxes': 10000, 'debt': 200000, 'equity': 500000, 
                 'cash': 50000, 'revenue': 1000000},
                {'fy': 2022, 'cfo': 110000, 'capex': -25000, 'shares': 1000, 
                 'ebit': 55000, 'taxes': 11000, 'debt': 220000, 'equity': 550000, 
                 'cash': 60000, 'revenue': 1100000},
            ]
            
            result = owner_earnings_series("0000320193")
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert "owner_earnings" in result[0]
    
    def test_owner_earnings_series_empty(self):
        """Test owner earnings series with empty data"""
        from app.metrics.compute import owner_earnings_series
        
        with patch('app.metrics.compute._fetch_cf_bs_for_roic') as mock_fetch:
            mock_fetch.return_value = []
            
            result = owner_earnings_series("0000320193")
            
            assert isinstance(result, list)
            assert len(result) == 0


class TestRoicAverage:
    """Tests for roic_average function"""
    
    def test_roic_average_with_data(self):
        """Test ROIC average with valid data"""
        from app.metrics.compute import roic_average
        
        with patch('app.metrics.compute.roic_series') as mock_roic:
            mock_roic.return_value = [
                {"fy": 2021, "roic": 0.15},
                {"fy": 2022, "roic": 0.16},
                {"fy": 2023, "roic": 0.17},
            ]
            
            result = roic_average("0000320193", years=3)
            
            assert result is not None
            assert 0.15 < result < 0.18
    
    def test_roic_average_empty_data(self):
        """Test ROIC average with empty data"""
        from app.metrics.compute import roic_average
        
        with patch('app.metrics.compute.roic_series') as mock_roic:
            mock_roic.return_value = []
            
            result = roic_average("0000320193")
            
            assert result is None


class TestLatestDebtToEquity:
    """Tests for latest_debt_to_equity function"""
    
    def test_latest_debt_to_equity_success(self):
        """Test latest debt to equity with valid data"""
        from app.metrics.compute import latest_debt_to_equity
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.first.return_value = (200000.0, 500000.0)
            
            result = latest_debt_to_equity("0000320193")
            
            assert result is not None
            assert result == 0.4  # 200000 / 500000
    
    def test_latest_debt_to_equity_no_data(self):
        """Test latest debt to equity with no data"""
        from app.metrics.compute import latest_debt_to_equity
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.first.return_value = None
            
            result = latest_debt_to_equity("0000320193")
            
            assert result is None


class TestTimeseriesAll:
    """Tests for timeseries_all function"""
    
    def test_timeseries_all(self):
        """Test timeseries_all returns all series"""
        from app.metrics.compute import timeseries_all
        
        with patch('app.metrics.compute.revenue_eps_series') as mock_rev, \
             patch('app.metrics.compute.owner_earnings_series') as mock_oe, \
             patch('app.metrics.compute.roic_series') as mock_roic, \
             patch('app.metrics.compute.coverage_series') as mock_cov:
            
            mock_rev.return_value = [{"fy": 2023, "revenue": 100000}]
            mock_oe.return_value = [{"fy": 2023, "owner_earnings": 50000}]
            mock_roic.return_value = [{"fy": 2023, "roic": 0.15}]
            mock_cov.return_value = [{"fy": 2023, "coverage": 5.0}]
            
            result = timeseries_all("0000320193")
            
            assert "is" in result
            assert "owner_earnings" in result
            assert "roic" in result
            assert "coverage" in result


class TestLatestOwnerEarningsPs:
    """Tests for latest_owner_earnings_ps function"""
    
    def test_latest_owner_earnings_ps_with_data(self):
        """Test latest owner earnings per share with valid data"""
        from app.metrics.compute import latest_owner_earnings_ps
        
        with patch('app.metrics.compute.owner_earnings_series') as mock_oe:
            mock_oe.return_value = [
                {"fy": 2021, "owner_earnings": 80000, "owner_earnings_ps": 80.0},
                {"fy": 2022, "owner_earnings": 85000, "owner_earnings_ps": 85.0},
                {"fy": 2023, "owner_earnings": 90000, "owner_earnings_ps": 90.0},
            ]
            
            result = latest_owner_earnings_ps("0000320193")
            
            assert result == 90.0
    
    def test_latest_owner_earnings_ps_empty(self):
        """Test latest owner earnings per share with empty data"""
        from app.metrics.compute import latest_owner_earnings_ps
        
        with patch('app.metrics.compute.owner_earnings_series') as mock_oe:
            mock_oe.return_value = []
            
            result = latest_owner_earnings_ps("0000320193")
            
            assert result is None


class TestCoverageSeries:
    """Tests for coverage_series function"""
    
    def test_coverage_series_with_data(self):
        """Test coverage series with valid data"""
        from app.metrics.compute import coverage_series
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 50000.0, 10000.0),
                (2022, 55000.0, 11000.0),
                (2023, 60000.0, 12000.0),
            ]
            
            result = coverage_series("0000320193")
            
            assert len(result) == 3
            assert result[0]["fy"] == 2021
            assert result[0]["coverage"] == 5.0  # 50000 / 10000
    
    def test_coverage_series_zero_interest(self):
        """Test coverage series with zero interest expense"""
        from app.metrics.compute import coverage_series
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 50000.0, 0.0),
            ]
            
            result = coverage_series("0000320193")
            
            assert len(result) == 1
            assert result[0]["coverage"] is None


class TestMarginStability:
    """Tests for margin_stability function"""
    
    def test_margin_stability_with_data(self):
        """Test margin stability with valid data"""
        from app.metrics.compute import margin_stability
        
        with patch('app.metrics.compute._fetch_is_series') as mock_fetch:
            mock_fetch.return_value = [
                (2021, 100000.0, 1.0, 10000.0),
                (2022, 110000.0, 1.1, 11000.0),
                (2023, 120000.0, 1.2, 12000.0),
                (2024, 130000.0, 1.3, 13000.0),
            ]
            
            result = margin_stability("0000320193")
            
            assert result is not None
            assert 0 <= result <= 1
    
    def test_margin_stability_insufficient_data(self):
        """Test margin stability with insufficient data"""
        from app.metrics.compute import margin_stability
        
        with patch('app.metrics.compute._fetch_is_series') as mock_fetch:
            mock_fetch.return_value = [
                (2021, 100000.0, 1.0, 10000.0),
            ]
            
            result = margin_stability("0000320193")
            
            assert result is None


class TestLatestEps:
    """Tests for latest_eps function"""
    
    def test_latest_eps_with_data(self):
        """Test latest EPS with valid data"""
        from app.metrics.compute import latest_eps
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.first.return_value = (5.25,)
            
            result = latest_eps("0000320193")
            
            assert result == 5.25
    
    def test_latest_eps_no_data(self):
        """Test latest EPS with no data"""
        from app.metrics.compute import latest_eps
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.first.return_value = None
            
            result = latest_eps("0000320193")
            
            assert result is None


class TestRevenueEpsSeries:
    """Tests for revenue_eps_series function"""
    
    def test_revenue_eps_series_with_data(self):
        """Test revenue EPS series with valid data"""
        from app.metrics.compute import revenue_eps_series
        
        with patch('app.metrics.compute.execute') as mock_execute:
            mock_execute.return_value.fetchall.return_value = [
                (2021, 100000.0, 5.0),
                (2022, 110000.0, 5.5),
                (2023, 120000.0, 6.0),
            ]
            
            result = revenue_eps_series("0000320193")
            
            assert len(result) == 3
            assert result[0]["fy"] == 2021
            assert result[0]["revenue"] == 100000.0
            assert result[0]["eps"] == 5.0


class TestLatestOwnerEarningsGrowth:
    """Tests for latest_owner_earnings_growth function"""
    
    def test_latest_owner_earnings_growth_with_data(self):
        """Test latest owner earnings growth with valid data"""
        from app.metrics.compute import latest_owner_earnings_growth
        
        with patch('app.metrics.compute.owner_earnings_series') as mock_oe:
            mock_oe.return_value = [
                {"fy": 2019, "owner_earnings": 50000, "owner_earnings_ps": 50.0},
                {"fy": 2020, "owner_earnings": 55000, "owner_earnings_ps": 55.0},
                {"fy": 2021, "owner_earnings": 60000, "owner_earnings_ps": 60.0},
                {"fy": 2022, "owner_earnings": 70000, "owner_earnings_ps": 70.0},
                {"fy": 2023, "owner_earnings": 80000, "owner_earnings_ps": 80.0},
            ]
            
            result = latest_owner_earnings_growth("0000320193")
            
            assert result is not None
    
    def test_latest_owner_earnings_growth_insufficient_data(self):
        """Test latest owner earnings growth with insufficient data"""
        from app.metrics.compute import latest_owner_earnings_growth
        
        with patch('app.metrics.compute.owner_earnings_series') as mock_oe:
            mock_oe.return_value = [
                {"fy": 2023, "owner_earnings": 80000, "owner_earnings_ps": 80.0},
            ]
            
            result = latest_owner_earnings_growth("0000320193")
            
            assert result is None
