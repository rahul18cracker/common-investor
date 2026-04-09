# Quantitative Analysis Gap Analysis V2 — Deep Correctness & Industry Readiness

> **Purpose:** This document supersedes the original `QUANTITATIVE_GAP_ANALYSIS.md` (which tracked Phase A-F metric additions). V2 focuses on **data correctness bugs, industry-awareness gaps, missing data dimensions, and shallow test coverage** — problems that would cause the Qualitative Analysis Agent to produce confidently wrong outputs.

**Created:** March 9, 2026
**Updated:** April 8, 2026
**Status:** Phases 1D, 1A, 1B, 1C complete — quantitative foundation ready for agent
**Predecessor:** `docs/QUANTITATIVE_GAP_ANALYSIS.md` (Phase A-F, all marked complete)

---

## Table of Contents

1. [Why V2 Is Needed](#1-why-v2-is-needed)
2. [Known Bugs](#2-known-bugs)
3. [Industry Awareness Gaps](#3-industry-awareness-gaps)
4. [Missing Data Dimensions](#4-missing-data-dimensions)
5. [Test Coverage Gaps](#5-test-coverage-gaps)
6. [Implementation Plan](#6-implementation-plan)
7. [Multi-Industry Test Portfolio](#7-multi-industry-test-portfolio)
8. [Agent Bundle V2 Schema](#8-agent-bundle-v2-schema)
9. [Spec Document Updates Required](#9-spec-document-updates-required)

---

## 1. Why V2 Is Needed

The original gap analysis asked: "Do the metrics exist?" The answer was yes — Phase A-F added gross margin series, revenue volatility, ROIC persistence, balance sheet resilience, etc.

V2 asks the harder questions:
- **Are the metrics correct across all company types?** (No — banks, REITs, negative-equity companies produce misleading results)
- **Does the system know what kind of company it's analyzing?** (No — zero industry classification)
- **Are there silent bugs in the computation layer?** (Yes — at least 3 identified)
- **Is the test coverage meaningful?** (Partially — happy path only, no edge cases, no Four Ms tests)
- **Can the agent distinguish trustworthy data from misleading data?** (No — no data quality flags)

---

## 2. Known Bugs

### BUG-1: Zero Growth Treated as Missing (CRITICAL) — ✅ FIXED (PR #5)

**Fixed in:** `valuation/service.py`, `nlp/fourm/service.py`
Uses `is not None` checks instead of `or` chain. Regression test added.

### BUG-2: Total Debt First-Match Instead of Sum (MODERATE) — ✅ FIXED (PR #6)

**Fixed in:** `ingest/sec.py`
Implemented `_sum_annual_values()` with `DEBT_COMPONENT_TAGS` that sums LT noncurrent + current debt.
Also added `SGA_COMPONENT_TAGS` for SGA summing and `DEPRECIATION_CF_TAGS` for CF fallback.

### BUG-3: Negative Equity Companies Produce Garbage Metrics (MODERATE) — ✅ FIXED (PR #5)

**Fixed in:** `metrics/compute.py`, `nlp/fourm/service.py`
`roic_series()` returns None when invested capital <= 0. `latest_debt_to_equity()` returns None when equity <= 0.
`roe_series()` (added in PR #7) uses the same guard. Regression tests added for SBUX-like data.

---

## 3. Industry Awareness Gaps

### GAP-IND-1: No Industry Classification — ✅ CLOSED (PR #7)

**Fixed in:** `ingest/sec.py`, `app/core/industry.py`, `db/models.py`
SIC code fetched from SEC submissions endpoint during ingestion. Mapped to broad categories
(technology, banking, reits, utilities, energy, pharma, defense, etc.) via `sic_to_category()`.
`sic_to_metric_notes()` provides plain-English guidance for the agent per industry.
Agent-bundle includes `sic_code`, `industry_category`, `industry_notes`, `fiscal_year_end_month`.

### GAP-IND-2: No Metric Applicability Matrix — Deferred to Phase 2

The agent now receives `industry_notes` — plain-English guidance like "ROIC is not meaningful
for depository banks". This is informational, not suppression. Full metric applicability matrix
with SUPPRESS/Caution/Replace logic is deferred to Phase 2 valuation plugins, per the
functional-spec-v5.md design: the agent researches industry context and makes its own judgment.

### GAP-IND-3: Missing Industry-Specific XBRL Tags — Deferred to Phase 2

Banks (Net Interest Income, Provision for Loan Losses), REITs (FFO, AFFO), and regulatory
metrics (CET1 Ratio) require industry-specific XBRL taxonomy work. Documented in
`.claude/memory/industry_expectations.md` so the agent knows what's missing.

---

## 4. Missing Data Dimensions

### DIM-1: Quarterly Data (10-Q) — Deferred to Phase 2

Significant architecture change (new statement tables, ingestion pipeline rework). Agent works with annual data for now.

### DIM-2: Operating Margin Series — ✅ CLOSED (PR #7)

`operating_margin_series(cik)` added to `metrics/compute.py`. EBIT/Revenue per fiscal year. Exposed in timeseries and agent-bundle.

### DIM-3: FCF Margin Series — ✅ CLOSED (PR #7)

`fcf_margin_series(cik)` added. (CFO - CapEx) / Revenue. Joins IS and CF data. Exposed in timeseries and agent-bundle.

### DIM-4: Cash Conversion Ratio — ✅ CLOSED (PR #7)

`cash_conversion_series(cik)` added. CFO / Net Income. >1.0 = high quality earnings. Exposed in timeseries and agent-bundle.

### DIM-5: Return on Equity (ROE) — ✅ CLOSED (PR #7)

`roe_series(cik)` added. NI / Equity with negative equity guard (returns None when equity <= 0). Exposed in timeseries and agent-bundle.

### DIM-6: Share-Based Compensation — Deferred to Phase 2

Requires new XBRL tags + IS model change. Agent notes mention SBC distortion for SaaS companies.

### DIM-7: Goodwill & Intangibles — Deferred to Phase 2

Requires new BS model column. Low priority for current agent scope.

### DIM-8: Fiscal Year End Awareness — ✅ CLOSED (PR #7)

`fiscal_year_end_month` column added to Company model. Parsed from SEC submissions endpoint (`fiscalYearEnd` field). Alembic migration `0003`. Exposed in agent-bundle.

### DIM-9: Currency Awareness — Deferred to Phase 2

Low priority — most S&P 500 file in USD.

---

## 5. Test Coverage Gaps

### Current Test Files (backend/tests/)

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_valuation_metrics_math.py` | 4 | Basic happy path: cagr, sticker, ten_cap, payback |
| `test_metrics_series.py` | 4 | owner_earnings, roic, coverage, revenue_eps with monkeypatched execute |
| `test_api_routes.py` | ~20 | API endpoint response codes and basic shapes |
| `test_fourm_service_phase_c.py` | ~15 | Phase C moat/balance sheet additions |
| `test_metrics_compute_comprehensive.py` | ~15 | Extended metrics from Phase B |
| `test_ingest_sec.py` | ~10 | Ingestion pipeline |
| `test_performance_benchmarks.py` | ~10 | Performance timing |

### What's NOT Tested

| Gap | Why It Matters |
|-----|----------------|
| **Negative equity edge cases** | SBUX/MCD would produce ROIC > 500%, uncaught |
| **Zero/negative EBIT** | Coverage ratio division, ROIC with negative NOPAT |
| **Single-year data** | Many metrics assume >=2 or >=3 years of data |
| **Missing fields (None throughout)** | What happens when a company has no gross_profit? |
| **The `or` zero-growth bug** | No test catches g=0.0 falling through |
| **XBRL tag fallback behavior** | No test verifies tag 2 is picked when tag 1 is missing |
| **Scoring boundary values** | What's the score at exactly ROIC=0.15? D/E=0.3? |
| **`compute_moat()` end-to-end** | Tested in Phase C but not with diverse company profiles |
| **`compute_management()` edge cases** | What if CFO is negative? Buybacks > CFO? |
| **`agent-bundle` response completeness** | No test verifies all expected keys exist |
| **Multi-industry data correctness** | No test ingests a bank or REIT and checks outputs |

### Test Strategy for V2

Each implementation phase should include:
1. **Regression tests** for the specific bugs fixed
2. **Edge case tests** with extreme/pathological data
3. **Industry integration tests** using real SEC data from diverse companies
4. **Property-based tests** for scoring functions (score always in valid range)

---

## 6. Implementation Plan

### Phase 1D: Multi-Industry Stress Test — ✅ COMPLETE
**Branch:** `rahul/phase-1d-industry-stress-test`
**Artifacts:** Stress test scripts in `backend/scripts/workflows/`, cohort of 18 companies in `scripts/workflows/cohort.py`.

---

### Phase 1A: Fix Data Correctness Bugs — ✅ COMPLETE (PRs #5, #6)
**PRs:** #5 (bug fixes), #6 (XBRL tag enrichment from edgartools spike)
**Summary:** Zero-growth `or` chain fixed, total_debt summing implemented, negative equity guards added, XBRL tags enriched from edgartools concept_mappings.json (MIT). 352+ tests at merge.

---

### Phase 1B: Industry Classification — ✅ COMPLETE (PR #7)
**Branch:** `rahul/phase-1b-1c-industry-enrichment`
**Summary:** SIC code ingestion from SEC submissions endpoint, `sic_to_category()` mapping, `sic_to_metric_notes()` agent guidance, fiscal_year_end_month. Agent-bundle expanded with industry context. 33 new tests. Metric applicability matrix deferred to Phase 2 (agent gets notes instead of suppression).

---

### Phase 1C: Enrich Quantitative Substrate — ✅ COMPLETE (PR #7, scoped to essentials)
**Summary:** Four new metrics (operating margin, FCF margin, cash conversion, ROE), fiscal year end month, all exposed in timeseries and agent-bundle. 27 new tests.

**Deferred to Phase 2 (significant architecture changes):**
- 10-Q quarterly ingestion + TTM calculations
- SBC ingestion (new XBRL tags + IS model change)
- Goodwill/intangibles (new BS model column)
- Currency detection
- MetricsYearly persistence

---

### Phase 1E: Agent Bundle V2 — Partially Complete, Remainder Deferred

**Done (in PR #7):** Agent-bundle includes industry context (`sic_code`, `industry_category`, `industry_notes`, `fiscal_year_end_month`) and new metric summaries (`latest_operating_margin`, `latest_fcf_margin`, `latest_cash_conversion`, `roe_avg`).

**Deferred to Phase 2:**
- `data_quality` section with `years_of_data`, `missing_fields`, `negative_equity` flags
- `metric_applicability` section with SUPPRESS/Caution/Replace logic
- Dedicated `/data-quality` endpoint
- TTM metrics in bundle (depends on quarterly data)

---

## 7. Multi-Industry Test Portfolio

Companies to ingest and validate in Phase 1D:

| Industry | Tickers | Why These |
|----------|---------|-----------|
| **Tech** | MSFT, AAPL, GOOG | Clean data, well-tested baseline |
| **Banks** | JPM, BAC | ROIC meaningless, deposits != debt, regulatory capital |
| **REITs** | O, SPG | EPS misleading, FFO matters, high leverage is structural |
| **Defense** | LMT, RTX | Government contract concentration, stable but different |
| **Consumer (neg equity)** | MCD, SBUX | Negative shareholder equity from buybacks |
| **Energy** | XOM, CVX | Cyclical, commodity-driven, different CapEx dynamics |
| **Utilities** | NEE, DUK | Regulated, low ROIC is structural, DDM-appropriate |
| **Healthcare** | JNJ, UNH | Different sub-models (pharma vs payer) |
| **SaaS** | CRM, NOW | High SBC distorts EPS, recurring revenue |

**For each company, capture:**
1. Raw ingestion success (all IS/BS/CF fields populated?)
2. Metrics output (any None where shouldn't be? any extreme values?)
3. Four Ms scores (reasonable? or misleading?)
4. Valuation output (sensible? or garbage?)
5. XBRL tag match log (which tags hit? which missed?)

---

## 8. Agent Bundle V2 Schema

Proposed additions to `GET /company/{ticker}/agent-bundle`:

```json
{
  "company": {
    "cik": "...",
    "ticker": "...",
    "name": "...",
    "sic_code": "6021",
    "industry_category": "financials",
    "fiscal_year_end_month": 12,
    "currency": "USD"
  },
  "data_quality": {
    "years_of_annual_data": 10,
    "quarters_available": 8,
    "missing_fields": ["goodwill", "sbc"],
    "negative_equity": false,
    "negative_equity_years": [],
    "data_completeness_pct": 0.92
  },
  "industry_context": {
    "category": "financials",
    "metric_applicability": {
      "roic": {"applicable": false, "reason": "Banks lack traditional invested capital"},
      "roe": {"applicable": true, "primary": true},
      "debt_equity": {"applicable": false, "reason": "Deposits distort leverage ratios"},
      "sticker_price": {"applicable": false, "reason": "EPS-based valuation inappropriate for banks"},
      "interest_coverage": {"applicable": false, "reason": "Interest is core business, not expense"}
    }
  },
  "metrics": { "..." },
  "metrics_ttm": { "..." },
  "quality_scores": { "..." },
  "four_ms": { "..." },
  "timeseries": { "..." }
}
```

---

## 9. Spec Document Updates Required

| Document | Update Needed | When |
|----------|---------------|------|
| `functional-spec-v5.md` -> v6 | Add data correctness guarantees, industry classification, quarterly data, new metrics | After Phase 1C |
| New: `industry-classification-v1.md` | SIC mapping, metric applicability matrix, industry-specific thresholds | Phase 1B |
| New: `industry-test-results.md` | Per-industry findings from stress test | Phase 1D |
| `qualitative-analysis-v2.md` -> v3 | Updated agent playbook accounting for industry context and data quality flags | Phase 1E |
| `QUANTITATIVE_GAP_ANALYSIS.md` | Add note pointing to this V2 document | Now |

---

## Appendix: Dependency Graph

```
Phase 1D (Stress Test)               ✅ Complete
    |
    v
Phase 1A (Data Correctness)          ✅ Complete (PRs #5, #6)
    |
    v
Phase 1B (Industry Classification)   ✅ Complete (PR #7)
    |
    v
Phase 1C (Enrich Metrics)            ✅ Complete — essentials (PR #7)
    |                                   Deferred: quarterly, TTM, SBC, goodwill
    v
Phase 1E (Agent Bundle V2)           ✅ Partially complete (PR #7)
    |                                   Deferred: data_quality flags, metric_applicability
    v
[Agent work can begin]               ✅ Ready — quantitative foundation sufficient
```

---

**Document Maintainer:** Rahul + Claude Code
**Review Cadence:** Update after each phase completion
