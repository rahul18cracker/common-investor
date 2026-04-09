# Engineering Foundations Plan

> **Purpose:** Harden CI, test infrastructure, linting, type safety, Docker hygiene, and code quality foundations before starting Phase 2 qualitative agent work.
>
> **Branch:** `rahul/engineering-foundations`
> **Created:** April 8, 2026
> **Status:** Plan ready, implementation not started

---

## Table of Contents

1. [Context & Motivation](#1-context--motivation)
2. [Phase A: Test Integrity](#2-phase-a-test-integrity)
3. [Phase B: CI Pipeline Hardening](#3-phase-b-ci-pipeline-hardening)
4. [Phase C: Docker & Deployment Hygiene](#4-phase-c-docker--deployment-hygiene)
5. [Phase D: Code Quality Foundations](#5-phase-d-code-quality-foundations)
6. [Parallelism Strategy (Worktrees)](#6-parallelism-strategy-worktrees)
7. [Claude Skills, Workflows & Memory Updates](#7-claude-skills-workflows--memory-updates)
8. [Verification Checklist](#8-verification-checklist)

---

## 1. Context & Motivation

### What triggered this

After merging PR #7 (Phase 1B+1C), a deep audit of CI, tests, linting, Docker, and code patterns revealed that the engineering foundations have gaps that would compound in Phase 2. CI passes in ~1m38s but gives false confidence — 41% of tests lack tier markers, linting only checks syntax errors, type checking never runs, and Docker has no health checks.

### What we want to accomplish

1. **Fast feedback loop** — CI catches regressions and quality issues quickly
2. **Strong engineering practices** — linting, type checking, formatting enforced
3. **Clean and lean infrastructure** — Docker, compose, CI are minimal and reliable
4. **Reduce bulk** — consolidate duplicate tests, remove redundant CI workflows, split deps

### Key numbers (current state)

| Metric | Current | Target |
|--------|---------|--------|
| Tests with tier markers | 59% (515/710) | 100% |
| CI lint enforcement | Syntax only (E9,F63,F7,F82) | Full style + types |
| mypy in CI | Not running | Running, passing |
| black/isort in CI | Not running | Running, enforced |
| Docker health checks | 0 services | All 6 services |
| `print()` in app code | 13+ calls | 0 (use logging) |
| Config locations | 5 scattered files | 1 centralized module |
| Duplicate test file pairs | 7 pairs | 0 (consolidated) |

---

## 2. Phase A: Test Integrity

**Goal:** Every test has a tier marker. CI test steps accurately reflect what's being tested. No duplicate/confusing test files.

**Estimated time:** 2-3 hours

### A1: Add `pytestmark` to fully unmarked test files

These 7 files have ZERO pytest markers. Add file-level `pytestmark`:

| File | Tests | Correct Marker | Rationale |
|------|-------|----------------|-----------|
| `tests/test_api_routes_unit.py` | 33 | `pytestmark = pytest.mark.unit` | Name says unit, tests mock everything |
| `tests/test_cli_seed.py` | 31 | `pytestmark = pytest.mark.unit` | All mocked, no real DB |
| `tests/test_core_utils_errors.py` | 35 | `pytestmark = pytest.mark.unit` | Pure utility tests |
| `tests/test_metrics_series.py` | 4 | `pytestmark = pytest.mark.unit` | Pure math/computation |
| `tests/test_pricefeed_provider.py` | 13 | `pytestmark = pytest.mark.unit` | All mocked external calls |
| `tests/test_valuation_metrics_math.py` | 4 | `pytestmark = pytest.mark.unit` | Pure math |
| `tests/test_performance_benchmarks.py` | 10 | `pytestmark = [pytest.mark.unit, pytest.mark.slow]` | Benchmarks should run but be skippable |

**How:** Add `import pytest` (if missing) and `pytestmark = pytest.mark.unit` at the top of each file, below imports.

### A2: Fix partial markers in Phase 1B/1C test files

| File | Unmarked Classes | Fix |
|------|-----------------|-----|
| `tests/test_enriched_metrics.py` | `TestOperatingMarginSeries`, `TestFcfMarginSeries`, `TestCashConversionSeries`, `TestRoeSeries` (4 classes, ~13 tests) | Add `pytestmark = pytest.mark.unit` at file level. The 2 existing `@pytest.mark.integration` on `TestTimeseriesNewMetrics` and `TestNoRegressions` will override for those classes. |
| `tests/test_industry_classification.py` | `TestSicToCategory`, `TestRealWorldSicCodes`, `TestSicToMetricNotes`, `TestFiscalYearEndParsing` (4 classes, ~40 tests) | Same approach — file-level `pytestmark = pytest.mark.unit`, keep `@pytest.mark.integration` on `TestIngestionWithSIC` and `TestAgentBundleIndustry`. |

### A3: Add missing marker definitions to `pytest.ini`

Add to the `markers` section:

```ini
markers =
    ...existing...
    timeout: Tests with timeout constraints
    asyncio: Async test functions
```

### A4: Fix misnamed test files

| Current Name | Content | Action |
|-------------|---------|--------|
| `test_sec_item1_integration.py` | 11 tests, all `@pytest.mark.unit` | Rename to `test_sec_item1.py` |
| `test_cli_seed_integration.py` | 17 tests, all `@pytest.mark.unit` | Rename to `test_cli_seed_unit.py` |

### A5: Consolidate duplicate test file pairs

7 pairs of test files test overlapping functionality. Strategy: **keep the comprehensive file, audit the original for any unique tests, migrate unique ones, then delete the original.**

| Module | Keep (comprehensive) | Remove (original) | Unique tests to migrate |
|--------|---------------------|-------------------|------------------------|
| Alerts | `test_alerts_engine_comprehensive.py` (15) | `test_alerts_engine.py` (12) | Audit for unique cases |
| API Routes | `test_api_routes_comprehensive.py` (28) + `test_api_routes_unit.py` (33) | `test_api_routes.py` (50) | Audit — this file has mixed unit/integration markers |
| NLP FourM | `test_nlp_fourm_comprehensive.py` (20) + `test_nlp_fourm_service_comprehensive.py` (26) | `test_fourm_endpoints.py` (6) + `test_fourm_integration.py` (7) | Check for unique integration tests |
| Valuation | `test_valuation_core_comprehensive.py` (26) + `test_valuation_service_comprehensive.py` (16) | `test_valuation_metrics_math.py` (4) | 4 math tests → move to core_comprehensive |
| Pricefeed | `test_pricefeed_provider.py` (13) | `test_pricefeed_integration.py` (3) | 3 integration tests → keep if unique |
| CLI Seed | `test_cli_seed.py` (31) | `test_cli_seed_integration.py` (17) → renamed `test_cli_seed_unit.py` in A4 | Merge into one file |
| Metrics | `test_metrics_compute_comprehensive.py` (54) + `test_metrics_compute_integration.py` (38) | `test_metrics_series.py` (4) | 4 series tests → move to comprehensive |

**Important:** For each removal, do `git log --oneline -- <file>` to check history, then diff test names between original and comprehensive to find unique tests. Do NOT delete tests that aren't covered elsewhere.

### A6: Fix incorrect `@pytest.mark.asyncio` markers

File: `tests/test_core_utils_errors.py`

Remove `@pytest.mark.asyncio` from 4 non-async test functions (they use `AsyncMock` but aren't themselves async). Replace with `@pytest.mark.unit` (already covered by file-level marker from A1).

### A — Verification

After all A changes:

```bash
# All tests still pass
cd backend && pytest tests/ -v --tb=short

# Verify marker counts — should see ~0 unmarked
pytest --collect-only -q -m "unit" 2>&1 | tail -3          # Should be ~500+
pytest --collect-only -q -m "integration" 2>&1 | tail -3   # Should be ~150+
pytest --collect-only -q -m "e2e" 2>&1 | tail -3           # Should be ~14
pytest --collect-only -q 2>&1 | tail -3                     # Total should be ~680+ (after dedup)

# Verify no unmarked tests remain
# (unit + integration + e2e + slow) should equal total
```

---

## 3. Phase B: CI Pipeline Hardening

**Goal:** CI enforces formatting, linting, and type checking. No redundant workflows. Dev dependencies separated.

**Estimated time:** 3-4 hours

### B1: Create Python tooling config files

**`backend/pyproject.toml`** (new file):

```toml
[tool.black]
line-length = 120
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 120

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
check_untyped_defs = true
disallow_untyped_defs = false  # Start gradual — tighten later
exclude = ["tests/", "alembic/", "scripts/"]

[tool.flake8]
max-line-length = 120
extend-ignore = ["E203", "W503"]  # Conflicts with black
exclude = [".git", "__pycache__", "alembic/versions"]
```

**`backend/.flake8`** (new file — flake8 doesn't read pyproject.toml natively):

```ini
[flake8]
max-line-length = 120
extend-ignore = E203,W503
exclude = .git,__pycache__,alembic/versions
```

### B2: Split requirements

Create `backend/requirements-dev.txt`:

```
-r requirements.txt
# Testing
pytest
pytest-asyncio
pytest-cov
pytest-mock
pytest-celery
pytest-httpx
pytest-docker-tools
faker
freezegun
# Linting & formatting
black
isort
flake8
mypy
# Pre-commit
pre-commit
```

Remove test/lint packages from `backend/requirements.txt` (keep only prod deps):

```
fastapi
uvicorn[standard]
pydantic
sqlalchemy
psycopg2-binary
alembic
celery
redis
httpx
python-dotenv
loguru
beautifulsoup4
lxml
yfinance
pandas
```

### B3: Update CI workflow

**`.github/workflows/ci.yml`** changes:

1. **Install step**: Change to `pip install -r requirements-dev.txt`

2. **Add formatting check step** (after lint, before tests):
```yaml
- name: Check formatting (black + isort)
  working-directory: backend
  run: |
    black --check app/ tests/
    isort --check-only app/ tests/
```

3. **Fix flake8 step** — remove `exit-zero`, use real enforcement:
```yaml
- name: Lint with flake8
  working-directory: backend
  run: |
    flake8 app/ tests/
```

4. **Add mypy step**:
```yaml
- name: Type check with mypy
  working-directory: backend
  run: |
    mypy app/ --config-file pyproject.toml
```

5. **Remove `frontend-tests` job from ci.yml** (lines 158-183) — it's redundant with `frontend-tests.yml`

6. **Update `all-tests-pass` gate** to only require `test` (backend) job — frontend is gated by its own workflow

### B4: Update Dockerfile to use split requirements

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

(No longer installs test deps in production image)

### B5: Create pre-commit config

**`.pre-commit-config.yaml`** (new file at repo root):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        args: [--line-length=120]
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black, --line-length=120]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports, --check-untyped-defs]
        additional_dependencies: [pydantic, fastapi, sqlalchemy]
        files: ^backend/app/
```

### B6: Run black/isort on existing code

This is a one-time formatting pass. Commit separately so git blame stays useful:

```bash
cd backend
black app/ tests/ --line-length 120
isort app/ tests/ --profile black --line-length 120
git add -A && git commit -m "style: auto-format with black + isort (one-time)"
```

### B7: Fix flake8 violations

After enabling real flake8 enforcement, fix any violations:

```bash
cd backend
flake8 app/ tests/ --statistics
# Fix reported issues
```

### B8: Fix mypy errors

Run mypy and fix errors. Start with `--ignore-missing-imports` and `disallow_untyped_defs = false` to be gradual:

```bash
cd backend
mypy app/ --config-file pyproject.toml
# Fix reported type errors (likely 20-50 issues)
```

### B — Verification

```bash
# All quality checks pass
cd backend
black --check app/ tests/
isort --check-only app/ tests/
flake8 app/ tests/
mypy app/ --config-file pyproject.toml

# All tests still pass
pytest tests/ -v --tb=short

# Pre-commit works
cd .. && pre-commit run --all-files
```

---

## 4. Phase C: Docker & Deployment Hygiene

**Goal:** Docker builds are fast, containers are reliable, startup is robust.

**Estimated time:** 2 hours

### C1: Add `.dockerignore` files

**`backend/.dockerignore`** (new):

```
.git
.github
__pycache__
.pytest_cache
.coverage
htmlcov
coverage.xml
*.pyc
*.pyo
.env
.env.*
tests/
docs/
*.md
.mypy_cache
.ruff_cache
scripts/workflows/baseline.json
```

**`ui/.dockerignore`** (new):

```
node_modules
.next
coverage
dist
build
.git
.github
*.md
.env.local
```

### C2: Add health checks to `docker-compose.yml`

Add to each service:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ci"]
    interval: 10s
    timeout: 5s
    retries: 5

redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5

api:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
    interval: 15s
    timeout: 5s
    retries: 3

worker:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy

scheduler:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy

ui:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000"]
    interval: 15s
    timeout: 5s
    retries: 3
```

### C3: Add restart policies

Add to all services:

```yaml
restart: unless-stopped
```

### C4: Fix UI Dockerfile

Replace:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install || true
COPY . .
EXPOSE 3000
CMD npm install && npm run dev
```

With:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

### C5: Fix `startup.sh` — replace `sleep 10` with health poll

Replace the hardcoded sleep:

```bash
# OLD:
echo "Waiting for database to be ready..."
sleep 10

# NEW:
echo "Waiting for database to be ready..."
until pg_isready -h postgres -p 5432 -U ci 2>/dev/null; do
  echo "  Database not ready, retrying in 2s..."
  sleep 2
done
echo "Database is ready."
```

### C6: Fix scheduler `depends_on`

Add `postgres` to scheduler's `depends_on` list (currently only has `redis`).

### C7: Clean backend Dockerfile

Remove `build-essential` after pip install to reduce image size:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
```

### C — Verification

```bash
# Rebuild and verify
docker compose down
docker compose up -d --build

# Check health checks are working
docker compose ps   # All should show "healthy" after ~30s

# Verify API responds
curl http://localhost:8080/api/v1/health

# Verify UI responds
curl -s http://localhost:3000 | head -5

# Ingest a ticker to verify full pipeline
curl -X POST http://localhost:8080/api/v1/company/MSFT/ingest
# Wait for worker, then:
curl http://localhost:8080/api/v1/company/MSFT/agent-bundle | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', list(d.keys()))"
```

---

## 5. Phase D: Code Quality Foundations

**Goal:** Centralize config, implement proper logging, fix silent error handling, add response models.

**Estimated time:** 4-5 hours

### D1: Centralize configuration — `app/core/config.py`

Create a Pydantic `BaseSettings` class:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://ci:ci_pass@postgres:5432/ci_db"
    redis_url: str = "redis://redis:6379/0"
    sec_user_agent: str = "CommonInvestor/1.0 dev@example.com"
    testing: bool = False
    auto_seed: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

Then replace all `os.getenv()` calls:

| File | Current | Replace With |
|------|---------|-------------|
| `app/db/session.py:9` | `os.getenv("DATABASE_URL", ...)` | `settings.database_url` |
| `app/db/session.py:12` | `os.getenv("TESTING", "0") == "1"` | `settings.testing` |
| `app/workers/celery_app.py:4` | `os.getenv("REDIS_URL", ...)` | `settings.redis_url` |
| `app/ingest/sec.py:10` | `os.getenv("SEC_USER_AGENT", ...)` | `settings.sec_user_agent` |
| `app/nlp/fourm/sec_item1.py:5` | `os.getenv("SEC_USER_AGENT", ...)` | `settings.sec_user_agent` |

**Note:** Add `pydantic-settings` to `requirements.txt`.

### D2: Implement proper logging — `app/core/logging.py`

Replace the empty stub with real config:

```python
import logging
import sys

def init_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

Then replace all `print()` calls:

| File | Lines | Change |
|------|-------|--------|
| `app/workers/tasks.py` | 11 | `log.info("Ingested %s: %s", ticker, res)` |
| `app/cli/seed.py` | 51, 76-103, 144-157 | Replace 13 `print()` with `log.info()` / `log.error()` |

### D3: Fix silent exception handlers

| File | Line | Current | Fix |
|------|------|---------|-----|
| `app/alerts/engine.py` | 29 | `except Exception: continue` | `except (ValueError, KeyError) as e: log.warning("Valuation failed for alert %s: %s", rule_id, e); continue` |
| `app/pricefeed/provider.py` | 8 | `except Exception: return None` | `except (httpx.HTTPError, KeyError, ValueError) as e: log.warning("Price fetch failed for %s: %s", ticker, e); return None` |
| `app/metrics/compute.py` | 28 | `except Exception: return None` | `except (ZeroDivisionError, ValueError): return None` (this one is OK to be quiet — it's a math guard) |

### D4: Add Pydantic response models for key endpoints

Add to `app/api/v1/routes.py`:

```python
class CompanySummary(BaseModel):
    company: dict
    latest_is: dict | None

class MetricsResponse(BaseModel):
    cik: str
    growths: dict
    growths_extended: dict
    roic_avg_10y: float | None
    debt_to_equity: float | None
    fcf_growth: float | None
    revenue_volatility: float | None
    roic_persistence_score: int | None
    latest_gross_margin: float | None
```

Apply as `response_model` on route decorators. Start with the most-used endpoints (`/metrics`, `/fourm`, `/agent-bundle`).

### D5: Enable TypeScript strict mode (frontend)

In `ui/tsconfig.json`, change:

```json
"strict": true
```

Then fix resulting `any` type errors in components. Key files to update:
- `ui/components/CompanyDashboard.tsx` — replace `useState<any>` with proper types
- Fix `catch (e: any)` patterns to `catch (e: unknown)`

### D — Verification

```bash
# Config works
cd backend && python -c "from app.core.config import settings; print(settings.database_url)"

# Logging works
python -c "from app.core.logging import init_logging; init_logging(); import logging; logging.getLogger('test').info('OK')"

# All tests still pass
pytest tests/ -v --tb=short

# mypy still passes (D1 changes type patterns)
mypy app/ --config-file pyproject.toml

# Frontend builds with strict mode
cd ../ui && npm run build
```

---

## 6. Parallelism Strategy (Worktrees)

Phases A+B are **independent from** C+D at the file level. We can use git worktrees to work on them in parallel.

### Recommended parallel split

```
Worktree 1 (main branch): Phase A + B
  - Tests, CI, linting config, formatting
  - Files: tests/*, .github/*, backend/pyproject.toml, .flake8, .pre-commit-config.yaml,
    requirements*.txt, pytest.ini

Worktree 2 (separate branch): Phase C + D
  - Docker, compose, app code quality
  - Files: backend/Dockerfile, ui/Dockerfile, docker-compose.yml, backend/scripts/startup.sh,
    .dockerignore, app/core/config.py, app/core/logging.py, app/api/v1/routes.py,
    app/alerts/engine.py, app/pricefeed/provider.py, app/workers/tasks.py, app/cli/seed.py,
    ui/tsconfig.json, ui/components/*
```

### Setup commands

```bash
# From repo root
# Worktree 1: Phase A+B (test + CI)
git worktree add ../common-investor-ab rahul/engineering-foundations-ab -b rahul/engineering-foundations-ab

# Worktree 2: Phase C+D (Docker + code quality)
git worktree add ../common-investor-cd rahul/engineering-foundations-cd -b rahul/engineering-foundations-cd

# Work in parallel with separate Claude instances
# After both complete, merge into rahul/engineering-foundations:
git checkout rahul/engineering-foundations
git merge rahul/engineering-foundations-ab
git merge rahul/engineering-foundations-cd
```

### Conflict risk

| File | Used In | Conflict Risk |
|------|---------|--------------|
| `requirements.txt` | B2 (split) + D1 (add pydantic-settings) | LOW — merge both changes |
| `backend/Dockerfile` | B4 (use prod requirements) + C7 (clean build-essential) | LOW — both modify same file but different lines |
| `app/api/v1/routes.py` | D4 (add response models) | NONE — only Phase D touches this |
| `.github/workflows/ci.yml` | B3 only | NONE |

### Alternative: Sequential with fast commits

If parallelism feels risky, do A → B → C → D sequentially on one branch with a commit after each phase. This is simpler and avoids merge conflicts entirely.

---

## 7. Claude Skills, Workflows & Memory Updates

### New Claude Commands to Create

#### `.claude/commands/lint-check.md`

```markdown
# Lint Check

Run all code quality checks and report status.

## Instructions

1. **Run checks**:
   ```
   cd backend
   black --check app/ tests/ 2>&1 | tail -5
   isort --check-only app/ tests/ 2>&1 | tail -5
   flake8 app/ tests/ 2>&1 | tail -20
   mypy app/ --config-file pyproject.toml 2>&1 | tail -20
   ```

2. **Report**:
   - Which checks pass/fail
   - Count of violations per tool
   - Suggested fix for most common violation type

3. **Auto-fix option**: If the user says "fix", run:
   ```
   black app/ tests/
   isort app/ tests/
   ```
   Then re-run flake8 and mypy to report remaining issues.

## Arguments
- `$ARGUMENTS` — optional: "fix" to auto-format, or specific path to check
```

#### `.claude/commands/test-audit.md`

```markdown
# Test Audit

Audit test marker coverage and report gaps.

## Instructions

1. **Collect marker stats**:
   ```
   cd backend
   pytest --collect-only -q -m "unit" 2>&1 | tail -3
   pytest --collect-only -q -m "integration" 2>&1 | tail -3
   pytest --collect-only -q -m "e2e" 2>&1 | tail -3
   pytest --collect-only -q 2>&1 | tail -3
   ```

2. **Calculate unmarked**: Total - (unit + integration + e2e)

3. **If unmarked > 0**: Find which files have unmarked tests:
   ```
   for f in tests/test_*.py; do
     grep -L "pytestmark\|pytest.mark.unit\|pytest.mark.integration\|pytest.mark.e2e" "$f"
   done
   ```

4. **Report**: Marker distribution table + list of files needing markers

## Arguments
- `$ARGUMENTS` — optional: specific test file to audit
```

#### `.claude/commands/docker-health.md`

```markdown
# Docker Health

Check Docker services health and verify full pipeline.

## Instructions

1. **Check services**: `docker compose ps`
2. **Verify health checks**: All services should show "healthy"
3. **Test API**: `curl -s http://localhost:8080/api/v1/health`
4. **Test UI**: `curl -s http://localhost:3000 | head -5`
5. **Report**: Service status table + any issues found

## Arguments
- `$ARGUMENTS` — optional: "restart" to rebuild, "logs <service>" to show logs
```

### Memory Updates

After implementation, update these memory files:

#### `.claude/memory/known_patterns.md` — Add section:

```markdown
## Engineering Foundations (Phase EF, April 2026)

- All tests require a tier marker (unit/integration/e2e) — enforced by CI
- black + isort formatting enforced (line-length=120, profile=black)
- mypy runs in CI with `--ignore-missing-imports` and `--check-untyped-defs`
- flake8 enforced (max-line-length=120, E203/W503 ignored for black compat)
- Config centralized in `app/core/config.py` via Pydantic BaseSettings
- Logging via Python `logging` module — no print() in app code
- Docker health checks on all services; `depends_on` uses `condition: service_healthy`
- Pre-commit hooks configured for local dev (.pre-commit-config.yaml)
```

#### Session memory (`MEMORY.md`) — Update project status:

```markdown
## Engineering Foundations (completed April 2026)
- Branch: `rahul/engineering-foundations`, PR #8
- Test markers: 100% coverage (was 59%)
- CI: black, isort, flake8, mypy all enforced
- Docker: health checks, restart policies, .dockerignore, lean Dockerfile
- Code: centralized config (Pydantic BaseSettings), proper logging, typed exceptions
- Claude commands: lint-check, test-audit, docker-health added
```

---

## 8. Verification Checklist

Run this after all phases are complete, before creating the PR:

### Tests
- [ ] `pytest tests/ -v --tb=short` — all pass
- [ ] `pytest --collect-only -q -m "unit"` — count matches expected
- [ ] `pytest --collect-only -q -m "integration"` — count matches expected
- [ ] No unmarked tests (unit + integration + e2e = total)
- [ ] No duplicate test files

### Code Quality
- [ ] `black --check app/ tests/` — passes
- [ ] `isort --check-only app/ tests/` — passes
- [ ] `flake8 app/ tests/` — passes
- [ ] `mypy app/ --config-file pyproject.toml` — passes
- [ ] `pre-commit run --all-files` — passes

### Docker
- [ ] `docker compose up -d --build` — all services start
- [ ] `docker compose ps` — all show "healthy"
- [ ] API health check responds
- [ ] Full ingest pipeline works (POST /ingest → worker processes → GET /agent-bundle returns data)

### CI
- [ ] Push to branch, CI passes
- [ ] Unit test step catches unit-marked tests
- [ ] Integration test step catches integration-marked tests
- [ ] Lint/format/type steps all run and pass
- [ ] Coverage threshold still met (90%)

### Claude Skills
- [ ] `/lint-check` command works
- [ ] `/test-audit` command works
- [ ] `/docker-health` command works
- [ ] Memory files updated

---

## Appendix: Files Changed Summary

### Phase A (~20 files)
- `tests/test_*.py` — add markers, rename, consolidate
- `pytest.ini` — add marker definitions

### Phase B (~10 files)
- `backend/pyproject.toml` (new)
- `backend/.flake8` (new)
- `backend/requirements.txt` (trim to prod)
- `backend/requirements-dev.txt` (new)
- `.github/workflows/ci.yml` (update)
- `.pre-commit-config.yaml` (new)
- `backend/Dockerfile` (use prod requirements)
- `app/**/*.py` — formatting pass (black/isort)

### Phase C (~8 files)
- `backend/.dockerignore` (new)
- `ui/.dockerignore` (new)
- `docker-compose.yml` (health checks, restart, depends_on)
- `ui/Dockerfile` (fix npm install)
- `backend/Dockerfile` (clean build-essential)
- `backend/scripts/startup.sh` (pg_isready)

### Phase D (~12 files)
- `app/core/config.py` (new)
- `app/core/logging.py` (implement)
- `app/db/session.py` (use settings)
- `app/workers/celery_app.py` (use settings)
- `app/ingest/sec.py` (use settings)
- `app/nlp/fourm/sec_item1.py` (use settings)
- `app/workers/tasks.py` (use logging)
- `app/cli/seed.py` (use logging)
- `app/alerts/engine.py` (fix exception)
- `app/pricefeed/provider.py` (fix exception)
- `app/api/v1/routes.py` (response models)
- `ui/tsconfig.json` (strict mode)

### Claude Infrastructure
- `.claude/commands/lint-check.md` (new)
- `.claude/commands/test-audit.md` (new)
- `.claude/commands/docker-health.md` (new)
- `.claude/memory/known_patterns.md` (update)
- Session `MEMORY.md` (update)
