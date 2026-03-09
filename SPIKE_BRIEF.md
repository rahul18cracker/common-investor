# Spike: Evaluate `edgartools` as XBRL Parsing Replacement

## Objective

Determine whether the `edgartools` library (https://github.com/dgunning/edgartools) can replace our custom XBRL tag mapping in `backend/app/ingest/sec.py`, improving data coverage across industries while reducing maintenance burden.

## Background

Our current approach uses hand-curated XBRL tag fallback lists (`IS_TAGS`, `BS_TAGS`, `CF_TAGS` — ~40 tags total) with a `_pick_first_units()` function that searches SEC CompanyFacts JSON for the first matching tag. This has proven fragile:

- Companies that switch XBRL tags over time get NULLs (bug we just fixed in `_pick_first_units`)
- Each new industry requires discovering and adding non-standard tags
- Banks, REITs, energy, and utilities use significantly different XBRL taxonomies
- We're maintaining domain knowledge that the XBRL community has already solved

## Current Data Quality Problems (what the spike must address)

Our current ingestion produces these NULL fields for recent fiscal years (2020+):

| Company | Industry | Critical NULLs |
|---------|----------|---------------|
| MSFT | Tech | cogs, gross_profit, sga, rnd, depreciation, dividends, acquisitions |
| AAPL | Tech | cogs, gross_profit, sga, rnd, depreciation |
| JPM | Bank | cogs, gross_profit, sga, rnd, depreciation, ebit, cash, receivables, inventory, total_debt, equity, capex |
| XOM | Energy | revenue(!!), cogs, gross_profit, ebit, shares, inventory, total_debt, dividends |
| NEE | Utility | revenue(!!), cogs, gross_profit, sga, rnd, interest_exp, receivables, capex, buybacks |
| SBUX | Restaurant | revenue, cogs, gross_profit, rnd, cash |
| MCD | Restaurant | cogs, gross_profit, rnd, receivables, total_liab, dividends |
| O | REIT | revenue, cogs, gross_profit, rnd, ebit, interest_exp, receivables, inventory, total_debt, capex, buybacks, dividends |
| LMT | Defense | revenue, cogs, sga, capex, dividends |
| CRM | SaaS | interest_exp, inventory, equity |

Note: Some NULLs are expected (banks don't have inventory, SaaS doesn't have inventory). The critical failures are: MSFT missing COGS/gross_profit, XOM/NEE/SBUX missing revenue, JPM missing virtually everything.

## What We Need From the Library

### Income Statement fields (table: `statement_is`)
| DB Column | Description | XBRL tags we currently try |
|-----------|-------------|---------------------------|
| revenue | Total revenue | RevenueFromContractWithCustomerExcludingAssessedTax, SalesRevenueNet, Revenues, +4 more |
| cogs | Cost of goods sold | CostOfGoodsAndServicesSold, CostOfRevenue, CostOfGoodsSold, CostOfServices |
| gross_profit | Gross profit | GrossProfit |
| sga | SG&A expense | SellingGeneralAndAdministrativeExpense, SellingAndMarketingExpense, GeneralAndAdministrativeExpense |
| rnd | R&D expense | ResearchAndDevelopmentExpense |
| depreciation | D&A | DepreciationDepletionAndAmortization, DepreciationAndAmortization, Depreciation |
| ebit | Operating income | OperatingIncomeLoss |
| interest_expense | Interest expense | InterestExpense |
| taxes | Income tax | IncomeTaxExpenseBenefit |
| net_income | Net income | NetIncomeLoss |
| eps_diluted | Diluted EPS | EarningsPerShareDiluted, EarningsPerShareBasic |
| shares_diluted | Diluted shares | WeightedAverageNumberOfDilutedSharesOutstanding, WeightedAverageNumberOfSharesOutstandingBasic |

### Balance Sheet fields (table: `statement_bs`)
| DB Column | Description |
|-----------|-------------|
| cash | Cash and equivalents |
| receivables | Net receivables |
| inventory | Net inventory |
| total_assets | Total assets |
| total_liabilities | Total liabilities |
| total_debt | Total debt (LT + ST) — currently picks first match instead of summing |
| shareholder_equity | Total stockholders equity |

### Cash Flow fields (table: `statement_cf`)
| DB Column | Description |
|-----------|-------------|
| cfo | Net cash from operations |
| capex | Capital expenditures |
| buybacks | Stock repurchases |
| dividends | Dividend payments |
| acquisitions | Acquisition payments |

## Spike Tasks

### Task 1: Install and Basic Exploration
```bash
cd backend
pip install edgartools
```
Write a script `backend/scripts/spike_edgartools_explore.py` that:
1. Fetches MSFT financials via `edgartools`
2. Prints what an income statement, balance sheet, and cash flow look like
3. Documents the data structure (DataFrame columns, index, etc.)
4. Check if it uses the same CompanyFacts API or a different EDGAR endpoint

### Task 2: Field Mapping Comparison
Write a script `backend/scripts/spike_edgartools_compare.py` that for each of these 10 tickers:
**MSFT, AAPL, JPM, XOM, NEE, SBUX, MCD, O, LMT, CRM**

1. Fetches financial statements via `edgartools` for FY 2020-2024
2. Attempts to extract ALL 26 fields listed above
3. Prints a comparison table showing:
   - Field name
   - Our current value (NULL or actual number from our DB)
   - `edgartools` value (NULL or actual number)
   - Match/Mismatch/New (edgartools has data we don't)

The key questions to answer per company:
- **Coverage improvement**: How many of our current NULLs does edgartools fill?
- **Value agreement**: Where both have data, do values match (within 1% tolerance)?
- **New NULLs**: Does edgartools miss anything we currently have?

### Task 3: Edge Case Verification
For each company, specifically verify:

1. **Negative equity companies (SBUX, MCD, LMT)**: Does edgartools report negative shareholder_equity? Our current data sometimes misses equity for these.
2. **Banks (JPM)**: Banks don't use standard revenue/COGS. Does edgartools provide any useful financial metrics for banks, or does it also return NULLs?
3. **REITs (O)**: REITs use FFO instead of net income. Does edgartools expose FFO?
4. **Energy (XOM)**: Our current ingestion misses XOM revenue entirely for 2022+. Does edgartools get it?
5. **Utilities (NEE)**: Similar revenue gap. Does edgartools handle regulated utility accounting?
6. **Total debt**: Our current approach picks the FIRST matching debt tag. Does edgartools give us a proper total debt figure (LT + ST combined)?
7. **Annual vs Quarterly**: We only want annual (10-K/20-F) data. Can edgartools filter by form type?
8. **Fiscal year handling**: Companies like MSFT (June FY), AAPL (Sept FY), COST (Aug FY) have non-calendar fiscal years. Does edgartools correctly report fiscal year?

### Task 4: Integration Feasibility Assessment
Write `backend/scripts/spike_edgartools_prototype.py` — a minimal prototype of what a new `ingest_via_edgartools()` function would look like:
1. Takes a ticker
2. Fetches all annual financial data via edgartools
3. Maps to our DB column names
4. Returns the same data structure as our current `ingest_companyfacts_richer_by_ticker()`

This doesn't need to write to DB — just return dicts showing what would be inserted.

### Task 5: Write Assessment Report
Create `docs/SPIKE_EDGARTOOLS_REPORT.md` with:
1. **Coverage comparison matrix**: 10 companies x 26 fields, showing current vs edgartools
2. **Summary statistics**: % NULL reduction, % value agreement
3. **Industry-specific findings**: Which industries benefit most
4. **Risk assessment**: What we'd lose, what could break
5. **Recommendation**: Replace / Hybrid / Keep current, with reasoning
6. **Migration effort estimate**: What code changes would be needed

## Success Criteria

The spike is a **GO** for adoption if:
- edgartools fills >50% of our current NULLs across the 10 test companies
- Value agreement is >95% where both have data
- It handles at least 8 of the 10 companies without errors
- Annual/fiscal year filtering works correctly
- The library is actively maintained (commits in last 3 months)

The spike is a **NO-GO** if:
- It introduces new NULLs for fields we currently have
- It can't filter to annual data only
- Banks/REITs/energy are just as bad as our current approach
- The library is abandoned or unstable

## Reference: Our Current Ingestion Architecture

The file to potentially replace is `backend/app/ingest/sec.py`. Key functions:
- `ticker_map()` → CIK lookup
- `company_facts(cik)` → raw CompanyFacts JSON from SEC EDGAR
- `_pick_first_units(facts, tag_list)` → finds first XBRL tag with 10-K data
- `_annual_value(units, unit_key, fy)` → extracts value for a specific fiscal year
- `_insert_statement(filing_id, fy, stmt_type, units_cache)` → writes to DB
- `ingest_companyfacts_richer_by_ticker(ticker)` → orchestrator

The DB schema is in `backend/app/db/models.py` — tables: company, filing, statement_is, statement_bs, statement_cf.

## Environment Notes

- Python 3.11 in Docker container
- You can run scripts locally with `pip install edgartools` in a venv, no need for Docker
- SEC EDGAR rate limit: 10 req/sec, must set User-Agent header
- Set `SEC_USER_AGENT` env var or the library may have its own config

## How to Run This Spike

```bash
# From the worktree root
cd backend
python -m venv .venv-spike
source .venv-spike/bin/activate
pip install edgartools

# Run exploration
python scripts/spike_edgartools_explore.py

# Run comparison (this will take a few minutes due to SEC rate limiting)
python scripts/spike_edgartools_compare.py

# Run prototype
python scripts/spike_edgartools_prototype.py
```
