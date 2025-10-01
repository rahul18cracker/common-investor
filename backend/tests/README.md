# Backend Tests

This directory contains the comprehensive test suite for the Common Investor backend.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_ingest_sec.py
```

## Test Files

| File | Purpose | Tests | Component |
|------|---------|-------|-----------|
| `conftest.py` | Shared fixtures & configuration | N/A | Infrastructure |
| `test_ingest_sec.py` | SEC EDGAR API integration | 82 | Data Ingestion |
| `test_workers_celery.py` | Celery task execution | 31 | Background Workers |
| `test_e2e_ingestion_pipeline.py` | Complete workflows | 18 | System Integration |
| `test_migrations.py` | Database migrations | 20 | Database |
| `test_api_routes.py` | REST API endpoints | 47 | API Layer |
| `test_metrics_series.py` | Financial metrics | 15 | Business Logic |
| `test_valuation_metrics_math.py` | Valuation calculations | 18 | Business Logic |
| `test_fourm_*.py` | Four Ms analysis | 12 | NLP/Analysis |

**Total: 225+ tests**

## Test Categories

Use pytest markers to run specific test categories:

```bash
# Fast unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"
```

### Available Markers

- `unit`: Fast, isolated unit tests
- `integration`: Component integration tests
- `e2e`: End-to-end workflow tests
- `slow`: Tests that take > 1 second
- `db`: Tests requiring database
- `api`: API endpoint tests
- `celery`: Celery worker tests
- `migration`: Database migration tests
- `mock_sec`: Tests with mocked SEC API

## Documentation

- **[TEST_GUIDE.md](../TEST_GUIDE.md)**: Comprehensive testing guide
  - What each test does
  - Which components are tested
  - How to run tests
  - Writing new tests
  - Troubleshooting

- **[TESTING_SUMMARY.md](../TESTING_SUMMARY.md)**: Implementation summary
  - Test coverage breakdown
  - Performance metrics
  - Best practices used
  - Maintenance guide

- **[Makefile](../Makefile)**: Command shortcuts
  - `make test`: Run all tests
  - `make test-coverage`: Generate coverage report
  - `make test-fast`: Run only fast tests

## Coverage

Current coverage: **83%** (Target: 80%+)

View detailed coverage:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Fixtures

Reusable test fixtures are defined in `conftest.py`:

### Database
- `test_engine`: SQLite in-memory engine
- `db_session`: Isolated database session
- `create_test_company`: Company factory
- `create_test_filing`: Filing factory

### API
- `client`: FastAPI test client
- `override_get_db`: Database dependency override

### Celery
- `celery_worker`: Eager mode worker
- `celery_config`: Test configuration

### Mocks
- `mock_httpx_client`: Mocked HTTP responses
- `mock_sec_company_tickers`: Sample ticker data
- `mock_sec_company_facts`: Sample financial data

## Writing Tests

### Example Unit Test

```python
@pytest.mark.unit
def test_function_name():
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Example Integration Test

```python
@pytest.mark.integration
@pytest.mark.db
def test_database_integration(db_session, create_test_company):
    """Test with database."""
    # Create test data
    company = create_test_company(ticker="TEST")
    
    # Test your function
    result = query_company(db_session, "TEST")
    
    # Verify
    assert result.id == company.id
```

### Example E2E Test

```python
@pytest.mark.e2e
@pytest.mark.api
def test_complete_workflow(client, celery_worker, mock_httpx_client):
    """Test complete system workflow."""
    # Trigger ingestion
    response = client.post("/api/v1/company/MSFT/ingest")
    assert response.status_code == 200
    
    # Verify data
    response = client.get("/api/v1/company/MSFT")
    assert response.status_code == 200
```

## Running in Docker

```bash
# Run tests in container
docker compose exec api pytest -v

# With coverage
docker compose exec api pytest --cov=app --cov-report=html

# Access container
docker compose exec api bash
```

## CI/CD

Tests are designed for CI/CD integration:

```bash
# CI test suite with coverage
pytest --cov=app --cov-report=xml --cov-fail-under=80

# Quick validation
pytest -m "unit and not slow"
```

## Troubleshooting

### Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH=.

# Or run with python -m
python -m pytest
```

### Database Errors

Tests use SQLite in-memory database. Ensure `conftest.py` is loaded and fixtures are used correctly.

### Slow Tests

```bash
# Identify slow tests
pytest --durations=10

# Run fast tests only
pytest -m "not slow"
```

## Performance

- Unit tests: < 5 seconds
- Integration tests: < 30 seconds
- E2E tests: < 60 seconds
- **Full suite: < 2 minutes**

## Support

For detailed information, see:
- [TEST_GUIDE.md](../TEST_GUIDE.md) - Complete testing guide
- [TESTING_SUMMARY.md](../TESTING_SUMMARY.md) - Implementation details
- [Makefile](../Makefile) - Command reference

---

**Status**: ✅ Production Ready  
**Coverage**: 83%  
**Tests**: 225+
