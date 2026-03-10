"""Task 1c: Test multi-year data extraction from individual 10-K filings."""

from edgar import Company, set_identity
import time

set_identity("CommonInvestor/1.0 spike@example.com")

company = Company("MSFT")
filings_10k = company.get_filings(form="10-K")

print("All 10-K filings:")
for f in list(filings_10k)[:10]:
    print(f"  {f.filing_date}  {f.form}  {f.accession_no}")

# Try getting financials from the 2021 filing (FY ending June 2021)
# That should be the ~4th filing back
filings_list = list(filings_10k)

# Get financials from a few different filings
for filing in filings_list[:6]:
    print(f"\n{'='*60}")
    print(f"Filing: {filing.filing_date}")
    print(f"{'='*60}")
    try:
        xbrl = filing.xbrl()
        if not xbrl:
            print("  No XBRL data")
            continue

        # Check the period info
        print(f"  Entity: {xbrl.entity_name}")
        print(f"  Document type: {xbrl.document_type}")

        # Try income statement
        stmts = xbrl.statements
        inc = stmts.income_statement()
        if inc:
            df = inc.to_dataframe()
            # Filter to non-dimensional consolidated rows
            consolidated = df[(df['dimension'] == False) & (df['abstract'] == False)]

            # Get value columns (dates)
            date_cols = [c for c in df.columns if c.startswith('20')]
            print(f"  Date columns: {date_cols}")

            # Show key fields
            for _, row in consolidated.iterrows():
                concept = row.get('concept', '')
                label = row.get('label', '')
                vals = {col: row[col] for col in date_cols}
                sc = row.get('standard_concept', '')
                if any(kw in concept.lower() for kw in ['revenue', 'costofgoods', 'grossprofit', 'operatingincome', 'netincome', 'earningspershare', 'weightedaverage', 'researchand', 'sellingand', 'generaland', 'interestexpense', 'incometax', 'depreciation']):
                    print(f"  {label:40s} std={sc:30s} {vals}")
        else:
            print("  No income statement found")

        # Also check balance sheet and cash flow
        bs = stmts.balance_sheet()
        if bs:
            bs_df = bs.to_dataframe()
            date_cols_bs = [c for c in bs_df.columns if c.startswith('20')]
            print(f"\n  BS date columns: {date_cols_bs}")
            bs_cons = bs_df[(bs_df['dimension'] == False) & (bs_df['abstract'] == False)]
            for _, row in bs_cons.iterrows():
                concept = row.get('concept', '')
                label = row.get('label', '')
                vals = {col: row[col] for col in date_cols_bs}
                sc = row.get('standard_concept', '')
                if any(kw in concept.lower() for kw in ['cashandcash', 'receivable', 'inventor', 'assets', 'liabilit', 'debt', 'equity', 'stockholder']):
                    print(f"  {label:50s} std={sc:30s} {vals}")

    except Exception as e:
        import traceback
        traceback.print_exc()

    time.sleep(0.5)  # Rate limiting
