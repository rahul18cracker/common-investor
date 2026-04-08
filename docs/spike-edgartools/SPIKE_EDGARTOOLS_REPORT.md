# Spike Report: edgartools as XBRL Parsing Replacement

**Date**: 2026-03-09
**Branch**: `rahul/spike-edgartools`
**Library version**: edgartools 5.22.0
**Decision**: **Option B — Take the mapping data, not the library**

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Spike Tasks & Data Findings](#spike-tasks--data-findings)
3. [Coverage Comparison Matrix](#coverage-comparison-matrix)
4. [Industry-Specific Findings](#industry-specific-findings)
5. [Regression Analysis](#regression-analysis)
6. [Edge Case Verification](#edge-case-verification)
7. [Deep Analysis: 6 Critical Questions](#deep-analysis-6-critical-questions)
8. [Three Options Considered](#three-options-considered)
9. [Decision: Option B — Take the Data, Not the Code](#decision-option-b--take-the-data-not-the-code)
10. [Next Steps](#next-steps)
11. [Appendix](#appendix)

---

## Executive Summary

edgartools dramatically improves data coverage for standard companies (+185 fields filled across 10 companies). It parses XBRL from individual 10-K filing documents rather than using the CompanyFacts aggregate API our current code uses.

However, after thorough analysis of the library's dependency chain (49 packages including pyarrow at 150MB), security surface (eval()/exec() in non-critical paths), debuggability (147K lines vs our 301), and maintenance risk (single maintainer), we concluded that **adopting the library brings too much unneeded complexity**.

The most valuable artifact from edgartools is not its code but its **mapping data**: `concept_mappings.json` (100 standard concepts with XBRL tag fallbacks) and `gaap_mappings.json` (2,921 XBRL concepts mapped to standard names from analyzing 32,240 filings). This accumulated XBRL taxonomy knowledge is exactly what our hand-curated tag lists lack.

**Decision**: Extract the mapping data (MIT licensed), enhance our existing `sec.py` with better tag fallback lists derived from it, and add ~50-100 lines of targeted logic for SGA splitting, total_debt summing, and depreciation fallback to CF. Zero new dependencies. Full ownership.

---

## Spike Tasks & Data Findings

### Task 1: API Exploration (MSFT)

**Key discoveries about edgartools' architecture:**

- `Company("MSFT").get_financials()` returns data from the latest 10-K only (covers 3 fiscal years)
- For multi-year data, iterate individual filings: `company.get_filings(form="10-K")`
- Each filing's XBRL is accessed via `filing.xbrl().statements.income_statement().to_dataframe()`
- The DataFrame has columns: `concept`, `label`, `standard_concept`, date columns (e.g., `2024-06-30`), `dimension`, `abstract`, `level`, `balance`, `weight`, `preferred_sign`
- Consolidated data is filtered by `dimension == False` and `abstract == False`
- The `standard_concept` column maps raw XBRL tags to standardized names — this is the core value
- Balance sheets contain 2 years per filing; Income statements and Cash flows contain 3
- MSFT fiscal year (June) correctly identified — dates show `2024-06-30` not `2024-12-31`
- Values are in full dollars (not millions), despite display saying "In millions"
- `get_quarterly_financials()` exists — annual/quarterly separation works

**Helper methods on the Financials object:**
```
get_revenue()              -> 281724000000.0
get_net_income()           -> 101832000000.0
get_operating_income()     -> 128528000000.0
get_operating_cash_flow()  -> 136162000000.0
get_capital_expenditures() -> 64551000000.0
get_total_assets()         -> 619003000000.0
get_stockholders_equity()  -> 343479000000.0
```

### Task 2+3: Field Mapping Comparison & Edge Cases

Ran comparison across 10 tickers x 26 fields x FY 2020-2024. See [Coverage Comparison Matrix](#coverage-comparison-matrix) below.

**Critical systematic issues discovered during comparison:**

1. **Balance sheet data availability**: BS only has 2 date columns per filing (current + prior year). For FY2020 BS data, you must use the filing from FY2020 or FY2021, not a later filing. The IS/CF from a FY2022 filing includes 3 years (2022, 2021, 2020), but the BS does not.

2. **Cash flow sign convention**: edgartools stores outflows as negative (accounting standard: capex = -$15.4B). Our DB stores them as positive ($15.4B). This is a predictable mapping difference, not a data quality issue.

3. **SGA splitting**: MSFT reports "Sales and marketing" and "General and administrative" as separate line items, not combined SGA. edgartools maps both to `standard_concept = SellingGeneralAndAdminExpenses`. Need to sum them.

4. **Dividends tag**: Our current code looks for `PaymentsOfDividends`. MSFT uses `PaymentsOfDividendsCommonStock`. edgartools finds it because it checks both tags.

5. **Company-specific XBRL tags**: MSFT uses `msft_AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets` instead of the standard `PaymentsToAcquireBusinessesNetOfCashAcquired`. edgartools can't find this either (it only maps standard us-gaap tags).

### Task 4: Integration Prototype

Built `spike_edgartools_prototype.py` with an `ingest_via_edgartools()` function. Results:
- MSFT: 21/24 fields populated per year (3 NULLs: interest_expense, depreciation, acquisitions)
- AAPL: 22-23/24 fields populated (1-2 NULLs)
- JPM: 14/24 fields populated (10 NULLs — genuinely not applicable for banks)

The prototype iterates all 10-K filings (including pre-XBRL ones from pre-2009, which return "No XBRL"). Should be limited to post-2009 filings.

### Task 5: This Report

---

## Coverage Comparison Matrix

### NULL Count: Current DB vs edgartools (FY 2020-2024, 24 fields per year)

| Ticker | Industry | NULLs Before | NULLs After | Filled | Regressions | Matches |
|--------|----------|:------------:|:-----------:|:------:|:-----------:|:-------:|
| MSFT   | Tech     | 35           | 10          | **30** | 5           | 75      |
| AAPL   | Tech     | 28           | 5           | **27** | 4           | 81      |
| JPM    | Bank     | 64           | 42          | **22** | 0           | 45      |
| XOM    | Energy   | 43           | 20          | **23** | 0           | 71      |
| NEE    | Utility  | 50           | 49          | 6      | 5           | 56      |
| SBUX   | Restaurant | 27         | 22          | **12** | 6           | 77      |
| MCD    | Restaurant | 39         | 30          | **10** | 1           | 77      |
| O      | REIT     | 58           | 36          | **27** | 5           | 50      |
| LMT    | Defense  | 28           | 18          | **23** | 13          | 71      |
| CRM    | SaaS     | 23           | 18          | 5      | 0           | 68      |
| **TOTAL** |       | **395**      | **250**     | **185**| 39          | 671     |

### Key Metrics

- **NULL reduction**: 36.7% (395 -> 250). Below the 50% GO threshold on raw numbers.
- **Value agreement**: 87.6% (671 matches out of 766 where both have data). Below 95% threshold.
- **Companies handled without errors**: 10/10

### Why the raw metrics undercount the improvement

1. **total_debt mismatch (17 instances)**: edgartools sums LT noncurrent + current portion, giving a more accurate total. Our DB picks a single XBRL tag. edgartools is **more correct**.

2. **CF sign convention (counted as mismatches)**: edgartools stores outflows as negative. After correcting for sign, most CF fields match perfectly.

3. **Bank total_assets (JPM: 5 mismatches)**: CompanyFacts picks consolidated holding company total assets ($4T for JPM). edgartools parses the XBRL document which sometimes reports bank entity level ($274B-$425B). Different entities in the consolidated structure.

**Adjusted metrics**: ~46% NULL reduction, ~93% value agreement.

---

## Industry-Specific Findings

### Tech (MSFT, AAPL) — Biggest Winner

MSFT and AAPL get 21-23/24 fields populated. Key new fills: COGS ($46B MSFT, $170B AAPL), gross_profit ($97B MSFT, $105B AAPL), SGA ($25B MSFT, $22B AAPL), R&D ($19B MSFT, $22B AAPL), dividends ($15B MSFT, $14B AAPL).

MSFT's 3 remaining NULLs: `interest_expense` (bundled into "Other income/expense" line — not a separate IS line item), `depreciation` (not on IS, found in CF adjustments), `acquisitions` (uses MSFT-specific XBRL tag).

### Bank (JPM) — Moderate Improvement, Fundamental Differences

- **Revenue**: edgartools gets non-interest revenue ($18-25B). Our current approach gets total revenue including interest spread ($120-178B). Both are valid; different XBRL concepts.
- **New fills**: total_debt, shareholder_equity, depreciation, acquisitions
- **Still NULL**: cash, receivables, inventory, capex, sga, rnd, ebit, gross_profit — genuinely not applicable for banks
- **No regressions**: Zero data lost

### Energy (XOM) — Solid Improvement

Revenue matches perfectly. New fills: cogs, gross_profit, dividends, acquisitions, receivables. No regressions.

### Utility (NEE) — Limited Improvement

Revenue remains NULL in both approaches — NEE uses utility-specific revenue concepts that neither approach captures. 6 new fields filled. NEE is the hardest case for any standard XBRL approach.

### REIT (O — Realty Income) — Good Improvement

27 new fields filled including revenue, interest_expense, total_debt, equity, dividends. FFO not directly available (non-GAAP metric), but building blocks are present.

### Restaurant (SBUX, MCD) — Mixed

SBUX: 12 new fills including revenue. MCD: 10 new fills, negative equity correctly reported. SGA handling varies between companies.

### Defense (LMT) — Good Coverage, Unusual IS Structure

23 new fills but 13 regressions (highest). LMT doesn't have SGA — costs go into "cost of sales." IS structure is unusual — most expenses bundled.

### SaaS (CRM) — Minor Improvement, Clean

5 new fills, 0 regressions. Most fields already populated. January fiscal year correctly handled.

---

## Regression Analysis

### Total: 39 regressions

| Field | Count | Root Cause | Fixable? |
|-------|:-----:|------------|----------|
| sga | 11 | Some companies split into non-standard components (selling + G&A); some (LMT) don't report SGA at all | Partially — sum logic helps for splits; true absence is expected |
| shares_diluted | 10 | Not always a line item on IS (sometimes only in EPS footnotes) | Yes — CompanyFacts has it as a standalone tag |
| interest_expense | 9 | MSFT et al bundle into "Other income/expense" — not a separate IS line item | Yes — CompanyFacts has it as a standalone tag |
| rnd | 5 | Not reported by some industries (defense, REIT) | Expected NULL, not a real regression |
| depreciation | 3 | IS-only search misses it; available in CF adjustments section | Yes — look in CF adjustments |
| cash | 1 | BS date column mismatch on one filing | Yes — use correct filing |

**30 of 39 fixable** with better extraction logic. 9 are expected NULLs (field doesn't exist for that industry).

---

## Edge Case Verification

| Edge Case | Result |
|-----------|--------|
| Negative equity (SBUX, MCD, LMT) | Correctly reported by both approaches. Values match. |
| Banks (JPM) | Different revenue concept (non-interest vs total). Net income, EPS, shares, CF all match. |
| REITs (O) | FFO not directly available (non-GAAP). Building blocks present. |
| Energy (XOM) | Revenue captured for all years including 2022+ (our biggest gap). |
| Utilities (NEE) | Revenue still NULL. Utility-specific taxonomy issue. |
| Total debt summing | edgartools sums LT + ST correctly. Our single-tag approach understates by 5-16%. |
| Annual vs quarterly | `get_filings(form="10-K")` correctly filters. Works. |
| Fiscal year handling | MSFT (June), AAPL (Sept), CRM (Jan), SBUX (Sept), calendar-year — all correct. |

---

## Deep Analysis: 6 Critical Questions

After the initial data comparison showed promising results, we investigated 6 critical questions before making an adoption decision.

### Q1: How would the fallback decision be made? Per-industry or universal?

**Answer: Universal, not per-industry.**

The fallback is driven by per-field NULL checks after extraction:
```
if interest_expense is NULL → query CompanyFacts for InterestExpense tag
if shares_diluted is NULL   → query CompanyFacts for WeightedAverageNumberOfDilutedSharesOutstanding
if depreciation is NULL     → query CompanyFacts for DepreciationDepletionAndAmortization
```

Regressions aren't industry-specific — MSFT (tech) and LMT (defense) both miss `interest_expense` because it's not a separate IS line item in their filings. It's about how each *company* structures its filing, not the industry.

Industry-based rules would require maintaining an industry classification system and per-industry logic branches — the same fragile domain knowledge we're trying to avoid.

**Challenge identified**: Distinguishing "field doesn't apply" (bank has no inventory) from "extraction missed it" (MSFT has interest expense but it's bundled). The fallback approach handles this implicitly — if CompanyFacts also returns NULL, the field truly doesn't exist.

### Q2: How will regressions be caught and where will they be fixed?

**Answer: Needs a dedicated regression detection strategy.**

There's no built-in safety net. Required layers:

1. **Validation test suite**: For 10 reference companies, store expected values in a fixture file (like `current_db_baseline.json`). Run integration test that compares against fixtures. Any new NULL where fixture has a value = test failure.

2. **Ingestion-time assertions**: After extracting fields for a FY, count NULLs. If a company that previously had 20/24 fields suddenly has 15/24, log a warning.

3. **Version pinning**: Pin library version exactly. Re-run comparison test suite before any upgrade.

4. **Fix strategy**: Check if field exists under different concept name (XBRL tag renaming) → update mapping. If not → add to CompanyFacts fallback list. If library bug → file issue and pin to last working version.

**Key insight**: Regressions come from two completely different sources — our mapping code vs the library's XBRL parsing. The comparison test suite isolates which layer broke.

### Q3: How will regressions in edgartools itself be caught?

**Answer: Hard problem. Library releases nearly daily.**

edgartools recently did a major remapping (2,770 tags to 234 concepts). Any release could change standard_concept names, statement type resolution, or dimensional data handling.

Required mitigations:
- Pin version aggressively (`edgartools==5.22.0`, not `>=`)
- Snapshot test suite: store exact DataFrame output for 3-5 companies as fixtures
- Monitor changelog (maintainer uses semantic commit messages)
- Wrap the library — single import point, one file to fix if API changes

**Honest assessment**: Can't fully insulate from upstream changes in a 147K-line library. The custom approach (301 lines) is fully under our control.

### Q4: Security and malicious code in edgartools?

**Source code audit findings:**

| Pattern | Location | Risk | Assessment |
|---------|----------|------|------------|
| `eval()` | `attachments.py:618` | Medium | Query filtering restricted to 3 allowed attrs + `re.match`. **Not in our code path** (we don't call `attachments.query()`). |
| `exec()` | `ai/evaluation/evaluators.py:175` | High on paper | MCP agent evaluation harness. **We wouldn't import or use this module.** |
| `__import__()` | `entity/data.py`, `thirteenf/models.py` | Low | Lazy loading of internal modules. Standard Python pattern. |

**Network surface**: Only contacts `*.sec.gov` domains. Searched all URL patterns — **zero non-SEC URLs** in entire codebase.

**File system surface**: Writes HTTP response cache to `~/.edgar/_tcache/`. Configurable via `EDGAR_LOCAL_DATA_DIR`. No code execution from cache.

**Supply chain risk**: 21 direct dependencies, ~49 total packages. Any could be compromised via PyPI supply chain attack. Mitigation: `pip install --require-hashes` with lockfile, periodic `pip-audit`.

### Q5: Debuggability — can we debug edgartools when things go wrong?

**What's debuggable:**
- XBRL parsing code (`edgar/xbrl/`) is ~30K lines of pure Python. No compiled extensions, no obfuscation.
- `to_dataframe()` returns standard pandas DataFrame — fully inspectable.
- Uses `lxml` for XML parsing (industry standard).
- Debugging path: `filing.xbrl()` → `xbrl.statements` → `statement.to_dataframe()` → inspect rows.
- Raw facts accessible via `xbrl.facts`.

**What's hard:**
- `standard_concept` mapping lives in `xbrl/standardization/` (~2,500 lines + data files). If a field maps wrong, need to trace through standardization pipeline.
- Statement resolver decides what counts as "Income Statement" vs "Comprehensive Income." Misclassification = wrong statement entirely.
- **147K lines total** vs our 301 lines. Debuggable surface area is ~500x larger.

### Q6: Dependency headaches — what does edgartools bring?

**edgartools direct dependencies (21 packages):**

| Package | Nature | Needed for our use case? | Risk |
|---------|--------|--------------------------|------|
| **pyarrow** (23.0.1) | **150MB compiled C++** | No (Parquet for standardization data) | Version conflicts, build failures |
| **RapidFuzz** (3.14.3) | Compiled C extension | No (fuzzy string matching) | Low |
| **orjson** (3.11.7) | Compiled Rust extension | No (fast JSON) | Low |
| **rich** (14.3.3) | Pure Python | No (pretty-printing) | Low |
| **pydantic** (2.12.5) | Already in project | Yes | **Version alignment needed** |
| **pandas** (2.3.3) | Already in project | Yes | Already have it |
| **lxml** (6.0.2) | Already in project | Yes | Already have it |
| **httpx** (0.28.1) | Already in project | Yes | Already have it |
| **beautifulsoup4** | Already in project | Partial | Already have it |
| **rank-bm25** | Pure Python + numpy | No (text search) | Unnecessary |
| **textdistance** | Pure Python | No (string distance) | Unnecessary |
| **Unidecode** | Pure Python | No (Unicode) | Unnecessary |
| **humanize** | Pure Python | No (formatting) | Unnecessary |
| **tqdm** | Pure Python | No (progress bars) | Unnecessary |
| **tabulate** | Pure Python | No (table formatting) | Unnecessary |
| **stamina/tenacity** | Pure Python | No (retry logic) | Low |
| **nest-asyncio** | Pure Python | No | **Monkey-patches asyncio event loop — can cause subtle FastAPI issues** |
| **truststore** | Pure Python | No (system certs) | Low |
| **httpxthrottlecache** | Pure Python | No (HTTP caching) | Adds complexity to httpx |
| **Jinja2** | Already via FastAPI | Partial | Already have it |
| **filelock** | Pure Python | No (cache locking) | Low |

**Summary**: 49 total packages vs 23 current. 3 heavy compiled packages (pyarrow, RapidFuzz, orjson). ~10 packages serve features we don't use. `nest-asyncio` is the sneakiest risk (monkey-patches asyncio).

**Comparison**: Custom approach dependency cost = **0 new packages**. Our `sec.py` uses only httpx (already in requirements) and stdlib.

---

## Three Options Considered

### Option A: Adopt edgartools as a dependency

- 49 packages, 147K lines upstream, eval()/exec() in unused paths
- Coverage: best (21-23/24 fields for tech companies)
- Debuggability: source available but 500x larger surface
- **Rejected**: Too much unneeded complexity, dependency burden, and maintenance risk for what we actually use (5% of the library)

### Option B: Take the mapping data, write our own code (SELECTED)

The most valuable artifact from edgartools is not code but **data**:

- `concept_mappings.json` (12KB): 100 standard financial concepts, each with ordered XBRL tag fallback lists. Better version of our `IS_TAGS`/`BS_TAGS`/`CF_TAGS`.
- `gaap_mappings.json` (4.4MB): 2,921 XBRL concepts mapped to standard names with confidence scores, occurrence rates, from analyzing 32,240 filings. This is "years of XBRL learning" in a JSON file.

**What we'd do**: Copy the mapping data (MIT licensed), enhance our existing `sec.py` with better tag lists derived from it, add ~50-100 lines for SGA splitting, total_debt summing, and CF-to-IS depreciation fallback.

- Zero new dependencies
- Full ownership of ~400 lines of code
- 80%+ of the coverage improvement
- Fully debuggable

### Option C: Extract just the XBRL parser module

Vendor `edgar/xbrl/` (~30K lines, 48 files) with minimal deps (lxml, pandas — already in project).

**Rejected**: 30K lines is still a lot to own. The XBRL parser's value = XML parsing (lxml does this) + concept standardization (which is just the JSON data). Don't need 30K lines of Python to look up a tag in a JSON file.

---

## Decision: Option B — Take the Data, Not the Code

### Rationale

1. **The spike's most valuable output is mapping data, not code.** The `concept_mappings.json` and `gaap_mappings.json` files encode which XBRL tags map to which financial concepts across 32K filings. The *data* is the valuable part, not the 147K lines of code.

2. **Our current architecture is the right approach** — query CompanyFacts, look up tags, extract values. It just has too-short tag fallback lists. Enriching `IS_TAGS`/`BS_TAGS`/`CF_TAGS` with edgartools' mapping data gets 80% of the improvement.

3. **The remaining 20% gap** (SGA splitting, total_debt summing, depreciation from CF) is ~50 lines of targeted logic.

4. **Zero new dependencies, zero new attack surface, zero upstream maintainer risk, full debuggability** in 350-400 lines of our own code.

5. **Migration path stays open.** If needs outgrow the custom approach (segment/geography parsing, IFRS, inline XBRL), we can add the library later.

### What Option B loses vs the library

The one thing edgartools does that we can't easily replicate: it parses XBRL document structure (presentation linkbase, calculation linkbase) which tells it how line items relate to each other (e.g., Selling+Marketing and G&A sum to SGA). Our CompanyFacts approach doesn't have structural info. But for 26 fields, we can hardcode those relationships.

---

## Next Steps

1. **Extract mapping data**: Copy `concept_mappings.json` into the project. Parse `gaap_mappings.json` to identify additional XBRL tags for our 26 fields.

2. **Enhance `sec.py` tag lists**: Expand `IS_TAGS`, `BS_TAGS`, `CF_TAGS` with tags discovered from the mapping data and this spike's debugging sessions.

3. **Add targeted extraction logic**:
   - SGA: try combined tag first, then sum `SellingAndMarketingExpense` + `GeneralAndAdministrativeExpense`
   - total_debt: sum `LongTermDebtNoncurrent` + `LongTermDebtCurrent`
   - depreciation: fall back to CF adjustment section tags
   - dividends: add `PaymentsOfDividendsCommonStock` tag

4. **Build regression test suite**: Freeze expected values for 10 reference companies as test fixtures.

5. **Validate**: Run comparison against baseline to confirm coverage improvement.

---

## Appendix

### Spike Scripts

| File | Purpose |
|------|---------|
| `backend/scripts/spike_edgartools_explore.py` | Task 1: Initial API exploration |
| `backend/scripts/spike_edgartools_explore2.py` | Task 1b: Deep dive into statement objects, DataFrame structure |
| `backend/scripts/spike_edgartools_multiyear.py` | Task 1c: Multi-year data extraction from individual filings |
| `backend/scripts/spike_edgartools_compare.py` | Task 2+3: Full 10-company x 26-field comparison with edge cases |
| `backend/scripts/spike_edgartools_debug.py` | Debug: BS regressions, CF sign conventions |
| `backend/scripts/spike_edgartools_debug_regressions.py` | Debug: Interest expense, shares_diluted, SGA regressions |
| `backend/scripts/spike_edgartools_prototype.py` | Task 4: Integration prototype (`ingest_via_edgartools()`) |
| `backend/scripts/spike_edgartools_results.json` | Raw comparison results |
| `backend/scripts/current_db_baseline.json` | Current DB values for comparison |

### edgartools Mapping Data (the real value)

| File | Size | Content |
|------|------|---------|
| `concept_mappings.json` | 12KB | 100 standard concepts with XBRL tag fallback lists |
| `gaap_mappings.json` | 4.4MB | 2,921 XBRL concepts with standard names, confidence scores, occurrence rates, industry overrides (from 32,240 filings) |
| `display_names.json` | 13KB | Human-readable labels for XBRL concepts |
| `section_membership.json` | 8.9KB | Statement section classification for concepts |

### Library Metadata

- **Version**: 5.22.0 (latest as of 2026-03-09)
- **License**: MIT
- **Maintainer**: Dwight Gunning (single person, AI-assisted development with Claude)
- **Stars**: 1,800 / Forks: 313
- **Release cadence**: Nearly daily
- **Open issues**: 16 (none critical)
- **Total codebase**: ~147K lines Python
- **XBRL module**: ~30K lines (48 files)
- **Direct dependencies**: 21 packages
- **Total transitive dependencies**: 49 packages
- **Python support**: 3.10 - 3.14
