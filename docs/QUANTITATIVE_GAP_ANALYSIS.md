# Quantitative Analysis Gap Analysis & Implementation Plan

> **Purpose:** This document serves as the master tracking document for completing all quantitative analysis features required before the Qualitative Analysis Agent can function. Each phase maps to a GitHub branch and PR.

**Last Updated:** January 8, 2026
**Status:** ✅ Complete (All Critical & Moderate Gaps Closed)

> **NOTE (March 2026):** This document tracked Phase A-F metric *additions*. A deeper analysis
> revealed correctness bugs, industry-awareness gaps, and shallow test coverage that would cause
> the Qualitative Agent to produce wrong outputs for non-standard companies (banks, REITs,
> negative-equity companies). See **[QUANTITATIVE_GAP_ANALYSIS_V2.md](./QUANTITATIVE_GAP_ANALYSIS_V2.md)**
> for the comprehensive plan addressing data correctness, industry classification, quarterly data,
> and agent bundle v2.
>
> **UPDATE (April 2026):** V2 Phases 1D, 1A, 1B, 1C all complete (PRs #5, #6, #7). Bugs fixed,
> industry classification added, four new metrics (operating margin, FCF margin, cash conversion,
> ROE), fiscal year end. Quantitative foundation ready for qualitative agent. Quarterly data,
> TTM, SBC, goodwill deferred to Phase 2.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Requirements Overview](#2-requirements-overview)
3. [Current Implementation Status](#3-current-implementation-status)
4. [Gap Analysis](#4-gap-analysis)
5. [Data Flow Architecture](#5-data-flow-architecture)
6. [Implementation Phases](#6-implementation-phases)
7. [Branch & PR Strategy](#7-branch--pr-strategy)
8. [Testing Strategy](#8-testing-strategy)
9. [Qualitative Agent Readiness Checklist](#9-qualitative-agent-readiness-checklist)
10. [Code Quality Guidelines](#10-code-quality-guidelines)

---

## 1. Executive Summary

### Goal
Complete all quantitative (static number-crunching) features so the Qualitative Analysis Agent has reliable numeric data to produce its JSON outputs (`moat.json`, `unit_economics.json`, `peers.json`, `risks.json`, `thesis.json`).

### Current State
- **Valuation Engine:** ✅ Complete (Sticker, MOS, Payback, Ten Cap)
- **Big Five Metrics:** ✅ Complete (ROIC, CAGR, Owner Earnings, Gross Margin, Volatility)
- **Four Ms Scores:** ✅ Complete (Moat, Management, Balance Sheet Resilience, Pricing Power)
- **Data Ingestion:** ✅ Complete (IS/BS/CF with all required fields)

### Blocking Issues for Qualitative Agent
~~1. No gross margin series → cannot assess pricing power~~ ✅ RESOLVED  
~~2. No revenue volatility → cannot assess cyclicality~~ ✅ RESOLVED  
~~3. No ROIC persistence score (0-5) → cannot populate `peers.json`~~ ✅ RESOLVED  
~~4. Missing 1y/3y CAGR windows → incomplete trend analysis~~ ✅ RESOLVED  

**All blocking issues have been resolved. The Qualitative Analysis Agent now has all required quantitative data.**

---

## 2. Requirements Overview

### 2.1 Big Five Numbers (from `summary-rule1-v2.md`)

| Metric | Definition | Target | Spec Reference |
|--------|------------|--------|----------------|
| **ROIC** | NOPAT ÷ Invested Capital | ≥15% sustained | §3.1 |
| **Revenue Growth** | CAGR across 1/3/5/10-year windows | Consistency > speed | §3.2 |
| **EPS Growth** | Diluted EPS CAGR | Consistency matters | §3.3 |
| **Owner Earnings** | CFO − Maintenance CapEx | Cash drives value | §3.4 |
| **Debt & Solvency** | Net Debt, Debt/Equity, Coverage | Coverage >5× comfortable | §3.5 |

### 2.2 Valuation Methods (from `summary-rule1-v2.md`)

| Method | Formula | Target |
|--------|---------|--------|
| **Sticker Price** | (EPS₀ × (1+g)¹⁰ × PE_future) ÷ (1+r)¹⁰ | Present value of 10-yr projection |
| **MOS Price** | Sticker × (1 − MOS%) | 50% buffer default |
| **Payback Time** | Years until cumulative OE ≥ purchase price | ≤7-8 years attractive |
| **Ten Cap** | Owner Earnings ÷ 0.10 | 10% yield threshold |

### 2.3 Qualitative Agent Data Dependencies (from `qualitative-analysis-v2.md`)

| Agent Output | Required Quantitative Data |
|--------------|---------------------------|
| `moat.json` | ROIC persistence, margin stability, ROIC volatility |
| `unit_economics.json` | Gross margin drivers, operating leverage, cash conversion |
| `peers.json` | Multi-year ROIC series, ROIC persistence score (0-5) |
| `risks.json` | Coverage ratio, debt/equity, margin trends |
| `thesis.json` | Composite quality score from moat/revenue/management |

---

## 3. Current Implementation Status

### 3.1 ✅ Fully Implemented

| Component | File | Functions/Features |
|-----------|------|-------------------|
| **DB Schema** | `backend/app/db/models.py` | StatementIS, StatementBS, StatementCF, MetricsYearly, ValuationScenario |
| **SEC Ingestion** | `backend/app/ingest/sec.py` | CompanyFacts API → IS/BS/CF tables |
| **CAGR Calculation** | `backend/app/metrics/compute.py` | `cagr()`, 5y/10y windows |
| **ROIC Series** | `backend/app/metrics/compute.py` | `roic_series()`, `roic_average()` |
| **Owner Earnings** | `backend/app/metrics/compute.py` | `owner_earnings_series()`, `latest_owner_earnings_ps()` |
| **Coverage Ratio** | `backend/app/metrics/compute.py` | `coverage_series()` |
| **Margin Stability** | `backend/app/metrics/compute.py` | `margin_stability()` (EBIT margin std dev) |
| **Debt/Equity** | `backend/app/metrics/compute.py` | `latest_debt_to_equity()` |
| **Sticker/MOS** | `backend/app/valuation/core.py` | `sticker_and_mos()` |
| **Ten Cap** | `backend/app/valuation/core.py` | `ten_cap_price()` |
| **Payback Time** | `backend/app/valuation/core.py` | `payback_time()` |
| **Moat Score** | `backend/app/nlp/fourm/service.py` | `compute_moat()` |
| **Management Score** | `backend/app/nlp/fourm/service.py` | `compute_management()` |
| **MOS Recommendation** | `backend/app/nlp/fourm/service.py` | `compute_margin_of_safety_recommendation()` |
| **API Endpoints** | `backend/app/api/v1/routes.py` | `/metrics`, `/timeseries`, `/valuation`, `/fourm` |

### 3.2 ✅ Now Implemented (Phase A-F Complete)

| Component | File | Function | Status |
|-----------|------|----------|--------|
| Gross margin series | `metrics/compute.py` | `gross_margin_series()` | ✅ |
| Revenue volatility | `metrics/compute.py` | `revenue_volatility()` | ✅ |
| ROIC persistence score (0-5) | `metrics/compute.py` | `roic_persistence_score()` | ✅ |
| 1y/3y CAGR windows | `metrics/compute.py` | `compute_growth_metrics_extended()` | ✅ |
| Net debt series | `metrics/compute.py` | `net_debt_series()` | ✅ |
| Share count trend | `metrics/compute.py` | `share_count_trend()` | ✅ |
| Balance sheet resilience | `nlp/fourm/service.py` | `compute_balance_sheet_resilience()` | ✅ |
| Pricing power indicator | `nlp/fourm/service.py` | `_compute_pricing_power()` | ✅ |

---

## 4. Gap Analysis

### 4.1 ✅ Critical Gaps - ALL CLOSED

| ID | Gap | Implementation | Commit | Status |
|----|-----|----------------|--------|--------|
| G1 | **Gross Margin Series** | `gross_margin_series(cik)` in `compute.py:408` | Phase B | ✅ |
| G2 | **Revenue Volatility** | `revenue_volatility(cik)` in `compute.py:442` | Phase B | ✅ |
| G3 | **ROIC Persistence Score** | `roic_persistence_score(cik)` in `compute.py:569` | Phase B | ✅ |
| G4 | **Gross Profit Ingestion** | `sec.py:46` + `models.py:35` | Phase A | ✅ |

### 4.2 ✅ Moderate Gaps - ALL CLOSED

| ID | Gap | Implementation | Commit | Status |
|----|-----|----------------|--------|--------|
| G5 | **1y/3y CAGR Windows** | `compute_growth_metrics_extended()` in `compute.py:468` | Phase B | ✅ |
| G6 | **Net Debt Series** | `net_debt_series(cik)` in `compute.py:504` | Phase B | ✅ |
| G7 | **FCF/OE CAGR** | `latest_owner_earnings_growth(cik)` in `compute.py:349` | Phase B | ✅ |
| G8 | **Balance Sheet Resilience Score** | `compute_balance_sheet_resilience(cik)` in `service.py:224` | Phase C | ✅ |

### 4.3 🟢 Minor Gaps (Nice to Have)

| ID | Gap | Implementation | Status |
|----|-----|----------------|--------|
| G9 | **Share Count Trend** | `share_count_trend(cik)` in `compute.py:533` | ✅ |
| G10 | **Maintenance vs Growth CapEx** | Not implemented (low priority) | 🟡 |
| G11 | **Working Capital Metrics** | Not implemented (low priority) | 🟡 |

**Note:** G10 and G11 are nice-to-have features that do NOT block the Qualitative Analysis Agent.

---

## 5. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SEC EDGAR (CompanyFacts API)                      │
│                    Primary data source for all financials            │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: DATA INGESTION (backend/app/ingest/sec.py)                │
│  ─────────────────────────────────────────────────────────────────  │
│  ✅ Income Statement: revenue, ebit, interest, taxes, net_income,   │
│                       eps_diluted, shares_diluted                   │
│  ✅ Balance Sheet: cash, debt, equity, assets, liabilities          │
│  ✅ Cash Flow: cfo, capex, buybacks, dividends, acquisitions        │
│  ✅ VERIFIED: gross_profit, cogs, sga, rnd, depreciation            │
│  ✅ All IS fields flowing through correctly                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2: METRICS COMPUTATION (backend/app/metrics/compute.py)      │
│  ─────────────────────────────────────────────────────────────────  │
│  ✅ ROIC: roic_series(), roic_average()                             │
│  ✅ Growth: compute_growth_metrics() [5y, 10y CAGR]                 │
│  ✅ Owner Earnings: owner_earnings_series()                         │
│  ✅ Coverage: coverage_series()                                     │
│  ✅ Margin Stability: margin_stability() [EBIT margin]              │
│  ✅ Debt/Equity: latest_debt_to_equity()                            │
│  ✅ ADD: gross_margin_series()                                      │
│  ✅ ADD: revenue_volatility()                                       │
│  ✅ ADD: roic_persistence_score()                                   │
│  ✅ ADD: 1y, 3y CAGR windows (compute_growth_metrics_extended)      │
│  ✅ ADD: net_debt_series()                                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3: VALUATION ENGINE (backend/app/valuation/)                 │
│  ─────────────────────────────────────────────────────────────────  │
│  ✅ Sticker Price: sticker_and_mos()                                │
│  ✅ MOS Price: included in sticker_and_mos()                        │
│  ✅ Ten Cap: ten_cap_price()                                        │
│  ✅ Payback Time: payback_time()                                    │
│  ✅ Scenario Service: run_default_scenario()                        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4: FOUR Ms ANALYSIS (backend/app/nlp/fourm/service.py)       │
│  ─────────────────────────────────────────────────────────────────  │
│  ✅ Moat Score: compute_moat() [ROIC avg/sd + margin stability]     │
│  ✅ Management Score: compute_management() [reinvest/payout]        │
│  ✅ MOS Recommendation: compute_margin_of_safety_recommendation()   │
│  ✅ ADD: Gross margin trajectory for pricing power                  │
│  ✅ ADD: ROIC persistence score (0-5) for peer comparison           │
│  ✅ ADD: Balance sheet resilience score                             │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 5: API ENDPOINTS (backend/app/api/v1/routes.py)              │
│  ─────────────────────────────────────────────────────────────────  │
│  ✅ GET /company/{ticker}/metrics                                   │
│  ✅ GET /company/{ticker}/timeseries                                │
│  ✅ POST /company/{ticker}/valuation                                │
│  ✅ GET /company/{ticker}/fourm                                     │
│  ✅ EXTEND: /timeseries to include gross margin                     │
│  ✅ EXTEND: /metrics to include new metrics                         │
│  ✅ ADD: /company/{ticker}/quality-scores                           │
│  ✅ ADD: /company/{ticker}/agent-bundle                             │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CONSUMER: QUALITATIVE ANALYSIS AGENT                               │
│  ─────────────────────────────────────────────────────────────────  │
│  Produces: business_profile.json, unit_economics.json, industry.json│
│            moat.json, management.json, peers.json, risks.json,      │
│            thesis.json                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Phases

### Phase A: Data Ingestion Verification ✅ COMPLETE
**Branch:** `feature/phase-a-ingestion-verification`  
**Status:** ✅ Merged  
**Actual Effort:** 3 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| A1 | Verify COGS/Gross Profit ingestion | `ingest/sec.py` | ✅ |
| A2 | Add SG&A to IS ingestion if missing | `ingest/sec.py` | ✅ |
| A3 | Add R&D to IS ingestion if missing | `ingest/sec.py` | ✅ |
| A4 | Add Depreciation to IS ingestion | `ingest/sec.py` | ✅ |

**Tests:**
- [x] Unit test: `test_ingest_gross_profit()` - verify gross_profit extraction
- [x] Unit test: `test_ingest_sga_rnd()` - verify SG&A and R&D extraction
- [x] Integration test: Ingest AAPL, verify all IS fields populated
- [x] Browser validation: Check `/company/AAPL` shows gross profit in response

---

### Phase B: Metrics Computation Extension ✅ COMPLETE
**Branch:** `feature/phase-b-metrics-extension`  
**Status:** ✅ Merged  
**Actual Effort:** 6 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| B1 | Add `gross_margin_series(cik)` | `metrics/compute.py` | ✅ |
| B2 | Add `revenue_volatility(cik)` | `metrics/compute.py` | ✅ |
| B3 | Add 1y/3y CAGR to `compute_growth_metrics()` | `metrics/compute.py` | ✅ |
| B4 | Add `net_debt_series(cik)` | `metrics/compute.py` | ✅ |
| B5 | Add `share_count_trend(cik)` | `metrics/compute.py` | ✅ |
| B6 | Add `roic_persistence_score(cik)` | `metrics/compute.py` | ✅ |

**Tests:**
- [x] Unit test: `test_gross_margin_series()` - verify calculation
- [x] Unit test: `test_revenue_volatility()` - verify std dev calculation
- [x] Unit test: `test_cagr_all_windows()` - verify 1y/3y/5y/10y
- [x] Unit test: `test_roic_persistence_score()` - verify 0-5 rating logic
- [x] Integration test: Full metrics for MSFT, compare to known values
- [x] Browser validation: `/company/MSFT/metrics` returns new fields

---

### Phase C: Four Ms Enhancement ✅ COMPLETE
**Branch:** `feature/phase-c-fourm-enhancement`  
**Status:** ✅ Merged  
**Actual Effort:** 4 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| C1 | Add gross margin trajectory to `compute_moat()` | `nlp/fourm/service.py` | ✅ |
| C2 | Add ROIC persistence score (0-5) | `nlp/fourm/service.py` | ✅ |
| C3 | Add `compute_balance_sheet_resilience()` | `nlp/fourm/service.py` | ✅ |
| C4 | Add pricing power indicator | `nlp/fourm/service.py` | ✅ |

**Tests:**
- [x] Unit test: `test_moat_with_gross_margin()` - verify new fields
- [x] Unit test: `test_roic_persistence_rating()` - verify 0-5 scale
- [x] Unit test: `test_balance_sheet_resilience()` - verify score calculation
- [x] Integration test: Full Four Ms for JNJ, verify all scores
- [x] Browser validation: `/company/JNJ/fourm` returns enhanced response

---

### Phase D: API Extension ✅ COMPLETE
**Branch:** `feature/phase-d-api-extension`  
**Status:** ✅ Merged  
**Actual Effort:** 3 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| D1 | Extend `/timeseries` with gross margin | `api/v1/routes.py` | ✅ |
| D2 | Extend `/metrics` with new metrics | `api/v1/routes.py` | ✅ |
| D3 | Add `/company/{ticker}/quality-scores` | `api/v1/routes.py` | ✅ |
| D4 | Add `/company/{ticker}/agent-bundle` | `api/v1/routes.py` | ✅ |

**Tests:**
- [x] Unit test: `test_timeseries_endpoint()` - verify new fields
- [x] Unit test: `test_quality_scores_endpoint()` - verify response schema
- [x] Integration test: Full API flow for GOOGL
- [x] Browser validation: All new endpoints return valid JSON
- [x] OpenAPI spec validation: Swagger docs updated

---

### Phase E: Frontend Integration ✅ COMPLETE
**Branch:** `feature/phase-e-frontend-integration`  
**Status:** ✅ Merged  
**Actual Effort:** 4 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| E1 | Display gross margin chart | `FourMsPanel.tsx` | ✅ |
| E2 | Display ROIC persistence badge | `FourMsPanel.tsx` | ✅ |
| E3 | Display balance sheet resilience card | `FourMsPanel.tsx` | ✅ |
| E4 | Add volatility indicator | `BigFivePanel.tsx` | ✅ |

**Tests:**
- [x] Component test: Gross margin chart renders
- [x] Component test: Balance sheet resilience card renders
- [x] Component test: ROIC persistence badge renders
- [x] Component test: Volatility indicator renders
- [x] Browser validation: Visual inspection of all new UI elements (WMT)

---

### Phase F: Code Quality & Refactoring ✅ COMPLETE
**Branch:** `feature/phase-f-code-quality`  
**Status:** ✅ Merged  
**Actual Effort:** 3 hours

| Task ID | Description | File | Status |
|---------|-------------|------|--------|
| F1 | Extract `_weighted_average()` helper | `nlp/fourm/service.py` | ✅ |
| F2 | Add type hints to all new functions | All modified files | ✅ |
| F3 | Add docstrings with examples | All modified files | ✅ |
| F4 | Reduce cyclomatic complexity | All modified files | ✅ |
| F5 | Add performance benchmarks | `tests/test_performance_benchmarks.py` | ✅ |

**Tests:**
- [x] Performance benchmarks: 10 tests for computation speed
- [x] All functions have docstrings
- [x] Type hints added to all new functions
- [x] DRY refactoring applied (weighted average helper)

---

## 7. Branch & PR Strategy

### Branch Naming Convention
```
feature/phase-{letter}-{short-description}
```

### PR Template
```markdown
## Phase {X}: {Title}

### Summary
Brief description of what this PR accomplishes.

### Related Gap IDs
- G1, G2, G3 (reference from Gap Analysis)

### Changes
- [ ] Backend: {files changed}
- [ ] Frontend: {files changed}
- [ ] Tests: {test files added/modified}

### Testing Checklist
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Browser validation complete
- [ ] No regression in existing features

### Code Quality
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Complexity acceptable
- [ ] No code duplication

### Screenshots/Recordings
{Attach browser validation evidence}

### Qualitative Agent Impact
After this PR, the agent can now:
- {capability 1}
- {capability 2}
```

### Merge Order
```
main
  └── feature/phase-a-ingestion-verification
        └── feature/phase-b-metrics-extension
              └── feature/phase-c-fourm-enhancement
                    └── feature/phase-d-api-extension
                          └── feature/phase-e-frontend-integration
                                └── feature/phase-f-code-quality
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Location:** `backend/tests/unit/`

| Test File | Coverage |
|-----------|----------|
| `test_metrics_compute.py` | All functions in `metrics/compute.py` |
| `test_valuation_core.py` | All functions in `valuation/core.py` |
| `test_fourm_service.py` | All functions in `nlp/fourm/service.py` |
| `test_ingest_sec.py` | All functions in `ingest/sec.py` |

**Run Command:**
```bash
cd backend
pytest tests/unit/ -v --cov=app --cov-report=html
```

### 8.2 Integration Tests

**Location:** `backend/tests/integration/`

| Test File | Coverage |
|-----------|----------|
| `test_full_ingest_flow.py` | Ticker → DB → Metrics → Valuation |
| `test_api_endpoints.py` | All API routes with real data |
| `test_fourm_pipeline.py` | Full Four Ms computation |

**Run Command:**
```bash
cd backend
pytest tests/integration/ -v --tb=short
```

### 8.3 Browser Validation Checklist

For each phase, manually verify in browser:

| Endpoint | Expected Behavior |
|----------|-------------------|
| `GET /api/v1/company/AAPL` | Returns company with latest IS data |
| `GET /api/v1/company/AAPL/metrics` | Returns all growth metrics |
| `GET /api/v1/company/AAPL/timeseries` | Returns multi-year series |
| `POST /api/v1/company/AAPL/valuation` | Returns Sticker, MOS, Ten Cap, Payback |
| `GET /api/v1/company/AAPL/fourm` | Returns Moat, Management, MOS recommendation |

### 8.4 Test Data Companies

Use these tickers for consistent testing:

| Ticker | Why |
|--------|-----|
| AAPL | Large cap, complete data, stable |
| MSFT | Large cap, complete data, stable |
| JNJ | Dividend aristocrat, stable margins |
| GOOGL | High growth, tech sector |
| BRK-B | Unique structure, tests edge cases |

---

## 9. Qualitative Agent Readiness Checklist

Track readiness for each agent output JSON:

| JSON Output | Required Quant Data | Phase A | Phase B | Phase C | Phase D | Ready |
|-------------|---------------------|---------|---------|---------|---------|-------|
| `business_profile.json` | Revenue segments (out of scope) | - | - | - | - | N/A |
| `unit_economics.json` | Gross margin, operating leverage | ✅ | ✅ | - | ✅ | ✅ |
| `industry.json` | Revenue volatility, cyclicality | - | ✅ | - | ✅ | ✅ |
| `moat.json` | ROIC persistence, margin stability | - | ✅ | ✅ | ✅ | ✅ |
| `management.json` | Capital allocation ratios | ✅ | - | - | - | ✅ |
| `peers.json` | ROIC persistence score (0-5) | - | ✅ | ✅ | ✅ | ✅ |
| `risks.json` | Coverage, debt/equity, margin trends | - | ✅ | ✅ | ✅ | ✅ |
| `thesis.json` | Quality score composite | - | - | ✅ | ✅ | ✅ |

**Legend:**
- ✅ Phase contributes to this output
- ✅ Ready (in Ready column)

**🎉 All Qualitative Agent outputs now have the required quantitative data!**

---

## 10. Code Quality Guidelines

### 10.1 Style Guide

- **Python:** Follow PEP 8, use Black formatter
- **Type Hints:** Required for all function signatures
- **Docstrings:** Google style, include examples for complex functions
- **Imports:** Group by stdlib → third-party → local

### 10.2 Complexity Limits

| Metric | Limit |
|--------|-------|
| Function length | ≤50 lines |
| Cyclomatic complexity | ≤10 |
| Cognitive complexity | ≤15 |
| File length | ≤500 lines |

### 10.3 DRY Patterns

Extract common patterns:
```python
# Good: Reusable series fetcher
def _fetch_series(cik: str, table: str, columns: list[str]) -> list[dict]:
    ...

# Bad: Copy-paste SQL in each function
def roic_series(cik): 
    rows = execute("SELECT fy, ... FROM ...")
def coverage_series(cik):
    rows = execute("SELECT fy, ... FROM ...")  # duplicated
```

### 10.4 Error Handling

```python
# Good: Explicit error handling with context
def compute_metric(cik: str) -> Optional[float]:
    try:
        data = fetch_data(cik)
        if not data:
            return None
        return calculate(data)
    except ZeroDivisionError:
        logger.warning(f"Division by zero for {cik}")
        return None

# Bad: Silent failures
def compute_metric(cik: str):
    try:
        return calculate(fetch_data(cik))
    except:
        pass
```

### 10.5 Post-Implementation Refactoring Checklist

After each phase, before merging:

- [ ] Run `black .` for formatting
- [ ] Run `mypy app/` for type checking
- [ ] Run `flake8 app/` for linting
- [ ] Run `radon cc app/ -a` for complexity
- [ ] Review for code duplication
- [ ] Ensure all new functions have docstrings
- [ ] Update this README with completion status

---

## Appendix A: File Reference

| File | Purpose |
|------|---------|
| `backend/app/db/models.py` | SQLAlchemy models for all tables |
| `backend/app/ingest/sec.py` | SEC EDGAR data ingestion |
| `backend/app/metrics/compute.py` | All metric calculations |
| `backend/app/valuation/core.py` | Valuation formulas |
| `backend/app/valuation/service.py` | Valuation orchestration |
| `backend/app/nlp/fourm/service.py` | Four Ms analysis |
| `backend/app/nlp/fourm/sec_item1.py` | Item 1 extraction |
| `backend/app/api/v1/routes.py` | All API endpoints |

---

## Appendix B: Formula Reference

```
CAGR = (End / Start)^(1/years) - 1

NOPAT = EBIT × (1 - Tax Rate)

ROIC = NOPAT / Invested Capital
     where Invested Capital = Debt + Equity - Cash

Owner Earnings = CFO - CapEx

Interest Coverage = EBIT / Interest Expense

Net Debt = Total Debt - Cash

Debt/Equity = Total Debt / Shareholder Equity

Gross Margin = Gross Profit / Revenue

Sticker Price = (EPS₀ × (1+g)¹⁰ × PE) / (1+r)¹⁰

MOS Price = Sticker × (1 - MOS%)

Ten Cap = Owner Earnings / 0.10

Payback Time = Years until Σ(OE × (1+g)^n) ≥ Price
```

---

## Appendix C: Spec Document References

| Document | Location | Purpose |
|----------|----------|---------|
| Functional Spec v5 | `docs/spec-ideas/functional-spec-v5.md` | Overall system requirements |
| Rule #1 Summary v2 | `docs/spec-ideas/summary-rule1-v2.md` | Big Five + Valuation methods |
| Qualitative Analysis v1 | `docs/spec-ideas/qualitative-analysis-v1.md` | QVG framework |
| Qualitative Analysis v2 | `docs/spec-ideas/qualitative-analysis-v2.md` | Agent output schemas |

---

**Document Maintainer:** Engineering Team  
**Review Cadence:** Update after each phase completion
