# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Common Investor is a financial analysis platform implementing Phil Town's Rule #1 investing methodology, augmented with Vitaliy Katsenelson's QVG (Quality-Valuation-Growth) qualitative framework. It analyzes public companies using the **Four Ms** (Meaning, Moat, Management, Margin of Safety), the **Big Five Numbers** (ROIC, Revenue Growth, EPS Growth, Owner Earnings, Debt Ratios), and multiple valuation methods (Sticker Price, MOS, Payback Time, Ten Cap). Data is sourced from SEC EDGAR XBRL filings.

Design docs: `docs/spec-ideas/` contains the full spec evolution from business idea through implementation.

## Domain Knowledge

### Rule #1 Investing Formulas (implemented in code)

- **ROIC** = NOPAT / Invested Capital, where NOPAT = EBIT * (1 - tax_rate), Invested Capital = Equity + Debt - Cash. Target: >=15% sustained. (`metrics/compute.py:roic_series`)
- **CAGR** = (last/first)^(1/years) - 1. Computed for 1y/3y/5y/10y windows on revenue and EPS. (`metrics/compute.py:cagr`, `_calculate_window_cagr`)
- **Owner Earnings** = CFO - CapEx (Buffett's preferred metric). (`metrics/compute.py:owner_earnings_series`)
- **Sticker Price** = (EPS0 * (1+g)^10 * terminal_PE) / (1+r)^10. Growth capped at 50%, PE = min(pe_cap, max(5, 2*g*100)). (`valuation/core.py:sticker_and_mos`)
- **MOS Price** = Sticker * (1 - mos_pct). Default 50% margin of safety.
- **Payback Time** = years for cumulative growing owner earnings to recoup purchase price. Target: <=8 years. (`valuation/core.py:payback_time`)
- **Ten Cap** = Owner Earnings per share / 0.10. (`valuation/core.py:ten_cap_price`)
- **Interest Coverage** = EBIT / Interest Expense. >5x comfortable, 2-5x cautious, <2x risky. (`metrics/compute.py:coverage_series`)

### Four Ms Scoring (implemented in `nlp/fourm/service.py`)

- **Moat score** (0-1): weighted from ROIC avg, ROIC stability (1/(1+sd)), margin stability, pricing power (0-1 from gross margin level/stability/trend), ROIC persistence (0-5).
- **Management score** (0-1): from reinvestment ratio (CapEx/CFO, sweet spot 0.3-0.7) and payout ratio ((buybacks+dividends)/CFO, sweet spot 0-0.6).
- **Balance Sheet Resilience** (0-5): weighted from interest coverage (40%), debt/equity (30%), net debt trend (30%).
- **MOS Recommendation** (0.3-0.7): higher MOS when growth is low, moat/management scores are weak, or balance sheet is poor.

### Qualitative Analysis Agent (experimental, in `nlp/research_agent/`)

An LLM-based research agent that produces structured JSON outputs: `business_profile.json`, `unit_economics.json`, `industry.json`, `moat.json`, `management.json`, `peers.json`, `risks.json`, `thesis.json`. Follows the playbook in `docs/spec-ideas/qualitative-analysis-v2.md`. The agent consumes quantitative data via the `/agent-bundle` endpoint and enriches it with qualitative research.

### Phase Status

The project follows a phased release plan from `docs/spec-ideas/functional-spec-v4.md`:
- **Phase 1 (current)**: Laptop monolith - search, ingest, metrics, valuation, Four Ms, exports, experimental qualitative agent.
  - **Phase 1A** (PRs #5, #6): Data correctness bugs fixed + XBRL tag enrichment. ✅ Complete.
  - **Phase 1B** (PR #7): SIC industry classification from SEC submissions endpoint. ✅ Complete.
  - **Phase 1C** (PR #7): Enriched metrics (operating margin, FCF margin, cash conversion, ROE, fiscal year end). ✅ Complete.
  - **Quantitative foundation**: Ready for qualitative agent. See `docs/QUANTITATIVE_GAP_ANALYSIS_V2.md`.
- **Phase 2 (planned)**: K8s deployment, quarterly (10-Q) data, TTM metrics, SBC/goodwill ingestion, metric suppression per industry, segment/geography parsing, transcripts, industry datasets, proxy ingestion, DCF, sensitivity analysis, industry-specific valuation plugins.
- **Phase 3 (planned)**: Public API, mobile, community features.

Not yet implemented: quarterly data (10-Q), TTM calculations, SBC ingestion, goodwill tracking, full XBRL processing (Arelle), user auth, DCF, technical signals (MA/MACD), PDF export, industry-specific valuation plugins (SaaS, financials, REIT, energy), peer resolution, risk classifier ML, segment/geography parsing, currency detection.

## Architecture

**Modular monolith** with three main layers:

- **Backend** (`backend/`): Python 3.11, FastAPI. All API routes in `app/api/v1/routes.py`. Database access uses raw SQL via `execute()` in `app/db/session.py` (not ORM queries), though SQLAlchemy models in `app/db/models.py` define schema and enable test setup.
- **Frontend** (`ui/`): Next.js 13 + React 18 + TypeScript. Components in `ui/components/`, pages use App Router in `ui/app/`.
- **Workers**: Celery tasks (`app/workers/tasks.py`) with Redis broker. Beat scheduler runs price snapshots (6h) and alert evaluation (24h).

**Data flow**: SEC EDGAR API -> `app/ingest/sec.py` (CompanyFacts JSON + Submissions JSON for SIC/fiscal year, XBRL tag mapping with ordered fallback lists) -> PostgreSQL tables (company with SIC/industry, filing, statement_is/bs/cf) -> `app/metrics/compute.py` (CAGR, ROIC, operating margin, FCF margin, cash conversion, ROE, coverage, owner earnings, volatility, share dilution) -> `app/valuation/` (sticker/MOS/payback/ten cap) -> `app/nlp/fourm/service.py` (moat/management/balance sheet/MOS recommendation scores). Industry classification via `app/core/industry.py` (SIC-to-category mapping + agent guidance notes).

**Key design decisions**:
- `execute(sql, **params)` in `app/db/session.py` auto-manages transactions via `engine.begin()` and returns a `ResultWrapper` that pre-fetches rows to avoid SQLite cursor issues. Tests inject via `set_test_session()` thread-local.
- XBRL tag mapping in `app/ingest/sec.py` uses `IS_TAGS`, `BS_TAGS`, `CF_TAGS` dicts where each DB column maps to an ordered list of XBRL tag fallbacks (e.g., revenue tries 7 different tags). `_pick_first_units()` finds the first matching tag in CompanyFacts.
- `STATEMENT_SCHEMAS` in `ingest/sec.py` defines table/field/unit mappings for generic `_insert_statement()` to avoid per-statement-type code duplication.
- All metrics functions operate on CIK strings and return dicts/lists, not ORM objects.
- The `app/nlp/research_agent/experimental/` directory is isolated with its own `requirements-research-agent.txt` (LangChain, OpenAI, etc.) to avoid dependency conflicts with core backend.

## Commands

### Docker (primary development method)
```bash
cp .env.example .env                          # First-time setup
docker compose up -d --build                  # Start all services
docker compose exec api pytest -v             # Run backend tests
docker compose exec ui npm run test:unit      # Run frontend tests
docker compose logs api                       # View API logs
docker compose exec api bash                  # Shell into API container
```

### Backend (from `backend/` directory)
```bash
make test                    # All tests
make test-unit               # Unit tests only (pytest -v -m unit)
make test-integration        # Integration tests (pytest -v -m integration)
make test-fast               # Exclude slow tests (pytest -v -m "not slow")
make test-coverage           # Tests with HTML coverage report
make test-api                # API endpoint tests only
make lint                    # flake8 + pylint
make format                  # black + isort
make dev                     # uvicorn with --reload on port 8080
```

Single test: `pytest tests/test_valuation_core_comprehensive.py -v -k "test_name"`

### Frontend (from `ui/` directory)
```bash
npm run dev                  # Next.js dev server on port 3000
npm run test:unit            # Vitest with jsdom
npm run build                # Production build
```

### Database
```bash
make db-migrate              # alembic upgrade head
make db-rollback             # alembic downgrade -1
```

## Test Infrastructure

- **Backend tests** use SQLite in-memory (`conftest.py` sets `DATABASE_URL=sqlite:///:memory:` and `TESTING=1` before imports). The `db_session` fixture injects via `set_test_session()` so all `execute()` calls route to test DB. Factory fixtures: `create_test_company`, `create_test_filing`.
- **Test markers**: `unit`, `integration`, `e2e`, `slow`, `celery`, `db`, `api`, `migration`, `mock_sec`, `real_sec`
- **CI coverage threshold**: 90% combined (unit tests alone ~83%). Frontend: 97%.
- **Mock SEC data**: `conftest.py` provides `mock_sec_company_facts` and `mock_httpx_client` fixtures with realistic MSFT data (2021-2023) covering all IS/BS/CF fields.

## Key API Endpoints

All under `/api/v1/`:
- `POST /company/{ticker}/ingest` - Queue SEC data ingestion (Celery background task)
- `GET /company/{ticker}` - Company summary + latest income statement
- `GET /company/{ticker}/metrics` - Growth CAGRs (1y/3y/5y/10y), ROIC avg, debt/equity, FCF growth, revenue volatility, ROIC persistence
- `GET /company/{ticker}/timeseries` - All time series (IS, owner earnings, ROIC, coverage, gross margin, net debt, share count)
- `GET /company/{ticker}/fourm` - Four Ms analysis (moat, management, balance sheet resilience, MOS recommendation)
- `POST /company/{ticker}/valuation` - Sticker price, MOS, payback time, ten cap (accepts mos_pct, g, pe_cap, discount overrides)
- `GET /company/{ticker}/quality-scores` - Gross margin trends, share dilution, ROIC persistence, net debt, extended growth
- `GET /company/{ticker}/agent-bundle` - All quantitative data aggregated for qualitative agent consumption
- `POST /company/{ticker}/fourm/meaning/refresh` - Extract Item 1 business description from latest 10-K
- `GET /company/{ticker}/export/metrics.csv` / `export/valuation.json` - Data exports

## Environment Variables

Required in `.env`:
- `SEC_USER_AGENT` - Must be set for SEC EDGAR API compliance (e.g., `"CommonInvestor/1.0 your-email@example.com"`)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - Database credentials (defaults: ci/ci_pass/ci_db)
- `AUTO_SEED` - Set to `false` to skip auto-seeding on startup

## Services (docker-compose)

| Service   | Port | Purpose                        |
|-----------|------|--------------------------------|
| api       | 8080 | FastAPI backend                |
| ui        | 3000 | Next.js frontend               |
| postgres  | 5432 | PostgreSQL with pgvector       |
| redis     | 6379 | Celery broker + result backend |
| worker    | -    | Celery worker                  |
| scheduler | -    | Celery beat scheduler          |

## Spec Documents Reference

Located in `docs/spec-ideas/`:
- `summary-rule1*.md` - Phil Town's Rule #1 methodology (Four Ms, Big Five, valuation formulas, worked examples)
- `functional-spec*.md` - Product spec evolution (v1-v5): personas, features, data model, acceptance criteria, release phases, K8s readiness, industry plugins, agent-ready data plan
- `qualitative-analysis-v1.md` - Katsenelson's QVG framework (quality, valuation, growth traits)
- `qualitative-analysis-v2.md` - Agent-ready qualitative playbook with JSON schemas for structured outputs
- `technical-implementation.md` - Deep code analysis doc with architecture diagrams and implementation status
- `AGENT-ITERATION-PLAN-V1.md` - LLM research agent development plan (4 phases: experiment, Docker, UI, K8s)
