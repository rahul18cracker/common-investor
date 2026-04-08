# Tag Regressions Log

Past incidents where XBRL tag changes caused data regressions, and how they were resolved.
Claude commands read this file to recognize known regression patterns.

## 2026-04 — edgartools Spike Regressions (39 total, 30 fixable)

During the edgartools comparison spike, we found 39 regressions when switching
to edgartools extraction. Root causes:

- **Sign conventions**: edgartools returns CapEx/buybacks/dividends as negative (cash outflow).
  Our DB stores them as positive. Need sign normalization if ever adopting edgartools.
- **Tag priority differences**: edgartools sometimes picks a different XBRL tag than our fallback
  list (e.g., `CostOfGoodsAndServicesSold` vs `CostOfRevenue`). Values differ by 5-15%.
- **Resolution**: Chose Option B (take mapping data, not library). Extracted tag lists from
  `concept_mappings.json` and enriched our own fallback lists.

## 2026-04 — _pick_first_units() Regression

- **Problem**: `_pick_first_units()` was picking the first tag that existed in CompanyFacts,
  even if it only had quarterly (10-Q) data. This caused NULL annual values downstream.
- **Fix**: Added check for at least one 10-K/20-F entry before accepting a tag's units.
- **Affected**: Companies that switched XBRL tags over time (e.g., MSFT CostOfRevenue).

## 2026-04 — SGA Splitting (MSFT pattern)

- **Problem**: MSFT reports SellingAndMarketingExpense + GeneralAndAdministrativeExpense
  separately, not as combined SellingGeneralAndAdministrativeExpense. SGA was NULL.
- **Fix**: Added `SGA_COMPONENT_TAGS` summing logic in `_sum_annual_values()`.
- **Watch for**: Other companies with split SGA — the current groups cover 3 variants.

## 2026-04 — Total Debt Missing

- **Problem**: Some companies don't report combined `LongTermDebt`. They report
  `LongTermDebtNoncurrent` + `LongTermDebtCurrent` separately.
- **Fix**: Added `DEBT_COMPONENT_TAGS` summing logic. Tries 3 group variants.
- **Watch for**: Companies that use `DebtInstrument` or `NotesPayable` tags — not covered yet.

## 2026-04 — Depreciation Not on Income Statement

- **Problem**: Some companies report depreciation only in the cash flow statement
  (as a non-cash adjustment), not as a separate line on the IS.
- **Fix**: Added `DEPRECIATION_CF_TAGS` fallback — if IS depreciation is NULL,
  look in CF adjustment tags.
