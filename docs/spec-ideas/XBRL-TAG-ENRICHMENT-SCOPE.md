# XBRL Tag Enrichment — Branch Scope

**Branch:** `rahul/xbrl-tag-enrichment-phase1b`
**Goal:** Fix XBRL tag resolution so the 25-company Phase 1B pilot cohort has
complete-as-possible financial data before the agent pilot runs.
**Predecessor:** Phase 1B preflight run (2026-05-08) — all 25 companies ingested,
coverage gaps identified per company.

---

## Context

The Common Investor platform ingests SEC EDGAR XBRL data via `backend/app/ingest/sec.py`.
It stores income statement (IS), balance sheet (BS), and cash flow (CF) fields into
PostgreSQL tables (`statement_is`, `statement_bs`, `statement_cf`) via filing records.

Field resolution works by trying an ordered list of XBRL tag fallbacks defined in
`IS_TAGS`, `BS_TAGS`, and `CF_TAGS` dicts in `ingest/sec.py`. The function
`_pick_first_units(facts, tags)` returns the first tag in the list that has annual
10-K FY data in the company's EDGAR CompanyFacts JSON.

The preflight run revealed three distinct classes of gaps. **Only the first two are
fixable.** The third is structural (the concept genuinely doesn't apply to that business).

---

## Problem 1: Stale Tag Wins the Race

**Affected:** MA (revenue, net_income), XOM (revenue, ebit), LMT (revenue, cogs, sga)

**Root cause:** `_pick_first_units()` returns the first tag in the fallback list that has
*any* annual FY entry in the EDGAR data. For MA and XOM, the first-match tag
(`RevenueFromContractWithCustomerExcludingAssessedTax`) has stale 10-K entries only
through FY2021 — the company stopped using that tag after adopting a revised disclosure
format. The function finds the tag, returns it, and the ingest writes NULL because no
recent-year data matches. Meanwhile, `Revenues` (which has data through FY2025) is
third in the fallback list but never reached.

LMT is the same pattern for revenue and cogs.

**Fix:** Modify `_pick_first_units()` to require that the matched tag has at least one
annual 10-K FY entry within the last 3 fiscal years (i.e., `max(fy) >= current_year - 3`).
If the first-matched tag only has stale data, continue down the fallback list.

**Evidence:**
- MA `RevenueFromContractWithCustomerExcludingAssessedTax`: last FY entry = FY2021
- MA `Revenues`: has FY2022, FY2023, FY2024, FY2025
- XOM same pattern
- LMT `Revenues` FY2025 = $75.0B — clearly present, not being picked

---

## Problem 2: Gross Profit Not Tagged, But Computable

**Affected:** AMZN (gross_profit), NFLX (gross_profit), LLY (gross_profit)

**Root cause:** These companies report `revenue` and `cogs` in their XBRL filings but
do not tag a separate `GrossProfit` line item — they don't report it as a distinct line
in their P&L. Our ingest only populates `gross_profit` if the `GrossProfit` XBRL tag
exists. Since it doesn't, the field is NULL even though it's arithmetically derivable.

Amazon FY2025: revenue = $716.9B, cogs = $356.4B — gross profit is $360.5B, computable
but absent as a tag.

**Fix:** After the `_pick_first_units()` pass for all IS fields, add a fallback
computation step: if `gross_profit` is NULL but both `revenue` and `cogs` are populated
for a given fiscal year row, compute `gross_profit = revenue - cogs` and write it.
This mirrors the existing pattern for SGA summing (`_resolve_sga_sum()`) and total
debt summing (`_sum_annual_values()`) already in the codebase.

---

## Problem 3: Structural Gaps — Accept as NULL (No Fix Needed)

These are correct NULLs. The concept does not exist in the business model.

| Ticker | Field | Why NULL is correct |
|--------|-------|---------------------|
| MA | cogs, gross_profit | Payment network — no cost of goods. Mastercard runs a network, not a factory. No COGS concept in their P&L. |
| MCD | cogs, gross_profit | Franchise model — revenue is franchise fees + rent. No COGS line. Costs are "franchised restaurants costs" under a different taxonomy. |
| NEE | cogs, gross_profit | Regulated utility — costs are fuel + purchased power, tagged under utility-specific taxonomy (`UtilitiesOperatingExpenseFuelAndPurchasedPower`). Standard COGS tags don't match. Not worth adding — low analytical value. |
| O | Most IS fields | REIT — income statement structure is fundamentally different. Revenue recognition changed post-2019. FFO, AFFO are the meaningful metrics, not revenue/COGS. The agent_bundle `industry_notes` already warns the agent about this. |
| O | buybacks | REITs are legally required to distribute 90%+ of income as dividends — structural prohibition on buybacks. Correct NULL. |
| NEE | buybacks, acquisitions | Utility capital deployment goes into regulated rate base, not buybacks or acquisitions in the traditional sense. |

These NULLs should be documented in `industry_expectations.md` in
`.claude/memory/` so the agent knows they are expected, not missing.

---

## Problem 4: Missing Tags for Specific Archetypes

**Affected:** NEE (interest_expense), XOM (ebit)

**Root cause:**
- NEE uses `InterestExpenseLongTermDebt` or `InterestCostsIncurred` rather than the
  standard `InterestExpense` tag. Utility financing is structured differently (rate
  base financing, long-term bonds with capitalized interest).
- XOM has no `OperatingIncomeLoss` tag (what we use for `ebit`). Their P&L goes
  revenues → total costs → pre-tax income. Operating income must be inferred from
  `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`
  or reconstructed.

**Fix:** Add the following to the fallback lists in `IS_TAGS`:
- `interest_expense`: add `InterestExpenseLongTermDebt`, `InterestCostsIncurred`,
  `InterestAndFeeExpense` (for banks/utilities) near the end of the fallback list
- `ebit`: add `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`
  as a last-resort fallback (pre-tax income as a proxy when operating income isn't tagged)

---

## Files to Change

| File | Change |
|------|--------|
| `backend/app/ingest/sec.py` | (1) `_pick_first_units()`: add recency filter; (2) post-pass gross_profit computation; (3) extend `IS_TAGS` fallback lists for `interest_expense` and `ebit` |
| `docs/QUANTITATIVE_GAP_ANALYSIS_V2.md` | Update GAP-IND-3, add GAP-XBRL-1 and GAP-XBRL-2 sections |
| `.claude/memory/industry_expectations.md` | Add entries for structural NULLs (MA, MCD, NEE, O) |

---

## Out of Scope for This Branch

- Full REIT taxonomy (FFO, AFFO, NOI) — Phase 2
- Bank-specific tags (NII, NIM, PCR, CET1) — Phase 2
- SBC ingestion — Phase 2
- Goodwill/intangibles — Phase 2
- Quarterly data (10-Q) — Phase 2
- Any changes to `metrics/compute.py`, `valuation/`, or `nlp/` — not this branch

---

## Verification

After fixing, re-run the preflight to confirm improvement:

```bash
# Inside the api container
docker exec common-investor-api-1 \
  python -m scripts.workflows.phase1b_preflight --skip-ingest \
  --output /tmp/post_fix_preflight.json
```

Expected outcomes:
- MA: revenue, net_income recover → coverage ~75%+
- XOM: revenue, ebit recover → coverage ~75%+
- LMT: revenue, cogs, sga recover → coverage ~87%+
- AMZN: gross_profit computed → coverage ~71%+
- NFLX: gross_profit computed → coverage ~83%+
- LLY: gross_profit computed → coverage ~75%+
- NEE: interest_expense recovers → coverage ~71%+
- O: no change expected (structural) — stays ~50%

Re-ingest affected tickers after the fix to pick up new tag resolutions:
```bash
for t in MA XOM LMT AMZN NFLX LLY NEE; do
  curl -X POST http://localhost:8080/api/v1/company/$t/ingest
  sleep 5
done
```

---

## How to Resume Phase 1B Pilot After This Branch Merges

1. Merge this branch to main
2. Re-ingest the 7 affected tickers (above)
3. Re-run preflight (`--skip-ingest`) to confirm coverage improved
4. Run pilot runner with the 20 new tickers:

```bash
docker exec common-investor-api-1 \
  python -m app.nlp.research_agent.harness.pilot_runner \
  --tickers GOOGL CAT JNJ UNH KO PG COST HD BRK-B MA XOM NEE O NVDA CRM AMZN LMT LLY NFLX MCD
```

---

**Created:** 2026-05-08
**Author:** Rahul + Claude (phase1B-25-company-pilot session)
