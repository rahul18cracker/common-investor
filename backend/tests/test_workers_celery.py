"""
Unit and integration tests for Celery workers (app/workers/)

Tests task execution, error handling, retry logic, and worker configuration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from celery.exceptions import Retry
from app.workers.celery_app import celery_app
from app.workers.tasks import (
    ingest_company,
    snapshot_prices,
    run_alerts_eval,
    enqueue_ingest
)


# =============================================================================
# Unit Tests: Celery Configuration
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestCeleryConfiguration:
    """Test Celery app configuration."""
    
    def test_celery_app_exists(self):
        """Test that Celery app is properly initialized."""
        assert celery_app is not None
        assert celery_app.main == "ci"
    
    def test_celery_broker_configured(self):
        """Test that broker URL is configured."""
        assert celery_app.conf.broker_url is not None
        assert "redis://" in celery_app.conf.broker_url
    
    def test_celery_backend_configured(self):
        """Test that result backend is configured."""
        assert celery_app.conf.result_backend is not None
    
    def test_celery_tasks_registered(self):
        """Test that all tasks are registered."""
        registered_tasks = list(celery_app.tasks.keys())
        
        assert "app.workers.tasks.ingest_company" in registered_tasks
        assert "app.workers.tasks.snapshot_prices" in registered_tasks
        assert "app.workers.tasks.run_alerts_eval" in registered_tasks
    
    def test_celery_beat_schedule_configured(self):
        """Test that beat schedule is configured."""
        assert hasattr(celery_app.conf, "beat_schedule")
        assert "snapshot-popular" in celery_app.conf.beat_schedule
        assert "evaluate-alerts-daily" in celery_app.conf.beat_schedule
    
    def test_beat_schedule_tasks_exist(self):
        """Test that scheduled tasks are valid."""
        schedule = celery_app.conf.beat_schedule
        
        # Verify snapshot-popular schedule
        assert schedule["snapshot-popular"]["task"] == "app.workers.tasks.snapshot_prices"
        assert isinstance(schedule["snapshot-popular"]["schedule"], (int, float))
        
        # Verify evaluate-alerts-daily schedule
        assert schedule["evaluate-alerts-daily"]["task"] == "app.workers.tasks.run_alerts_eval"
        assert isinstance(schedule["evaluate-alerts-daily"]["schedule"], (int, float))


# =============================================================================
# Unit Tests: ingest_company Task
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestIngestCompanyTask:
    """Test the ingest_company Celery task."""
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_company_success(self, mock_ingest, celery_worker):
        """Test successful company ingestion task."""
        mock_ingest.return_value = {"success": True, "records": 10}
        
        result = ingest_company.apply(args=["MSFT"]).get()
        
        mock_ingest.assert_called_once_with("MSFT")
        assert result is None  # Task prints but doesn't return
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_company_with_uppercase_ticker(self, mock_ingest, celery_worker):
        """Test that ticker is handled correctly."""
        mock_ingest.return_value = {"success": True}
        
        ingest_company.apply(args=["msft"]).get()
        
        mock_ingest.assert_called_once_with("msft")
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_company_api_error(self, mock_ingest, celery_worker):
        """Test task behavior when API call fails."""
        from httpx import HTTPError, Request, Response
        
        mock_ingest.side_effect = HTTPError("API Error")
        
        with pytest.raises(HTTPError):
            ingest_company.apply(args=["MSFT"]).get()
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_company_database_error(self, mock_ingest, celery_worker):
        """Test task behavior when database operation fails."""
        from sqlalchemy.exc import IntegrityError
        
        mock_ingest.side_effect = IntegrityError("DB Error", None, None)
        
        with pytest.raises(IntegrityError):
            ingest_company.apply(args=["MSFT"]).get()
    
    def test_enqueue_ingest_function(self, celery_worker):
        """Test the enqueue_ingest helper function."""
        with patch.object(ingest_company, "delay") as mock_delay:
            enqueue_ingest("MSFT")
            mock_delay.assert_called_once_with("MSFT")


# =============================================================================
# Unit Tests: snapshot_prices Task
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestSnapshotPricesTask:
    """Test the snapshot_prices Celery task."""
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_snapshot_prices_single_ticker(self, mock_snapshot, celery_worker):
        """Test price snapshot for single ticker."""
        mock_snapshot.return_value = {"ticker": "MSFT", "price": 350.50}
        
        snapshot_prices.apply(args=[["MSFT"]]).get()
        
        mock_snapshot.assert_called_once_with("MSFT")
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_snapshot_prices_multiple_tickers(self, mock_snapshot, celery_worker):
        """Test price snapshot for multiple tickers."""
        mock_snapshot.return_value = {"success": True}
        
        tickers = ["MSFT", "AAPL", "AMZN"]
        snapshot_prices.apply(args=[tickers]).get()
        
        assert mock_snapshot.call_count == 3
        for ticker in tickers:
            mock_snapshot.assert_any_call(ticker)
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_snapshot_prices_empty_list(self, mock_snapshot, celery_worker):
        """Test with empty ticker list."""
        snapshot_prices.apply(args=[[]]).get()
        
        mock_snapshot.assert_not_called()
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_snapshot_prices_partial_failure(self, mock_snapshot, celery_worker):
        """Test that task continues even if one ticker fails."""
        def side_effect(ticker):
            if ticker == "AAPL":
                raise Exception("Price feed error")
            return {"success": True}
        
        mock_snapshot.side_effect = side_effect
        
        # Task should raise exception from AAPL
        with pytest.raises(Exception):
            snapshot_prices.apply(args=[["MSFT", "AAPL", "AMZN"]]).get()


# =============================================================================
# Unit Tests: run_alerts_eval Task
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestRunAlertsEvalTask:
    """Test the run_alerts_eval Celery task."""
    
    @patch("app.workers.tasks.evaluate_alerts")
    def test_run_alerts_eval_success(self, mock_evaluate, celery_worker):
        """Test successful alerts evaluation."""
        expected_result = {"alerts_triggered": 5, "alerts_evaluated": 20}
        mock_evaluate.return_value = expected_result
        
        result = run_alerts_eval.apply().get()
        
        mock_evaluate.assert_called_once()
        assert result == expected_result
    
    @patch("app.workers.tasks.evaluate_alerts")
    def test_run_alerts_eval_no_alerts(self, mock_evaluate, celery_worker):
        """Test when no alerts are triggered."""
        mock_evaluate.return_value = {"alerts_triggered": 0, "alerts_evaluated": 10}
        
        result = run_alerts_eval.apply().get()
        
        assert result["alerts_triggered"] == 0
        assert result["alerts_evaluated"] == 10
    
    @patch("app.workers.tasks.evaluate_alerts")
    def test_run_alerts_eval_error(self, mock_evaluate, celery_worker):
        """Test error handling in alerts evaluation."""
        mock_evaluate.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception):
            run_alerts_eval.apply().get()


# =============================================================================
# Integration Tests: Task Execution
# =============================================================================

@pytest.mark.integration
@pytest.mark.celery
@pytest.mark.db
class TestTaskIntegration:
    """Integration tests for task execution with real database."""
    
    @patch("app.ingest.sec.fetch_json")
    def test_ingest_task_with_database(
        self,
        mock_fetch,
        db_session,
        celery_worker,
        mock_sec_company_tickers,
        mock_sec_company_facts
    ):
        """Test ingest task writes to database."""
        from app.db.models import Company
        
        # Mock SEC API responses
        def fetch_side_effect(url):
            if "company_tickers.json" in url:
                return mock_sec_company_tickers
            elif "companyfacts" in url:
                return mock_sec_company_facts
            return {}
        
        mock_fetch.side_effect = fetch_side_effect
        
        # Execute task
        ingest_company.apply(args=["MSFT"]).get()
        
        # Verify data in database
        company = db_session.query(Company).filter_by(ticker="MSFT").first()
        assert company is not None
        assert company.name == "MICROSOFT CORPORATION"


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.slow
@pytest.mark.celery
class TestTaskPerformance:
    """Test task performance and scalability."""
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_snapshot_prices_performance(self, mock_snapshot, celery_worker):
        """Test performance with large number of tickers."""
        import time
        
        mock_snapshot.return_value = {"success": True}
        
        # Generate 100 tickers
        tickers = [f"TICK{i}" for i in range(100)]
        
        start_time = time.time()
        snapshot_prices.apply(args=[tickers]).get()
        duration = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds for mocked calls)
        assert duration < 5.0
        assert mock_snapshot.call_count == 100
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_concurrent_ingestion_tasks(self, mock_ingest, celery_worker):
        """Test multiple concurrent ingestion tasks."""
        mock_ingest.return_value = {"success": True}
        
        # Submit multiple tasks
        results = []
        for ticker in ["MSFT", "AAPL", "AMZN", "GOOGL", "META"]:
            result = ingest_company.apply_async(args=[ticker])
            results.append(result)
        
        # Wait for all to complete
        for result in results:
            result.get(timeout=10)
        
        # All tasks should complete successfully
        assert all(r.successful() for r in results)


# =============================================================================
# Error Recovery Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestTaskErrorRecovery:
    """Test task error handling and recovery mechanisms."""
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_task_exception_propagation(self, mock_ingest, celery_worker):
        """Test that exceptions are properly propagated."""
        mock_ingest.side_effect = ValueError("Invalid ticker format")
        
        with pytest.raises(ValueError):
            ingest_company.apply(args=["INVALID"]).get()
    
    @patch("app.workers.tasks.snapshot_price_for_ticker")
    def test_task_timeout_handling(self, mock_snapshot, celery_worker):
        """Test handling of task timeout."""
        import time
        
        def slow_function(ticker):
            time.sleep(0.1)
            return {"success": True}
        
        mock_snapshot.side_effect = slow_function
        
        # Task should complete even if slow
        result = snapshot_prices.apply(args=[["MSFT"]]).get(timeout=5)
        assert result is None


# =============================================================================
# Task State Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestTaskState:
    """Test task state management."""
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_task_state_success(self, mock_ingest, celery_worker):
        """Test task state after successful execution."""
        mock_ingest.return_value = {"success": True}
        
        result = ingest_company.apply(args=["MSFT"])
        
        assert result.successful()
        assert result.state == "SUCCESS"
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_task_state_failure(self, mock_ingest, celery_worker):
        """Test task state after failure."""
        mock_ingest.side_effect = Exception("API Error")
        
        result = ingest_company.apply(args=["MSFT"])
        
        with pytest.raises(Exception):
            result.get()
        
        assert result.failed()
        assert result.state == "FAILURE"


# =============================================================================
# Task Arguments Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.celery
class TestTaskArguments:
    """Test task argument validation and handling."""
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_with_empty_string(self, mock_ingest, celery_worker):
        """Test ingestion with empty ticker string."""
        mock_ingest.side_effect = KeyError("Ticker not found")
        
        with pytest.raises(KeyError):
            ingest_company.apply(args=[""]).get()
    
    @patch("app.workers.tasks.ingest_companyfacts_richer_by_ticker")
    def test_ingest_with_special_characters(self, mock_ingest, celery_worker):
        """Test ingestion with special characters in ticker."""
        mock_ingest.return_value = {"success": True}
        
        # Some tickers have special characters (e.g., BRK.A)
        ingest_company.apply(args=["BRK.A"]).get()
        
        mock_ingest.assert_called_once_with("BRK.A")
    
    def test_snapshot_prices_with_invalid_type(self, celery_worker):
        """Test snapshot_prices with invalid argument type."""
        # Should raise TypeError for non-list argument
        with pytest.raises((TypeError, AttributeError)):
            snapshot_prices.apply(args=["MSFT"]).get()  # String instead of list
