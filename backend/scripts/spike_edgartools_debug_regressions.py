"""Debug specific regressions to see if they're fixable."""

from edgar import Company, set_identity
import math

set_identity("CommonInvestor/1.0 spike@example.com")

# 1. MSFT interest_expense regression
print("=" * 60)
print("MSFT interest_expense - is it in the IS or somewhere else?")
print("=" * 60)
company = Company("MSFT")
filings = list(company.get_filings(form="10-K", amendments=False))
# FY2020 filing
for f in filings:
    if "2020" in str(f.filing_date):
        xbrl = f.xbrl()
        inc = xbrl.statements.income_statement()
        df = inc.to_dataframe()
        cons = df[(df['dimension'] == False) & (df['abstract'] == False)]
        # Search for anything with "interest" in concept
        for _, row in cons.iterrows():
            if 'interest' in str(row['concept']).lower():
                print(f"  IS: {row['label']:50s} concept={row['concept']}")

        # Check all statements for interest
        for stmt_name in ['income_statement', 'balance_sheet', 'cash_flow_statement']:
            try:
                stmt = getattr(xbrl.statements, stmt_name)()
                if stmt:
                    sdf = stmt.to_dataframe()
                    scons = sdf[(sdf['dimension'] == False) & (sdf['abstract'] == False)]
                    for _, row in scons.iterrows():
                        if 'interestexpense' in str(row['concept']).lower().replace('_',''):
                            dc = [c for c in sdf.columns if c.startswith('20')]
                            vals = {c: row[c] for c in dc}
                            print(f"  {stmt_name}: {row['label']:40s} concept={row['concept']}  vals={vals}")
            except:
                pass
        break

# 2. Check shares_diluted regressions
print("\n" + "=" * 60)
print("NEE shares_diluted - where is it?")
print("=" * 60)
company = Company("NEE")
filings = list(company.get_filings(form="10-K", amendments=False))
for f in filings:
    if "2020" in str(f.filing_date):
        xbrl = f.xbrl()
        inc = xbrl.statements.income_statement()
        df = inc.to_dataframe()
        cons = df[(df['dimension'] == False) & (df['abstract'] == False)]
        dc = [c for c in df.columns if c.startswith('20')]
        for _, row in cons.iterrows():
            if 'share' in str(row['concept']).lower() or 'earning' in str(row['concept']).lower():
                vals = {c: row[c] for c in dc if not (isinstance(row[c], float) and math.isnan(row[c]))}
                print(f"  {row['label']:50s} concept={row['concept']:60s} sc={row.get('standard_concept')}  {vals}")
        # Also check the full df (including dimensional)
        print("\n  All shares rows (including dimensional):")
        for _, row in df.iterrows():
            if 'weightedaverage' in str(row['concept']).lower():
                vals = {c: row[c] for c in dc if not (isinstance(row[c], float) and math.isnan(row[c]))}
                print(f"  dim={row['dimension']}  {row['label']:40s} concept={row['concept']}  {vals}")
        break

# 3. Check SGA regressions - LMT
print("\n" + "=" * 60)
print("LMT SGA regression - what does IS look like?")
print("=" * 60)
company = Company("LMT")
filings = list(company.get_filings(form="10-K", amendments=False))
for f in filings:
    if "2024" in str(f.filing_date):
        xbrl = f.xbrl()
        inc = xbrl.statements.income_statement()
        df = inc.to_dataframe()
        cons = df[(df['dimension'] == False) & (df['abstract'] == False)]
        dc = [c for c in df.columns if c.startswith('20')]
        print("  All IS consolidated rows:")
        for _, row in cons.iterrows():
            vals = {c: row[c] for c in dc if not (isinstance(row[c], float) and math.isnan(row[c]))}
            sc = row.get('standard_concept') or ''
            print(f"  {row['label']:50s} sc={sc:30s} concept={row['concept']}")
        break
