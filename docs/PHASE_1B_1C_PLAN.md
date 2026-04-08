# Phase 1B + 1C Implementation Plan

**Branch:** `rahul/phase-1b-1c-industry-enrichment`
**Created:** 2026-04-07
**Status:** Ready for implementation
**Predecessor:** Phase 1A (bug fixes + XBRL enrichment, merged in PRs #5 and #6)

---

## Guiding Principles

1. **Spec-aligned scope** — functional-spec-v5.md says the agent researches industry context. We provide SIC codes + raw data; the agent does the reasoning.
2. **No metric suppression or industry-specific scoring** — that's Phase 2 valuation plugins.
3. **New metrics serve the agent** — operating margin, FCF margin, cash conversion, ROE are concrete data gaps the agent can't work around.
4. **Test everything, verify in browser** — unit tests, integration tests, then ingest diverse companies and verify via Chrome MCP.

---

## Phase 1B: Industry Classification (Minimal)

**Goal:** Tell the agent what industry a company is in. That's it.

### What we're building

1. **Fetch SIC code** from SEC EDGAR submissions endpoint during ingestion
2. **Store SIC + category** on the Company record (columns already exist)
3. **Expose in agent-bundle** so the agent has industry context
4. **Update workflow scripts** to use industry data

### What we're NOT building (deferred)

- Metric suppression/flagging per industry
- Metric applicability matrix in Python
- Industry-specific thresholds in scoring
- Industry-specific metrics (ROE for banks, FFO for REITs — ROE moves to 1C as a universal metric)

### Tasks

#### 1B.1: Add SEC submissions endpoint

**File:** `backend/app/ingest/sec.py`

Add a new function to fetch company metadata:
```python
def company_submissions(cik: int) -> dict:
    return fetch_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
```

The response includes:
- `sic`: SIC code (string, e.g., "7372")
- `sicDescription`: Human-readable (e.g., "SERVICES-PREPACKAGED SOFTWARE")
- `category`: Filing category
- `fiscalYearEnd`: Month (e.g., "0630" for June)

#### 1B.2: Create SIC-to-category mapping

**File:** New `backend/app/core/industry.py`

Simple dict mapping SIC division ranges to broad categories:
- SIC 0100-0999 → agriculture
- SIC 1000-1499 → mining
- SIC 1500-1799 → construction
- SIC 2000-3999 → manufacturing
- SIC 4000-4999 → transportation_utilities
- SIC 5000-5199 → wholesale
- SIC 5200-5999 → retail
- SIC 6000-6199 → banking (depository institutions)
- SIC 6200-6399 → securities_investments
- SIC 6500-6599 → reits (real estate)
- SIC 6000-6999 → financials (catch-all)
- SIC 7000-8999 → services
- SIC 7372-7374 → technology (software)
- SIC 3571-3672 → technology (hardware)
- SIC 2830-2836 → pharma
- SIC 4911-4991 → utilities (electric/gas/water)
- SIC 1311-1389 → energy (oil & gas)
- SIC 3760-3769 → defense

Expose as:
```python
def sic_to_category(sic_code: str) -> str:
    """Map SIC code to broad industry category."""

def sic_to_metric_notes(sic_code: str) -> list[str]:
    """Return plain-English notes about what the agent should know.
    e.g., ['ROIC is not meaningful for depository banks',
           'Interest income is core revenue, not expense']
    """
```

The metric_notes are informational strings for the agent — NOT suppression logic.

#### 1B.3: Populate SIC during ingestion

**File:** `backend/app/ingest/sec.py`

In `ingest_companyfacts_richer_by_ticker()`:
1. Call `company_submissions(cik)` to get SIC + fiscal year end
2. Pass SIC description to `upsert_company()` as `industry`
3. Pass category to `upsert_company()` as `sector`

Update `upsert_company()` to accept and store `sector` and `industry`.

#### 1B.4: Add to agent-bundle endpoint

**File:** `backend/app/api/v1/routes.py`

Expand the company dict in the agent-bundle response:
```python
"company": {
    "cik": cik,
    "ticker": ticker,
    "name": name,
    "sic_code": sic_code,           # raw SIC
    "sic_description": industry,     # from SEC
    "industry_category": sector,     # our mapping
    "industry_notes": sic_to_metric_notes(sic_code),  # agent guidance
}
```

#### 1B.5: Update workflow scripts

**File:** `backend/scripts/workflows/coverage_matrix.py`, `metrics_snapshot.py`

- `coverage_matrix.py`: Show industry_category from DB instead of hardcoded cohort lookup
- `metrics_snapshot.py`: Include SIC-based notes in anomaly detection context

#### 1B.6: Tests

- **Unit test:** `sic_to_category()` mapping covers all SIC ranges, returns sensible categories
- **Unit test:** `sic_to_metric_notes()` returns notes for banks, REITs, utilities
- **Integration test:** Ingest MSFT, verify SIC code = "7372", sector = "technology"
- **Integration test:** Agent-bundle includes industry fields after ingestion

#### 1B.7: Update memory files

- Update `.claude/memory/industry_expectations.md` with SIC code ranges
- Update `.claude/memory/known_patterns.md` with SIC-based pattern notes

---

## Phase 1C: Enrich Quantitative Substrate

**Goal:** Add the derived metrics the agent genuinely needs but can't compute itself.

### What we're building

New metric functions in `compute.py`, exposed via timeseries and agent-bundle endpoints.

### What we're deferring

- Quarterly (10-Q) ingestion — significant architecture change, Phase 2
- TTM calculations — depends on quarterly data
- SBC ingestion — requires new XBRL tags + IS model change
- Goodwill ingestion — requires new BS model column
- Fiscal year end month — moves to 1B (from submissions endpoint)
- Currency detection — low priority, most S&P 500 file in USD

### Tasks

#### 1C.1: Add operating_margin_series()

**File:** `backend/app/metrics/compute.py`

```python
def operating_margin_series(cik: str) -> list[dict]:
    """EBIT / Revenue per fiscal year."""
```

Revenue and EBIT already in statement_is. Simple ratio.

#### 1C.2: Add fcf_margin_series()

**File:** `backend/app/metrics/compute.py`

```python
def fcf_margin_series(cik: str) -> list[dict]:
    """(CFO - CapEx) / Revenue per fiscal year."""
```

Requires joining IS (revenue) with CF (cfo, capex). Similar to existing owner_earnings_series.

#### 1C.3: Add cash_conversion_ratio()

**File:** `backend/app/metrics/compute.py`

```python
def cash_conversion_series(cik: str) -> list[dict]:
    """CFO / Net Income per fiscal year. >1.0 = high quality earnings."""
```

#### 1C.4: Add roe_series()

**File:** `backend/app/metrics/compute.py`

```python
def roe_series(cik: str) -> list[dict]:
    """Net Income / Shareholder Equity per fiscal year.
    Returns None for years with equity <= 0 (same guard as ROIC)."""
```

This is universally useful, not just for banks. The agent can use it as a complement to ROIC.

#### 1C.5: Store fiscal_year_end_month on Company

**File:** `backend/app/db/models.py`, `backend/app/ingest/sec.py`

The SEC submissions endpoint returns `fiscalYearEnd` (e.g., "0630" for June).
- Add `fiscal_year_end_month` column to Company model (Integer, nullable)
- Parse from submissions response during ingestion
- Expose in agent-bundle

Requires an Alembic migration.

#### 1C.6: Expose new metrics in timeseries endpoint

**File:** `backend/app/api/v1/routes.py`

Add to `timeseries_all()` or the timeseries endpoint:
- `operating_margin` series
- `fcf_margin` series
- `cash_conversion` series
- `roe` series

#### 1C.7: Add to agent-bundle

**File:** `backend/app/api/v1/routes.py`

Add new metrics to the quality_scores or metrics section of the agent-bundle:
- Latest operating margin + trend
- Latest FCF margin
- Latest cash conversion ratio
- ROE average (similar to ROIC average)

#### 1C.8: Tests

For each new metric function:
- **Unit test:** Happy path with mock data (3 years of IS/BS/CF data)
- **Unit test:** Edge cases — zero revenue (division), negative equity (ROE guard), missing CFO
- **Unit test:** Single year of data
- **Integration test:** Ingest MSFT, verify operating margin ~41%, FCF margin ~28%, cash conversion >1.0
- **Regression test:** Existing metrics unchanged after adding new ones

#### 1C.9: Update workflow scripts

- `metrics_snapshot.py`: Include new metrics in the snapshot output + anomaly detection
- Update `.claude/memory/industry_expectations.md` with expected ranges for new metrics

---

## Implementation Order

```
1B.1  Add SEC submissions endpoint
1B.2  Create SIC-to-category mapping (app/core/industry.py)
1B.3  Populate SIC during ingestion + migration if needed
1B.5  Update workflow scripts
1B.6  Tests for 1B
  |
  v
1C.5  Store fiscal_year_end_month (piggybacks on submissions data from 1B)
1C.1  Add operating_margin_series()
1C.2  Add fcf_margin_series()
1C.3  Add cash_conversion_series()
1C.4  Add roe_series()
1C.6  Expose in timeseries endpoint
1C.7  Add to agent-bundle
1B.4  Expand agent-bundle with industry + new metrics (one combined change)
1C.8  Tests for 1C
  |
  v
1B.7 + 1C.9  Update memory files and workflow scripts
  |
  v
E2E VERIFICATION:
  - Ingest full stress test cohort (18 companies, 9 industries)
  - Run /project:validate-tags to check coverage
  - Run /project:check-metrics for sample companies (MSFT, JPM, O, NEE, SBUX)
  - Verify agent-bundle in Chrome browser via MCP for 3+ diverse companies
  - Run /project:check-regressions against baseline
```

---

## Verification Checklist (End-to-End)

After all code is done, verify by ingesting and checking in browser:

| Company | Industry | Key checks |
|---------|----------|------------|
| MSFT | technology | All metrics populated, operating margin ~41%, SIC=7372 |
| JPM | banking | SIC=6021, industry_notes mention ROIC not meaningful |
| O | reits | SIC=6798, industry_notes mention FFO |
| NEE | utilities | SIC=4911, industry_notes mention low ROIC is structural |
| SBUX | consumer_neg_equity | ROE returns None (negative equity), SIC stored |
| XOM | energy | All metrics populated, cyclical revenue noted |
| CRM | technology/services | Operating margin, FCF margin populated |

Use Chrome MCP to hit `/api/v1/company/{ticker}/agent-bundle` and visually confirm:
- `company.sic_code` present
- `company.industry_category` present
- `company.industry_notes` present (array of strings)
- New metrics in timeseries (operating_margin, fcf_margin, cash_conversion, roe)

---

## Files Changed (Expected)

### New files
- `backend/app/core/__init__.py`
- `backend/app/core/industry.py` — SIC mapping + category + notes
- `backend/alembic/versions/XXXX_add_fiscal_year_end_month.py` — migration
- `backend/tests/test_industry_classification.py` — 1B tests
- `backend/tests/test_enriched_metrics.py` — 1C tests

### Modified files
- `backend/app/ingest/sec.py` — add submissions endpoint, populate SIC + FY end
- `backend/app/db/models.py` — add fiscal_year_end_month column
- `backend/app/metrics/compute.py` — 4 new metric functions
- `backend/app/api/v1/routes.py` — expand agent-bundle + timeseries
- `backend/scripts/workflows/coverage_matrix.py` — use DB industry
- `backend/scripts/workflows/metrics_snapshot.py` — include new metrics
- `.claude/memory/industry_expectations.md` — add SIC ranges + new metric ranges
- `.claude/memory/known_patterns.md` — add SIC-related patterns

---

## Acceptance Criteria

### Phase 1B
- [ ] `Company.sector` and `Company.industry` populated for all ingested companies
- [ ] SIC code stored and mapped to category
- [ ] Agent-bundle includes `sic_code`, `industry_category`, `industry_notes`
- [ ] `fiscal_year_end_month` stored on Company
- [ ] Unit tests pass for SIC mapping
- [ ] Integration test: ingest MSFT, verify SIC fields populated

### Phase 1C
- [ ] `operating_margin_series()` returns data for MSFT (~41% recent)
- [ ] `fcf_margin_series()` returns data for MSFT (~28% recent)
- [ ] `cash_conversion_series()` returns data, MSFT >1.0
- [ ] `roe_series()` returns data for MSFT, None for SBUX (negative equity)
- [ ] All new metrics in timeseries endpoint
- [ ] All new metrics in agent-bundle
- [ ] Unit tests for all new functions + edge cases
- [ ] No regressions in existing 352+ tests

### End-to-End
- [ ] Full cohort ingested successfully
- [ ] Coverage matrix shows no unexpected new NULLs
- [ ] Agent-bundle verified in Chrome browser for 3+ companies
- [ ] Regression check passes against baseline
