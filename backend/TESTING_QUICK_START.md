# Testing Quick Start Guide

**TL;DR**: How to run tests right now.

---

## Prerequisites

```bash
cd backend/
pip install -r requirements.txt
```

---

## Running Tests

### 1. Unit Tests (Fast - Recommended)

Tests individual functions in isolation:

```bash
cd backend/

# Using Make (easiest)
make test-unit

# Using pytest directly
PYTHONPATH=. pytest -m unit -v --no-cov

# With coverage
PYTHONPATH=. pytest -m unit --cov=app --cov-report=html
open htmlcov/index.html
```

**Expected**: Fast execution (< 5 seconds)

### 2. Integration Tests

Tests component interactions:

```bash
cd backend/

# Using Make
make test-integration

# Using pytest
PYTHONPATH=. pytest -m integration -v --no-cov
```

**Expected**: Medium speed (10-30 seconds)

### 3. End-to-End Tests

Tests complete workflows:

```bash
cd backend/

# Using Make
make test-e2e

# Using pytest
PYTHONPATH=. pytest -m e2e -v --no-cov
```

**Expected**: Slower (30-60 seconds)

### 4. All Tests

```bash
cd backend/

# Run everything (no coverage to speed up)
PYTHONPATH=. pytest tests/ -v --no-cov

# With full coverage report
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html
```

---

## Currently Passing Tests

These tests are verified working:

```bash
cd backend/

# Valuation tests (4 tests)
PYTHONPATH=. pytest tests/test_valuation_metrics_math.py -v

# Metrics tests (~15 tests)
PYTHONPATH=. pytest tests/test_metrics_series.py -v

# Ingestion tests (9 tests)
PYTHONPATH=. pytest tests/test_ingest_sec.py::TestFetchJson -v
PYTHONPATH=. pytest tests/test_ingest_sec.py::TestTickerMap -v

# Run all passing tests together
PYTHONPATH=. pytest \
  tests/test_valuation_metrics_math.py \
  tests/test_metrics_series.py \
  tests/test_ingest_sec.py::TestFetchJson \
  tests/test_ingest_sec.py::TestTickerMap \
  -v --no-cov
```

**Expected**: ~24 tests PASS

---

## Makefile Commands

```bash
cd backend/

# List all commands
make help

# Common commands
make test                  # Run all tests
make test-unit             # Run unit tests only
make test-integration      # Run integration tests
make test-e2e              # Run E2E tests
make test-fast             # Run fast tests (exclude slow)
make test-coverage         # Generate HTML coverage report
make test-watch            # Auto-run on file changes
make clean                 # Clean test artifacts
```

---

## Test Organization

Tests are organized by markers:

| Marker | Purpose | Speed | Command |
|--------|---------|-------|---------|
| `unit` | Individual functions | Fast (ms) | `pytest -m unit` |
| `integration` | Component interactions | Medium (s) | `pytest -m integration` |
| `e2e` | Complete workflows | Slow (s) | `pytest -m e2e` |
| `slow` | Tests > 1 second | Slow | `pytest -m slow` |
| `db` | Requires database | Medium | `pytest -m db` |
| `api` | API endpoint tests | Fast | `pytest -m api` |
| `celery` | Worker tests | Medium | `pytest -m celery` |

---

## Common Use Cases

### During Development

```bash
# Watch mode - auto-run on changes
cd backend/
make test-watch

# Or specific file
ptw -- tests/test_valuation_metrics_math.py -v
```

### Before Committing

```bash
cd backend/

# Run fast tests
make test-fast

# If all pass, run full suite
make test
```

### Debugging Failed Tests

```bash
cd backend/

# Run with verbose output and stop on first failure
PYTHONPATH=. pytest tests/ -vvs -x

# Run specific test
PYTHONPATH=. pytest tests/test_ingest_sec.py::TestFetchJson::test_fetch_json_success -vvs

# Enter debugger on failure
PYTHONPATH=. pytest tests/ --pdb
```

---

## Troubleshooting

### Import Errors

```bash
# Make sure PYTHONPATH is set
export PYTHONPATH=.

# Or use python -m
python -m pytest tests/
```

### Database Errors

Tests use SQLite in-memory database. No setup needed.

### "Coverage failure: total less than 80%"

This is expected when running partial tests. Use `--no-cov` to skip coverage:

```bash
PYTHONPATH=. pytest tests/ --no-cov
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

File: `.github/workflows/backend-tests.yml`

**Triggers**:
- Every push to `main` branch
- Every pull request to `main`
- Only when backend files change

**What it runs**:
1. Linting (flake8)
2. Database migrations
3. Unit tests (with coverage)
4. Integration tests
5. End-to-end tests
6. Security scan

**How to check**:
1. Push code or create PR
2. Go to GitHub repo → Actions tab
3. See test results

### Local CI Simulation

```bash
cd backend/

# Run the same tests as CI
PYTHONPATH=. pytest tests/ \
  -v \
  -m "unit" \
  --cov=app \
  --cov-report=term-missing \
  --cov-fail-under=40
```

---

## Next Steps

1. **Run the passing tests** to verify setup:
   ```bash
   cd backend/
   PYTHONPATH=. pytest tests/test_valuation_metrics_math.py -v
   ```

2. **Add tests as you develop** using the patterns in existing tests

3. **Use watch mode** for fast feedback during development

4. **Check CI** on every PR to catch issues early

---

## Quick Reference

```bash
# Most common commands
cd backend/

make test-fast              # Quick validation
make test-coverage          # Full report
make test-watch             # Development mode

# Specific markers
pytest -m unit              # Fast tests
pytest -m "not slow"        # Exclude slow tests
pytest -m "unit and api"    # Combined markers

# Debugging
pytest -vvs -x              # Verbose, stop on failure
pytest --pdb                # Enter debugger
pytest --lf                 # Run last failed

# Coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## More Information

- **Comprehensive Guide**: See `TEST_GUIDE.md`
- **Implementation Details**: See `TESTING_SUMMARY.md`
- **Current Status**: See `TEST_STATUS.md`
- **Test Directory**: See `tests/README.md`

---

**Ready to test!** Start with `make test-fast` to validate your setup.
