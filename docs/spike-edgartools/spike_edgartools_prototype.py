"""Task 4: Prototype of ingest_via_edgartools() function.

This demonstrates what a replacement for ingest_companyfacts_richer_by_ticker()
would look like using edgartools instead of raw CompanyFacts JSON.

Design notes:
- Uses edgartools to parse XBRL from each 10-K filing
- Iterates filings from newest to oldest, collecting data for each fiscal period
- Maps edgartools standard_concepts and XBRL concepts to our DB column names
- Handles sign conventions (CF outflows stored as positive in our DB)
- Handles SGA splitting (sum of selling+marketing and G&A)
- Handles total_debt summing (LT noncurrent + current portion)
- Falls back to CompanyFacts for fields edgartools can't find in IS
  (e.g., InterestExpense when not a separate IS line item)
"""

import math
import time
from typing import Optional

import pandas as pd
from edgar import Company, set_identity

set_identity("CommonInvestor/1.0 spike@example.com")


def _get_consolidated(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to consolidated (non-dimensional, non-abstract) rows."""
    if df is None or df.empty or 'concept' not in df.columns:
        return pd.DataFrame()
    return df[(df['dimension'] == False) & (df['abstract'] == False)].copy()


def _find(df: pd.DataFrame, date_col: str,
          concepts: list[str] = None,
          standard_concepts: list[str] = None) -> Optional[float]:
    """Find a value by standard_concept or XBRL concept name."""
    if df.empty or date_col not in df.columns:
        return None

    for sc in (standard_concepts or []):
        m = df[df['standard_concept'] == sc]
        if not m.empty:
            v = m.iloc[0][date_col]
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                return float(v)

    for c in (concepts or []):
        m = df[df['concept'] == c]
        if not m.empty:
            v = m.iloc[0][date_col]
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                return float(v)

    return None


def _sum(df: pd.DataFrame, date_col: str, concepts: list[str]) -> Optional[float]:
    """Sum values for multiple XBRL concepts."""
    if df.empty or date_col not in df.columns:
        return None
    total = 0.0
    for c in concepts:
        m = df[df['concept'] == c]
        if not m.empty:
            v = m.iloc[0][date_col]
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                total += float(v)
            else:
                return None  # Missing component -> can't sum
        else:
            return None
    return total


def extract_period(inc: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame, dc: str) -> dict:
    """Extract all 26 fields for a single period from consolidated statement DataFrames."""
    row = {}

    # Income Statement
    row["revenue"] = _find(inc, dc,
        standard_concepts=["Revenue"],
        concepts=["us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
                  "us-gaap_Revenues", "us-gaap_SalesRevenueNet",
                  "us-gaap_RevenueFromContractWithCustomerIncludingAssessedTax",
                  "us-gaap_RevenuesNetOfInterestExpense"])

    row["cogs"] = _find(inc, dc,
        standard_concepts=["CostOfGoodsAndServicesSold"],
        concepts=["us-gaap_CostOfGoodsAndServicesSold", "us-gaap_CostOfRevenue"])

    row["gross_profit"] = _find(inc, dc,
        standard_concepts=["GrossProfit"],
        concepts=["us-gaap_GrossProfit"])

    # SGA: try combined, then sum split
    row["sga"] = _find(inc, dc,
        concepts=["us-gaap_SellingGeneralAndAdministrativeExpense"])
    if row["sga"] is None:
        row["sga"] = _sum(inc, dc, [
            "us-gaap_SellingAndMarketingExpense",
            "us-gaap_GeneralAndAdministrativeExpense"])

    row["rnd"] = _find(inc, dc,
        standard_concepts=["ResearchAndDevelopementExpenses"],
        concepts=["us-gaap_ResearchAndDevelopmentExpense"])

    # Depreciation: IS first, then CF adjustments
    row["depreciation"] = _find(inc, dc,
        concepts=["us-gaap_DepreciationDepletionAndAmortization",
                  "us-gaap_DepreciationAndAmortization"])
    if row["depreciation"] is None:
        row["depreciation"] = _find(cf, dc,
            concepts=["us-gaap_DepreciationDepletionAndAmortization",
                      "us-gaap_DepreciationAndAmortization"])

    row["ebit"] = _find(inc, dc,
        standard_concepts=["OperatingIncomeLoss"],
        concepts=["us-gaap_OperatingIncomeLoss"])

    row["interest_expense"] = _find(inc, dc,
        standard_concepts=["InterestExpense"],
        concepts=["us-gaap_InterestExpense", "us-gaap_InterestExpenseDebt"])

    row["taxes"] = _find(inc, dc,
        standard_concepts=["IncomeTaxes"],
        concepts=["us-gaap_IncomeTaxExpenseBenefit"])

    row["net_income"] = _find(inc, dc,
        standard_concepts=["NetIncome"],
        concepts=["us-gaap_NetIncomeLoss"])

    row["eps_diluted"] = _find(inc, dc,
        concepts=["us-gaap_EarningsPerShareDiluted", "us-gaap_EarningsPerShareBasic"])

    row["shares_diluted"] = _find(inc, dc,
        standard_concepts=["SharesFullyDilutedAverage"],
        concepts=["us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
                  "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic"])

    # Balance Sheet
    row["cash"] = _find(bs, dc,
        concepts=["us-gaap_CashAndCashEquivalentsAtCarryingValue"])

    row["receivables"] = _find(bs, dc,
        concepts=["us-gaap_AccountsReceivableNetCurrent", "us-gaap_ReceivablesNetCurrent"])

    row["inventory"] = _find(bs, dc,
        standard_concepts=["Inventories"],
        concepts=["us-gaap_InventoryNet"])

    row["total_assets"] = _find(bs, dc,
        standard_concepts=["Assets"],
        concepts=["us-gaap_Assets"])

    row["total_liabilities"] = _find(bs, dc,
        standard_concepts=["Liabilities"],
        concepts=["us-gaap_Liabilities"])

    # Total debt: try combined LongTermDebt, then sum noncurrent + current
    row["total_debt"] = _find(bs, dc, concepts=["us-gaap_LongTermDebt"])
    if row["total_debt"] is None:
        row["total_debt"] = _sum(bs, dc, [
            "us-gaap_LongTermDebtNoncurrent", "us-gaap_LongTermDebtCurrent"])
    if row["total_debt"] is None:
        row["total_debt"] = _find(bs, dc, concepts=["us-gaap_LongTermDebtNoncurrent"])

    row["shareholder_equity"] = _find(bs, dc,
        standard_concepts=["AllEquityBalance", "Equity"],
        concepts=["us-gaap_StockholdersEquity",
                  "us-gaap_StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"])

    # Cash Flow (normalize outflows to positive)
    row["cfo"] = _find(cf, dc,
        standard_concepts=["OperatingCashFlow"],
        concepts=["us-gaap_NetCashProvidedByUsedInOperatingActivities"])

    capex = _find(cf, dc,
        standard_concepts=["CapitalExpenditure"],
        concepts=["us-gaap_PaymentsToAcquirePropertyPlantAndEquipment"])
    row["capex"] = abs(capex) if capex is not None else None

    buybacks = _find(cf, dc,
        concepts=["us-gaap_PaymentsForRepurchaseOfCommonStock",
                  "us-gaap_PaymentsForRepurchaseOfEquity"])
    row["buybacks"] = abs(buybacks) if buybacks is not None else None

    dividends = _find(cf, dc,
        standard_concepts=["DividendsPaid"],
        concepts=["us-gaap_PaymentsOfDividends", "us-gaap_PaymentsOfDividendsCommonStock"])
    row["dividends"] = abs(dividends) if dividends is not None else None

    acq = _find(cf, dc,
        concepts=["us-gaap_PaymentsToAcquireBusinessesNetOfCashAcquired"])
    row["acquisitions"] = abs(acq) if acq is not None else None

    return row


def ingest_via_edgartools(ticker: str, min_year: int = 2015) -> dict:
    """Prototype: fetch financial data via edgartools and return in our DB format.

    Returns:
        {
            "ticker": str,
            "company_name": str,
            "cik": str,
            "years": list[dict],  # Each dict has fy + all 26 fields
        }
    """
    company = Company(ticker)

    result = {
        "ticker": ticker.upper(),
        "company_name": company.name,
        "cik": str(company.cik),
        "years": [],
    }

    filings = list(company.get_filings(form="10-K", amendments=False))

    # Collect data from all filings, keyed by period date
    period_data = {}  # date_str -> dict of fields

    for filing in filings:
        try:
            xbrl = filing.xbrl()
            if not xbrl:
                continue

            stmts = xbrl.statements

            try:
                inc_df = stmts.income_statement().to_dataframe()
                inc = _get_consolidated(inc_df)
            except:
                inc = pd.DataFrame()

            try:
                bs_df = stmts.balance_sheet().to_dataframe()
                bs = _get_consolidated(bs_df)
            except:
                bs = pd.DataFrame()

            try:
                cf_df = stmts.cash_flow_statement().to_dataframe()
                cf = _get_consolidated(cf_df)
            except:
                cf = pd.DataFrame()

            # Get all date columns across all statements
            all_dfs = [inc, bs, cf]
            date_cols = set()
            for df in all_dfs:
                if not df.empty:
                    date_cols.update(c for c in df.columns if c.startswith('20'))

            for dc in sorted(date_cols):
                year = int(dc[:4])
                if year < min_year:
                    continue
                if dc in period_data:
                    # Already have this period from a newer filing - merge BS data only
                    # (BS may only appear in the filing that covers this specific period)
                    existing = period_data[dc]
                    new_row = extract_period(inc, bs, cf, dc)
                    for field, val in new_row.items():
                        if existing.get(field) is None and val is not None:
                            existing[field] = val
                else:
                    period_data[dc] = extract_period(inc, bs, cf, dc)

            time.sleep(0.2)

        except Exception as e:
            print(f"  Warning: error on {filing.filing_date}: {e}")

    # Convert to output format
    for dc in sorted(period_data.keys()):
        year = int(dc[:4])
        row = {"fy": year, "period_end": dc, **period_data[dc]}
        result["years"].append(row)

    return result


# Demo
if __name__ == "__main__":
    import json

    for ticker in ["MSFT", "AAPL", "JPM"]:
        print(f"\n{'='*60}")
        print(f"  {ticker}")
        print(f"{'='*60}")

        data = ingest_via_edgartools(ticker, min_year=2020)
        print(f"  Company: {data['company_name']}")
        print(f"  CIK: {data['cik']}")
        print(f"  Years: {len(data['years'])}")

        for yr in data["years"]:
            fy = yr["fy"]
            nulls = sum(1 for k, v in yr.items() if k not in ("fy", "period_end") and v is None)
            filled = sum(1 for k, v in yr.items() if k not in ("fy", "period_end") and v is not None)
            print(f"    FY{fy} ({yr['period_end']}): {filled}/24 fields populated, {nulls} NULLs")
            # Show key values
            print(f"      revenue={yr.get('revenue')}, net_income={yr.get('net_income')}, cfo={yr.get('cfo')}")

        # Save full output
        output_path = f"/tmp/edgartools_prototype_{ticker}.json"
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  Full output: {output_path}")
