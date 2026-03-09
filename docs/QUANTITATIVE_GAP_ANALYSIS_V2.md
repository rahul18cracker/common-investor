# Quantitative Analysis Gap Analysis V2 — Deep Correctness & Industry Readiness

> **Purpose:** This document supersedes the original `QUANTITATIVE_GAP_ANALYSIS.md` (which tracked Phase A-F metric additions). V2 focuses on **data correctness bugs, industry-awareness gaps, missing data dimensions, and shallow test coverage** — problems that would cause the Qualitative Analysis Agent to produce confidently wrong outputs.

**Created:** March 9, 2026
**Status:** Planning — implementation not yet started
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

### BUG-1: Zero Growth Treated as Missing (CRITICAL)

**Location:** `backend/app/valuation/service.py:15`
```python
g = g_override if g_override is not None else (
    growths.get("eps_cagr_5y") or growths.get("rev_cagr_5y") or
    growths.get("eps_cagr_10y") or growths.get("rev_cagr_10y") or 0.10
)
```

**Problem:** Python's `or` operator treats `0.0` as falsy. A company with exactly 0% EPS growth (flat EPS) falls through to revenue CAGR or the 0.10 default. This **overstates valuations** for flat/slow-growth companies.

**Impact:** Sticker Price, Payback Time, and MOS Recommendation all consume `g`. A company with 0% EPS growth and 8% revenue growth gets valued at 8% growth instead of 0%.

**Fix:** Use `is not None` checks:
```python
g = g_override
if g is None:
    g = growths.get("eps_cagr_5y")
if g is None:
    g = growths.get("rev_cagr_5y")
# ... etc
if g is None:
    g = 0.10
```

**Same bug also in:** `backend/app/nlp/fourm/service.py:330`
```python
g = growths.get("eps_cagr_5y") or growths.get("rev_cagr_5y") or 0.10
```

### BUG-2: Total Debt First-Match Instead of Sum (MODERATE)

**Location:** `backend/app/ingest/sec.py:77-83`
```python
"total_debt": [
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "LongTermDebtCurrent",
    "DebtCurrent",
    "ShortTermBorrowings",
],
```

**Problem:** `_pick_first_units()` returns the **first matching tag** from this list. For companies that report both long-term and short-term debt under separate tags, only one is captured. Total debt = LT debt + current portion of LT debt + short-term borrowings, but we only get whichever tag appears first.

**Impact:** Understates total debt for many companies, making debt/equity ratios look artificially low and balance sheet resilience scores artificially high.

**Fix:** Either:
- (a) Add a composite tag like `LongTermDebtAndFinanceLeaseObligations` higher in the list, or
- (b) Implement a `_sum_units()` function that aggregates multiple tags instead of picking the first.

Option (b) is more correct but requires changing the ingestion architecture. Option (a) is a pragmatic improvement.

### BUG-3: Negative Equity Companies Produce Garbage Metrics (MODERATE)

**Companies affected:** Starbucks (SBUX), McDonald's (MCD), Philip Morris (PM), Boeing (BA) — all have negative shareholder equity due to aggressive buybacks or accumulated losses.

**Impact across metrics:**
- **ROIC:** `Invested Capital = Equity + Debt - Cash`. With negative equity, invested capital can be tiny or negative, producing ROIC of 500%+ or negative when the business is actually profitable.
- **Debt/Equity:** Negative or meaningless when equity < 0.
- **Balance Sheet Resilience:** debt_equity_score blows up.
- **Moat Score:** inflated ROIC average feeds into moat calculation.

**Fix:** Detect negative equity and either:
- Flag it explicitly in the output (`negative_equity: true`)
- Use alternative metrics (ROA, or ROIC with `invested_capital = total_assets - excess_cash`)
- Clamp ROIC to a reasonable range (e.g., -1.0 to 2.0) and flag when clamped

---

## 3. Industry Awareness Gaps

### GAP-IND-1: No Industry Classification

The `Company` model has `sector` and `industry` columns but they are **never populated**. The system treats every company identically — a bank, a REIT, a SaaS company, and a manufacturer all get the same metrics and scoring.

**Why this matters for the agent:** The agent will receive ROIC scores for JPMorgan and conclude it has weak economics. In reality, ROIC is meaningless for banks — they don't have "invested capital" in the traditional sense.

**Fix:** Ingest SIC code from SEC EDGAR filing headers (available in CompanyFacts metadata or filing index). Map SIC to broad industry categories.

### GAP-IND-2: No Metric Applicability Matrix

Even after classification, the system doesn't know which metrics are appropriate for which industry.

**Proposed matrix:**

| Metric | General | Banks | REITs | Utilities | SaaS |
|--------|---------|-------|-------|-----------|------|
| ROIC | Primary | SUPPRESS | SUPPRESS | Caution | Primary |
| ROE | Secondary | Primary | Secondary | Primary | Secondary |
| Debt/Equity | Primary | SUPPRESS | SUPPRESS | Caution | Primary |
| Interest Coverage | Primary | SUPPRESS | Secondary | Primary | Primary |
| Gross Margin | Primary | SUPPRESS | Secondary | Primary | Primary |
| Owner Earnings | Primary | SUPPRESS | Replace w/ AFFO | Primary | Primary (adj SBC) |
| Sticker Price | Primary | SUPPRESS | SUPPRESS | Caution | Primary |
| Ten Cap | Primary | SUPPRESS | Replace w/ FFO cap | Primary | Primary |

"SUPPRESS" = don't compute, flag as inapplicable.
"Caution" = compute but flag that thresholds differ.
"Replace" = use industry-specific alternative (Phase 2 plugin).

### GAP-IND-3: Missing Industry-Specific XBRL Tags

Banks report under different XBRL taxonomies:
- Net Interest Income: `InterestIncomeExpenseNet`
- Provision for Loan Losses: `ProvisionForLoanLeaseAndOtherLosses`
- Non-Interest Income: `NoninterestIncome`
- CET1 Ratio: not in standard XBRL (regulatory filing)

REITs:
- FFO: `FundsFromOperations` (often non-standard, reported in supplemental)
- AFFO: typically derived, not filed directly

These are Phase 2 additions but should be documented now so the agent knows what's missing.

---

## 4. Missing Data Dimensions

### DIM-1: Quarterly Data (10-Q)

**Current:** Only 10-K annual data ingested.
**Impact:**
- No TTM (trailing twelve months) calculations — investors use TTM, not last annual
- Cannot detect growth inflection points within a year
- Agent cannot assess "how is the company doing right now"

**Fix:** Extend `_annual_value()` to support 10-Q forms, add quarterly statement tables or flag quarterly rows, compute TTM as sum of last 4 quarters.

### DIM-2: Operating Margin Series

**Current:** `margin_stability()` computes EBIT margin internally but doesn't expose the series. `gross_margin_series()` exists but not `operating_margin_series()`.

**Fix:** Add `operating_margin_series(cik)` returning `{fy, operating_margin}` dicts.

### DIM-3: FCF Margin Series

**Current:** Owner earnings (CFO - CapEx) exists as a series, but not as a percentage of revenue.

**Fix:** Add `fcf_margin_series(cik)` = (CFO - CapEx) / Revenue.

### DIM-4: Cash Conversion Ratio

**Current:** Not computed.
**Definition:** CFO / Net Income. Values persistently > 1.0 indicate high-quality earnings (cash exceeds accounting profit). Values < 0.8 suggest earnings quality concerns.

### DIM-5: Return on Equity (ROE)

**Current:** Not computed (only ROIC).
**Why needed:** Primary metric for banks/financials. Also useful universally as a complement to ROIC.
**Definition:** Net Income / Shareholder Equity.

### DIM-6: Share-Based Compensation

**Current:** Not in IS model or XBRL tags.
**Why needed:** For SaaS companies, SBC can be 20-30% of revenue. Without it, the agent can't assess "real" profitability. Available as XBRL tag `ShareBasedCompensation`.

### DIM-7: Goodwill & Intangibles

**Current:** Not tracked in BS model.
**Why needed:** Acquisition-heavy companies (most tech) may have 50-70% of total assets as goodwill. Tangible book value vs total book value is a key risk indicator.

### DIM-8: Fiscal Year End Awareness

**Current:** `fy` stored as integer year, but fiscal year-end month not tracked.
**Impact:** MSFT FY2023 = Jul 2022-Jun 2023. AAPL FY2023 = Oct 2022-Sep 2023. WMT FY2024 = Feb 2023-Jan 2024. Without FY end awareness, peer comparisons are misaligned.
**Fix:** Store `fiscal_year_end_month` on Company model (available from SEC filing metadata).

### DIM-9: Currency Awareness

**Current:** `Company.currency` column exists but never populated. Non-US filers (20-F) may report in local currency.
**Fix:** Detect currency from XBRL units and populate. Flag non-USD companies in agent bundle.

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

### Phase 1D: Multi-Industry Stress Test (RESEARCH SPIKE)
**Branch:** `rahul/phase-1d-industry-stress-test`
**Purpose:** Discover all problems by ingesting diverse companies and documenting what breaks.
**Depends on:** Nothing (pure research)

| Task | Description |
|------|-------------|
| 1D.1 | Create integration test that ingests ~18 companies across 9 industries (see Section 7) |
| 1D.2 | For each company, run all metrics + Four Ms + valuation and capture output |
| 1D.3 | Flag: any None where data should exist, extreme outliers (ROIC > 200%, D/E < 0), XBRL tag misses |
| 1D.4 | Document findings per industry in `docs/industry-test-results.md` |
| 1D.5 | Update this document with newly discovered bugs/gaps |

**Acceptance:** A documented report of what works and what breaks for each industry category.

---

### Phase 1A: Fix Data Correctness Bugs
**Branch:** `rahul/phase-1a-data-correctness`
**Purpose:** Make existing metrics trustworthy before adding new ones.
**Depends on:** 1D findings

| Task | Description | File |
|------|-------------|------|
| 1A.1 | Fix BUG-1: zero-growth `or` chain in valuation service | `valuation/service.py` |
| 1A.2 | Fix BUG-1 duplicate: zero-growth in MOS recommendation | `nlp/fourm/service.py` |
| 1A.3 | Fix BUG-2: total_debt aggregation (approach TBD after 1D findings) | `ingest/sec.py` |
| 1A.4 | Fix BUG-3: negative equity guards + flag | `metrics/compute.py`, `nlp/fourm/service.py` |
| 1A.5 | Add comprehensive unit tests for all Four Ms scoring functions | `tests/` |
| 1A.6 | Add edge case tests: negative EBIT, zero revenue, single-year, missing fields | `tests/` |
| 1A.7 | Add boundary value tests for all scoring thresholds | `tests/` |
| 1A.8 | Add regression test for BUG-1 (g=0.0 must not fall through) | `tests/` |
| 1A.9 | Add agent-bundle response completeness test | `tests/` |

**Acceptance:** All known bugs fixed, edge cases tested, CI passes with no regressions.

---

### Phase 1B: Industry Classification & Guardrails
**Branch:** `rahul/phase-1b-industry-awareness`
**Purpose:** Make the system know what kind of company it's analyzing.
**Depends on:** 1A

| Task | Description | File |
|------|-------------|------|
| 1B.1 | Ingest SIC code from SEC EDGAR headers, store on Company | `ingest/sec.py`, `db/models.py` |
| 1B.2 | Create SIC-to-category mapping (Tech, Financials, REIT, Energy, etc.) | New: `app/core/industry.py` |
| 1B.3 | Define metric applicability matrix per category | `app/core/industry.py` |
| 1B.4 | Add `industry_type` and `metric_warnings` to agent-bundle response | `api/v1/routes.py` |
| 1B.5 | Suppress/flag inapplicable metrics in Four Ms scoring | `nlp/fourm/service.py` |
| 1B.6 | Add integration tests: bank metrics correctly flagged, REIT metrics flagged | `tests/` |
| 1B.7 | Create spec doc: `docs/spec-ideas/industry-classification-v1.md` | New doc |

**Acceptance:** Agent bundle for JPM includes `industry_type: "financials"` and `metric_warnings` that flag ROIC/Sticker as inapplicable.

---

### Phase 1C: Enrich Quantitative Substrate
**Branch:** `rahul/phase-1c-quant-enrichment`
**Purpose:** Give the agent more and better data to work with.
**Depends on:** 1B

| Task | Description | File |
|------|-------------|------|
| 1C.1 | Add 10-Q quarterly ingestion | `ingest/sec.py` |
| 1C.2 | Add TTM calculation (sum of last 4 quarters) for key metrics | `metrics/compute.py` |
| 1C.3 | Persist MetricsYearly (compute + store, not just on-the-fly) | `metrics/compute.py`, `workers/tasks.py` |
| 1C.4 | Add `operating_margin_series(cik)` | `metrics/compute.py` |
| 1C.5 | Add `fcf_margin_series(cik)` | `metrics/compute.py` |
| 1C.6 | Add `cash_conversion_ratio(cik)` — CFO / Net Income | `metrics/compute.py` |
| 1C.7 | Add `roe_series(cik)` — Net Income / Equity | `metrics/compute.py` |
| 1C.8 | Add SBC to IS model + XBRL tags | `db/models.py`, `ingest/sec.py` |
| 1C.9 | Add goodwill to BS model + XBRL tags | `db/models.py`, `ingest/sec.py` |
| 1C.10 | Store fiscal_year_end_month on Company | `db/models.py`, `ingest/sec.py` |
| 1C.11 | Detect and store currency from XBRL units | `ingest/sec.py` |
| 1C.12 | Include all new series in timeseries endpoint | `api/v1/routes.py` |
| 1C.13 | Unit tests for all new metrics | `tests/` |

**Acceptance:** `/timeseries` returns operating margin, FCF margin, cash conversion, ROE. Quarterly data available. Agent bundle includes TTM metrics.

---

### Phase 1E: Agent Bundle V2
**Branch:** `rahul/phase-1e-agent-bundle-v2`
**Purpose:** Upgrade the agent's data interface with everything above.
**Depends on:** 1C

| Task | Description | File |
|------|-------------|------|
| 1E.1 | Agent bundle v2 schema: industry context, TTM, new ratios, data quality flags | `api/v1/routes.py` |
| 1E.2 | Add `GET /company/{ticker}/data-quality` validation endpoint | `api/v1/routes.py` |
| 1E.3 | Include `negative_equity`, `years_of_data`, `missing_fields`, `fiscal_year_end` in bundle | `api/v1/routes.py` |
| 1E.4 | Update spec: `docs/spec-ideas/qualitative-analysis-v3.md` with industry-aware playbook | New doc |
| 1E.5 | Integration test: agent bundle for 5 diverse companies validates schema completeness | `tests/` |

**Acceptance:** Agent bundle includes all data quality context needed for the agent to self-assess data reliability.

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
Phase 1D (Stress Test — research spike)
    |
    v
Phase 1A (Data Correctness — fix bugs found in 1D)
    |
    v
Phase 1B (Industry Classification + Guardrails)
    |
    v
Phase 1C (Enrich Quantitative Substrate)
    |
    v
Phase 1E (Agent Bundle V2)
    |
    v
[Agent work can begin]
```

---

**Document Maintainer:** Rahul + Claude Code
**Review Cadence:** Update after each phase completion
