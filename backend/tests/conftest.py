"""
Pytest configuration and shared fixtures for all tests.

This module provides:
- Database fixtures (test database, session management)
- API client fixtures (FastAPI test client)
- Celery fixtures (test workers, eager mode)
- Mock fixtures (SEC API, external services)
- Data factories (sample companies, financial data)
"""

import os

# CRITICAL: Set test environment variables BEFORE any imports
# This must happen before app modules are imported to prevent
# session.py from creating a PostgreSQL engine in CI
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Test Redis DB
os.environ["SEC_USER_AGENT"] = "TestCommonInvestor/1.0 test@example.com"
os.environ["TESTING"] = "1"

# flake8: noqa: E402 (imports below env setup are intentional)
import pytest  # noqa: E402
from typing import Generator  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker, Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db import session as db_module  # noqa: E402
from app.workers.celery_app import celery_app  # noqa: E402


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """
    Create a test database engine using SQLite in-memory.
    
    Session-scoped to reuse across all tests for performance.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test.
    
    Function-scoped to ensure test isolation.
    Cleans up all data after each test for true isolation.
    
    Note: Automatically sets up the thread-local session so execute() 
    calls work correctly in tests.
    """
    # Ensure the app's engine points to our test engine
    db_module.engine = test_engine
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = SessionLocal()
    
    # Set up thread-local session for execute() calls
    db_module.set_test_session(session)
    
    try:
        yield session
    finally:
        # Cleanup - delete all data from all tables
        session.rollback()  # Rollback any pending transactions
        
        # Delete all data in reverse order to handle foreign keys
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        
        session.close()
        
        # Clear thread-local session
        db_module.clear_test_session()


@pytest.fixture(scope="function")
def override_execute(db_session):
    """
    Override the execute function to use test database session.
    """
    def _override_execute(sql: str, **params):
        from sqlalchemy import text
        return db_session.execute(text(sql), params)
    
    return _override_execute


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(test_engine, db_session) -> TestClient:
    """
    FastAPI test client with database session properly injected.
    
    This ensures that both ORM operations (db_session.add/commit) and
    raw SQL operations (execute()) use the same database connection,
    allowing tests to see data created by fixtures.
    
    Uses thread-local session injection so all execute() calls throughout
    the codebase use the test session automatically.
    
    Note: test_engine dependency ensures tables are created before tests run.
    """
    # Ensure the app's engine points to our test engine with tables
    db_module.engine = test_engine
    
    # Set the test session in thread-local storage
    db_module.set_test_session(db_session)
    
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Clear the test session
        db_module.clear_test_session()


# =============================================================================
# Celery Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def celery_config():
    """
    Celery configuration for testing.
    """
    return {
        "broker_url": "redis://localhost:6379/15",
        "result_backend": "redis://localhost:6379/15",
        "task_always_eager": True,  # Execute tasks synchronously
        "task_eager_propagates": True,  # Propagate exceptions
        "task_ignore_result": False,
    }


@pytest.fixture(scope="function")
def celery_worker(celery_config):
    """
    Celery worker in eager mode for testing.
    """
    celery_app.conf.update(celery_config)
    yield celery_app
    celery_app.conf.task_always_eager = False


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_sec_company_tickers():
    """
    Mock SEC company tickers API response.
    """
    return {
        "0": {
            "cik_str": 789019,
            "ticker": "MSFT",
            "title": "MICROSOFT CORPORATION"
        },
        "1": {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "APPLE INC"
        },
        "2": {
            "cik_str": 1018724,
            "ticker": "AMZN",
            "title": "AMAZON COM INC"
        }
    }


@pytest.fixture
def mock_sec_company_facts():
    """
    Mock SEC company facts API response with sample financial data.
    """
    return {
        "cik": 789019,
        "entityName": "MICROSOFT CORPORATION",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "label": "Revenues",
                    "description": "Total revenues",
                    "units": {
                        "USD": [
                            {"end": "2023-06-30", "val": 211915000000, "fy": 2023, "form": "10-K"},
                            {"end": "2022-06-30", "val": 198270000000, "fy": 2022, "form": "10-K"},
                            {"end": "2021-06-30", "val": 168088000000, "fy": 2021, "form": "10-K"},
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "label": "Earnings Per Share, Diluted",
                    "description": "Diluted EPS",
                    "units": {
                        "USD/shares": [
                            {"end": "2023-06-30", "val": 9.72, "fy": 2023, "form": "10-K"},
                            {"end": "2022-06-30", "val": 9.21, "fy": 2022, "form": "10-K"},
                            {"end": "2021-06-30", "val": 8.05, "fy": 2021, "form": "10-K"},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "label": "Net Income",
                    "description": "Net income or loss",
                    "units": {
                        "USD": [
                            {"end": "2023-06-30", "val": 72361000000, "fy": 2023, "form": "10-K"},
                            {"end": "2022-06-30", "val": 72738000000, "fy": 2022, "form": "10-K"},
                            {"end": "2021-06-30", "val": 61271000000, "fy": 2021, "form": "10-K"},
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_httpx_client(httpx_mock, mock_sec_company_tickers, mock_sec_company_facts):
    """
    Mock HTTP client for SEC API calls.
    """
    # Mock company tickers endpoint
    httpx_mock.add_response(
        url="https://www.sec.gov/files/company_tickers.json",
        json=mock_sec_company_tickers,
    )
    
    # Mock company facts endpoint for MSFT  
    httpx_mock.add_response(
        url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
        json=mock_sec_company_facts,
    )
    
    # Allow un-matched requests to avoid errors
    httpx_mock.non_mocked_hosts = []
    
    return httpx_mock


# =============================================================================
# Data Factory Fixtures
# =============================================================================

@pytest.fixture
def sample_company_data():
    """
    Sample company data for testing.
    """
    return {
        "cik": "0000789019",
        "ticker": "MSFT",
        "name": "MICROSOFT CORPORATION"
    }


@pytest.fixture
def sample_filing_data():
    """
    Sample filing data for testing.
    """
    return {
        "cik": "0000789019",
        "form": "10-K",
        "accession": "0000789019-23-000030",
        "period_end": "2023-06-30"
    }


@pytest.fixture
def sample_financial_metrics():
    """
    Sample financial metrics for testing valuation calculations.
    """
    return {
        "revenue": [168088000000, 198270000000, 211915000000],
        "eps_diluted": [8.05, 9.21, 9.72],
        "net_income": [61271000000, 72738000000, 72361000000],
        "years": [2021, 2022, 2023]
    }


# =============================================================================
# Helper Functions
# =============================================================================

@pytest.fixture
def create_test_company(db_session):
    """
    Factory fixture to create test companies in the database.
    """
    from app.db.models import Company
    
    def _create_company(cik="0000789019", ticker="MSFT", name="MICROSOFT CORPORATION"):
        company = Company(cik=cik, ticker=ticker, name=name)
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)
        return company
    
    return _create_company


@pytest.fixture
def create_test_filing(db_session):
    """
    Factory fixture to create test filings in the database.
    """
    from app.db.models import Filing
    from datetime import date
    
    def _create_filing(cik="0000789019", form="10-K", accession=None, period_end=None):
        if accession is None:
            accession = f"TEST-{cik}-{form}"
        if period_end is None:
            period_end = date(2023, 6, 30)
        
        filing = Filing(cik=cik, form=form, accession=accession, period_end=period_end)
        db_session.add(filing)
        db_session.commit()
        db_session.refresh(filing)
        return filing
    
    return _create_filing


@pytest.fixture(autouse=True)
def reset_db_state(db_session):
    """
    Automatically reset database state after each test.
    """
    yield
    # Rollback is handled by db_session fixture
    pass
