"""Task 2+3: Compare edgartools vs current DB for 10 tickers, including edge cases.

Key design decisions:
- Each 10-K filing is processed independently. We take the LATEST period date from each filing
  as the "primary" year for that filing (the most current data).
- For IS/CF, filings contain 3 years; for BS, only 2. So BS data for a given FY
  must come from the filing filed for that FY (or the next year's filing).
- CF outflows are stored as negative in edgartools but positive in our DB.
  We use abs() for CF comparison fields (capex, buybacks, dividends, acquisitions).
- SGA may be reported as one line or split into Selling+Marketing and G&A.
"""

import json
import math
import time
import traceback
from pathlib import Path

import pandas as pd
from edgar import Company, set_identity

set_identity("CommonInvestor/1.0 spike@example.com")

TICKERS = ["MSFT", "AAPL", "JPM", "XOM", "NEE", "SBUX", "MCD", "O", "LMT", "CRM"]
FY_RANGE = range(2020, 2025)

baseline_path = Path(__file__).parent / "current_db_baseline.json"
with open(baseline_path) as f:
    BASELINE = json.load(f)

# All 26 fields in order
ALL_FIELDS = [
    "revenue", "cogs", "gross_profit", "sga", "rnd", "depreciation",
    "ebit", "interest_expense", "taxes", "net_income", "eps_diluted", "shares_diluted",
    "cash", "receivables", "inventory", "total_assets", "total_liabilities",
    "total_debt", "shareholder_equity",
    "cfo", "capex", "buybacks", "dividends", "acquisitions",
]

# Fields where edgartools stores as negative (outflow) but our DB stores positive
ABS_FIELDS = {"capex", "buybacks", "dividends", "acquisitions", "taxes"}


def get_consolidated(df):
    """Filter dataframe to consolidated (non-dimensional, non-abstract) rows."""
    if df is None or df.empty:
        return pd.DataFrame()
    return df[(df['dimension'] == False) & (df['abstract'] == False)].copy()


def has_concept_col(df):
    """Check if a DataFrame has the expected edgartools columns."""
    return not df.empty and 'concept' in df.columns


def find_val(cons_df, date_col, concepts=None, standard_concepts=None):
    """Find a value in a consolidated statement df by concept or standard_concept."""
    if not has_concept_col(cons_df) or date_col not in cons_df.columns:
        return None

    # Try standard_concept first (more reliable across companies)
    for sc in (standard_concepts or []):
        matches = cons_df[cons_df['standard_concept'] == sc]
        if not matches.empty:
            val = matches.iloc[0][date_col]
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                return float(val)

    # Try exact concept
    for c in (concepts or []):
        matches = cons_df[cons_df['concept'] == c]
        if not matches.empty:
            val = matches.iloc[0][date_col]
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                return float(val)

    return None


def sum_vals(cons_df, date_col, concept_groups):
    """Sum multiple concept values (e.g., SGA = selling + G&A, debt = LT + ST)."""
    if not has_concept_col(cons_df) or date_col not in cons_df.columns:
        return None
    for group in concept_groups:
        total = 0.0
        all_found = True
        for concept in group:
            matches = cons_df[cons_df['concept'] == concept]
            if not matches.empty:
                val = matches.iloc[0][date_col]
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
                    total += float(val)
                else:
                    all_found = False
                    break
            else:
                all_found = False
                break
        if all_found:
            return total
    return None


def extract_all_fields(inc_cons, bs_cons, cf_cons, date_col):
    """Extract all 26 fields from consolidated statement dataframes for a given date column."""
    data = {}

    # --- Income Statement ---
    data["revenue"] = find_val(inc_cons, date_col,
        standard_concepts=["Revenue"],
        concepts=["us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
                  "us-gaap_Revenues", "us-gaap_SalesRevenueNet",
                  "us-gaap_RevenueFromContractWithCustomerIncludingAssessedTax",
                  "us-gaap_RevenuesNetOfInterestExpense",
                  "us-gaap_InterestAndDividendIncomeOperating"])

    data["cogs"] = find_val(inc_cons, date_col,
        standard_concepts=["CostOfGoodsAndServicesSold"],
        concepts=["us-gaap_CostOfGoodsAndServicesSold", "us-gaap_CostOfRevenue",
                  "us-gaap_CostOfGoodsSold", "us-gaap_CostOfServices"])

    data["gross_profit"] = find_val(inc_cons, date_col,
        standard_concepts=["GrossProfit"],
        concepts=["us-gaap_GrossProfit"])

    # SGA: try combined first, then sum of split components
    sga = find_val(inc_cons, date_col,
        concepts=["us-gaap_SellingGeneralAndAdministrativeExpense"])
    if sga is None:
        sga = sum_vals(inc_cons, date_col, [
            ("us-gaap_SellingAndMarketingExpense", "us-gaap_GeneralAndAdministrativeExpense"),
        ])
    data["sga"] = sga

    data["rnd"] = find_val(inc_cons, date_col,
        standard_concepts=["ResearchAndDevelopementExpenses"],
        concepts=["us-gaap_ResearchAndDevelopmentExpense"])

    data["depreciation"] = find_val(inc_cons, date_col,
        concepts=["us-gaap_DepreciationDepletionAndAmortization",
                  "us-gaap_DepreciationAndAmortization", "us-gaap_Depreciation",
                  "us-gaap_DepreciationAmortizationAndAccretionNet"])
    # Depreciation often only appears in CF adjustments, not IS
    if data["depreciation"] is None:
        data["depreciation"] = find_val(cf_cons, date_col,
            concepts=["us-gaap_DepreciationDepletionAndAmortization",
                      "us-gaap_DepreciationAndAmortization",
                      "us-gaap_Depreciation",
                      "us-gaap_DepreciationAmortizationAndAccretionNet"])

    data["ebit"] = find_val(inc_cons, date_col,
        standard_concepts=["OperatingIncomeLoss"],
        concepts=["us-gaap_OperatingIncomeLoss"])

    data["interest_expense"] = find_val(inc_cons, date_col,
        standard_concepts=["InterestExpense"],
        concepts=["us-gaap_InterestExpense", "us-gaap_InterestExpenseDebt",
                  "us-gaap_InterestIncomeExpenseNet"])

    data["taxes"] = find_val(inc_cons, date_col,
        standard_concepts=["IncomeTaxes"],
        concepts=["us-gaap_IncomeTaxExpenseBenefit"])

    data["net_income"] = find_val(inc_cons, date_col,
        standard_concepts=["NetIncome"],
        concepts=["us-gaap_NetIncomeLoss"])

    data["eps_diluted"] = find_val(inc_cons, date_col,
        concepts=["us-gaap_EarningsPerShareDiluted", "us-gaap_EarningsPerShareBasic"])

    data["shares_diluted"] = find_val(inc_cons, date_col,
        standard_concepts=["SharesFullyDilutedAverage"],
        concepts=["us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
                  "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic"])

    # --- Balance Sheet ---
    data["cash"] = find_val(bs_cons, date_col,
        concepts=["us-gaap_CashAndCashEquivalentsAtCarryingValue",
                  "us-gaap_CashCashEquivalentsAndShortTermInvestments"])

    data["receivables"] = find_val(bs_cons, date_col,
        concepts=["us-gaap_AccountsReceivableNetCurrent", "us-gaap_ReceivablesNetCurrent",
                  "us-gaap_AccountsReceivableNet"])

    data["inventory"] = find_val(bs_cons, date_col,
        standard_concepts=["Inventories", "Inventory"],
        concepts=["us-gaap_InventoryNet"])

    data["total_assets"] = find_val(bs_cons, date_col,
        standard_concepts=["Assets"],
        concepts=["us-gaap_Assets"])

    data["total_liabilities"] = find_val(bs_cons, date_col,
        standard_concepts=["Liabilities"],
        concepts=["us-gaap_Liabilities"])

    # Total debt: try combined, then sum LT noncurrent + current portion
    td = find_val(bs_cons, date_col,
        concepts=["us-gaap_LongTermDebt"])
    if td is None:
        td = sum_vals(bs_cons, date_col, [
            ("us-gaap_LongTermDebtNoncurrent", "us-gaap_LongTermDebtCurrent"),
            ("us-gaap_LongTermDebtNoncurrent", "us-gaap_ShortTermBorrowings"),
        ])
    if td is None:
        td = find_val(bs_cons, date_col,
            standard_concepts=["LongTermDebt"],
            concepts=["us-gaap_LongTermDebtNoncurrent", "us-gaap_DebtCurrent"])
    data["total_debt"] = td

    data["shareholder_equity"] = find_val(bs_cons, date_col,
        standard_concepts=["Equity", "StockholdersEquity", "AllEquityBalance"],
        concepts=["us-gaap_StockholdersEquity",
                  "us-gaap_StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"])

    # --- Cash Flow ---
    data["cfo"] = find_val(cf_cons, date_col,
        standard_concepts=["OperatingCashFlow"],
        concepts=["us-gaap_NetCashProvidedByUsedInOperatingActivities",
                  "us-gaap_NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"])

    data["capex"] = find_val(cf_cons, date_col,
        standard_concepts=["CapitalExpenditure"],
        concepts=["us-gaap_PaymentsToAcquirePropertyPlantAndEquipment",
                  "us-gaap_CapitalExpenditures", "us-gaap_PaymentsToAcquireProductiveAssets"])

    data["buybacks"] = find_val(cf_cons, date_col,
        concepts=["us-gaap_PaymentsForRepurchaseOfCommonStock",
                  "us-gaap_PaymentsForRepurchaseOfEquity"])

    data["dividends"] = find_val(cf_cons, date_col,
        standard_concepts=["DividendsPaid"],
        concepts=["us-gaap_PaymentsOfDividends", "us-gaap_PaymentsOfDividendsCommonStock",
                  "us-gaap_PaymentsOfOrdinaryDividends",
                  "us-gaap_PaymentsOfDividendsPreferredStockAndPreferenceStock"])

    data["acquisitions"] = find_val(cf_cons, date_col,
        concepts=["us-gaap_PaymentsToAcquireBusinessesNetOfCashAcquired",
                  "us-gaap_PaymentsToAcquireBusinessesAndInterestInAffiliates"])
    # Some companies use custom tags for acquisitions - do a fuzzy search
    if data["acquisitions"] is None and has_concept_col(cf_cons) and date_col in cf_cons.columns:
        acq_rows = cf_cons[cf_cons['concept'].str.contains('Acqui', case=False, na=False)]
        if not acq_rows.empty:
            val = acq_rows.iloc[0][date_col]
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                data["acquisitions"] = float(val)

    return data


def process_ticker(ticker):
    """Process a single ticker: fetch all data from edgartools, return per-FY extracted data."""
    print(f"\n{'='*80}")
    print(f"  {ticker}")
    print(f"{'='*80}")

    try:
        company = Company(ticker)
        filings_10k = list(company.get_filings(form="10-K", amendments=False))[:8]
        print(f"  Found {len(filings_10k)} recent 10-K filings")

        # For each filing, extract data for all date columns it contains
        # Key insight: for a given FY, we want:
        #   IS/CF: can come from any filing that includes that year
        #   BS: must come from a filing whose date columns include that year
        # Strategy: process each filing, collect all (date_col -> field -> value) data
        # For overlapping dates, prefer the filing closest to that date (most accurate)

        all_is_data = {}  # date_col -> {field: value}
        all_bs_data = {}
        all_cf_data = {}

        for filing in filings_10k:
            try:
                xbrl = filing.xbrl()
                if not xbrl:
                    continue

                stmts = xbrl.statements

                # Income statement
                try:
                    inc_stmt = stmts.income_statement()
                    inc_df = inc_stmt.to_dataframe() if inc_stmt else None
                    inc_cons = get_consolidated(inc_df) if inc_df is not None else pd.DataFrame()
                except:
                    inc_cons = pd.DataFrame()

                # Balance sheet
                try:
                    bs_stmt = stmts.balance_sheet()
                    bs_df = bs_stmt.to_dataframe() if bs_stmt else None
                    bs_cons = get_consolidated(bs_df) if bs_df is not None else pd.DataFrame()
                except:
                    bs_cons = pd.DataFrame()

                # Cash flow
                try:
                    cf_stmt = stmts.cash_flow_statement()
                    cf_df = cf_stmt.to_dataframe() if cf_stmt else None
                    cf_cons = get_consolidated(cf_df) if cf_df is not None else pd.DataFrame()
                except:
                    cf_cons = pd.DataFrame()

                # Collect date columns from each statement type
                def date_cols(df):
                    if df is None or df.empty:
                        return []
                    return sorted(c for c in df.columns if c.startswith('20'))

                is_dates = date_cols(inc_cons)
                bs_dates = date_cols(bs_cons)
                cf_dates = date_cols(cf_cons)
                all_dates = sorted(set(is_dates + bs_dates + cf_dates))

                for dc in all_dates:
                    # IS fields
                    if dc in is_dates and dc not in all_is_data:
                        is_fields = {}
                        for field in ["revenue", "cogs", "gross_profit", "sga", "rnd",
                                     "depreciation", "ebit", "interest_expense", "taxes",
                                     "net_income", "eps_diluted", "shares_diluted"]:
                            # Use extract_all_fields for individual field extraction
                            pass
                        # Just store the consolidated dfs for later extraction
                        all_is_data[dc] = (inc_cons, cf_cons)

                    # BS fields
                    if dc in bs_dates and dc not in all_bs_data:
                        all_bs_data[dc] = bs_cons

                    # CF fields
                    if dc in cf_dates and dc not in all_cf_data:
                        all_cf_data[dc] = cf_cons

                time.sleep(0.3)

            except Exception as e:
                print(f"  Error on filing {filing.filing_date}: {e}")

        # Now extract all fields for each available date
        extracted = {}  # date_col -> {field: value}
        all_dates = sorted(set(list(all_is_data.keys()) + list(all_bs_data.keys()) + list(all_cf_data.keys())))

        for dc in all_dates:
            try:
                inc_cons = all_is_data.get(dc, (pd.DataFrame(), pd.DataFrame()))[0]
                cf_cons_for_is = all_is_data.get(dc, (pd.DataFrame(), pd.DataFrame()))[1]
                bs_cons = all_bs_data.get(dc, pd.DataFrame())
                cf_cons = all_cf_data.get(dc, pd.DataFrame())

                # Use cf_cons for depreciation fallback, prefer the one from IS filing
                cf_for_depr = cf_cons_for_is if has_concept_col(cf_cons_for_is) else cf_cons

                extracted[dc] = extract_all_fields(inc_cons, bs_cons,
                    cf_cons if has_concept_col(cf_cons) else cf_for_depr, dc)
            except Exception as e:
                print(f"  Error extracting {dc}: {e}")

        print(f"  Extracted data for dates: {list(extracted.keys())}")
        return extracted

    except Exception as e:
        print(f"  FATAL ERROR for {ticker}: {e}")
        traceback.print_exc()
        return extracted if 'extracted' in dir() else {}


def compare_field(field, baseline_val, edgar_val):
    """Compare a single field value between baseline and edgartools."""
    # Normalize CF sign convention
    if field in ABS_FIELDS and edgar_val is not None:
        edgar_val = abs(edgar_val)

    if baseline_val is None and edgar_val is None:
        return "both_null", edgar_val
    elif baseline_val is None and edgar_val is not None:
        # Skip trivially zero values
        if abs(edgar_val) < 1:
            return "both_null", edgar_val
        return "NEW", edgar_val
    elif baseline_val is not None and edgar_val is None:
        return "REGRESSION", edgar_val
    else:
        # Both have values
        if baseline_val == 0:
            if abs(edgar_val) < 1:
                return "match", edgar_val
            else:
                return "mismatch", edgar_val
        pct_diff = abs(edgar_val - baseline_val) / abs(baseline_val)
        if pct_diff < 0.01:
            return "match", edgar_val
        elif pct_diff < 0.05:
            return "close", edgar_val
        else:
            return "mismatch", edgar_val


def match_fy_to_date(fy, available_dates):
    """Match a fiscal year number to the best available date column."""
    # Direct year match (e.g., FY2024 -> 2024-06-30 or 2024-12-31)
    for dc in sorted(available_dates):
        if dc.startswith(str(fy)):
            return dc

    # Some companies have FY ending early next year (e.g., FY2024 ending Jan 2025)
    for dc in sorted(available_dates):
        year = int(dc[:4])
        month = int(dc.split("-")[1])
        if year == fy + 1 and month <= 3:
            return dc

    return None


def run_comparison():
    all_summaries = {}

    for ticker in TICKERS:
        extracted = process_ticker(ticker)

        baseline_entries = BASELINE.get(ticker, [])
        baseline_by_fy = {int(e["fy"]): e for e in baseline_entries}

        ticker_stats = {
            "nulls_before": 0, "nulls_after": 0,
            "new": 0, "regressions": 0,
            "matches": 0, "mismatches": 0, "both_null": 0,
        }

        for fy in sorted(FY_RANGE):
            if fy not in baseline_by_fy:
                continue

            baseline_row = baseline_by_fy[fy]
            date_col = match_fy_to_date(fy, extracted.keys())

            if not date_col:
                print(f"  FY{fy}: no matching edgartools date (available: {list(extracted.keys())})")
                # Count all baseline non-nulls as regressions
                for field in ALL_FIELDS:
                    bv = baseline_row.get(field)
                    if bv is None:
                        ticker_stats["nulls_before"] += 1
                        ticker_stats["nulls_after"] += 1
                        ticker_stats["both_null"] += 1
                    else:
                        ticker_stats["regressions"] += 1
                        ticker_stats["nulls_after"] += 1
                continue

            edgar_row = extracted[date_col]

            print(f"\n  FY{fy} (period: {date_col}):")
            print(f"  {'Field':20s} {'Baseline':>16s} {'edgartools':>16s} {'Status':>12s}")
            print(f"  {'-'*20} {'-'*16} {'-'*16} {'-'*12}")

            for field in ALL_FIELDS:
                bv = baseline_row.get(field)
                ev = edgar_row.get(field)
                status, ev_normalized = compare_field(field, bv, ev)

                bv_str = f"{bv:>16,.0f}" if bv is not None else f"{'NULL':>16s}"
                ev_display = ev_normalized if ev_normalized is not None else ev
                ev_str = f"{ev_display:>16,.0f}" if ev_display is not None else f"{'NULL':>16s}"

                marker = ""
                if status == "NEW":
                    marker = " <-- FILLED"
                    ticker_stats["new"] += 1
                elif status == "REGRESSION":
                    marker = " <-- LOST!"
                    ticker_stats["regressions"] += 1
                elif status == "mismatch":
                    pct = ""
                    if bv and ev_normalized and bv != 0:
                        pct = f" ({(ev_normalized-bv)/abs(bv)*100:+.1f}%)"
                    marker = f" <-- DIFF{pct}"
                    ticker_stats["mismatches"] += 1
                elif status in ("match", "close"):
                    ticker_stats["matches"] += 1
                elif status == "both_null":
                    ticker_stats["both_null"] += 1

                if bv is None:
                    ticker_stats["nulls_before"] += 1
                if ev is None or (field in ABS_FIELDS and ev is not None and abs(ev) < 1):
                    ticker_stats["nulls_after"] += 1

                print(f"  {field:20s} {bv_str} {ev_str} {status:>12s}{marker}")

        print(f"\n  Summary for {ticker}:")
        for k, v in ticker_stats.items():
            print(f"    {k}: {v}")

        all_summaries[ticker] = ticker_stats

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")

    print(f"\n{'Ticker':8s} {'NULLs Before':>14s} {'NULLs After':>14s} {'Filled':>8s} {'Lost':>8s} {'Match':>8s} {'Mismatch':>10s} {'BothNull':>10s}")
    print(f"{'-'*8} {'-'*14} {'-'*14} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*10}")

    total = {k: 0 for k in ["nulls_before", "nulls_after", "new", "regressions", "matches", "mismatches", "both_null"]}
    for ticker in TICKERS:
        s = all_summaries.get(ticker, {})
        if not s:
            continue
        print(f"{ticker:8s} {s['nulls_before']:>14d} {s['nulls_after']:>14d} {s['new']:>8d} {s['regressions']:>8d} {s['matches']:>8d} {s['mismatches']:>10d} {s['both_null']:>10d}")
        for k in total:
            total[k] += s.get(k, 0)

    print(f"{'-'*8} {'-'*14} {'-'*14} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*10}")
    print(f"{'TOTAL':8s} {total['nulls_before']:>14d} {total['nulls_after']:>14d} {total['new']:>8d} {total['regressions']:>8d} {total['matches']:>8d} {total['mismatches']:>10d} {total['both_null']:>10d}")

    if total['nulls_before'] > 0:
        pct_reduction = (total['nulls_before'] - total['nulls_after']) / total['nulls_before'] * 100
        print(f"\nNULL reduction: {pct_reduction:.1f}%")

    if total['matches'] + total['mismatches'] > 0:
        agreement = total['matches'] / (total['matches'] + total['mismatches']) * 100
        print(f"Value agreement (where both have data): {agreement:.1f}%")

    print(f"\n--- GO/NO-GO ---")
    null_red = (total['nulls_before'] - total['nulls_after']) / total['nulls_before'] * 100 if total['nulls_before'] > 0 else 0
    agree = total['matches'] / (total['matches'] + total['mismatches']) * 100 if (total['matches'] + total['mismatches']) > 0 else 0
    print(f"  >50% NULL reduction: {null_red:.1f}% -> {'PASS' if null_red > 50 else 'FAIL'}")
    print(f"  >95% value agreement: {agree:.1f}% -> {'PASS' if agree > 95 else 'FAIL'}")
    print(f"  Zero regressions: {total['regressions']} -> {'PASS' if total['regressions'] == 0 else 'FAIL (investigate below)'}")

    # Save results
    output_path = Path(__file__).parent / "spike_edgartools_results.json"
    with open(output_path, "w") as f:
        json.dump({"summaries": all_summaries, "total": total}, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    run_comparison()
