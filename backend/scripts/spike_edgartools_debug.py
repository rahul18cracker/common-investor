"""Debug: investigate BS regressions and CF sign conventions."""

from edgar import Company, set_identity

set_identity("CommonInvestor/1.0 spike@example.com")

# Check MSFT BS - why are we getting NULLs for FY2020?
company = Company("MSFT")
filings_10k = list(company.get_filings(form="10-K"))

# FY2020 ends June 2020 -> that's the 2020-07-30 filing
fy2020_filing = None
for f in filings_10k:
    if "2020" in str(f.filing_date):
        fy2020_filing = f
        break

# But also check the 2022 filing which covers FY2020 as oldest year
fy2022_filing = None
for f in filings_10k:
    if "2022" in str(f.filing_date):
        fy2022_filing = f
        break

print("=" * 60)
print("MSFT FY2020 filing (filed 2020-07-30)")
print("=" * 60)
xbrl = fy2020_filing.xbrl()
stmts = xbrl.statements

bs = stmts.balance_sheet()
bs_df = bs.to_dataframe()

# Show all columns
print(f"BS DataFrame columns: {list(bs_df.columns)}")
date_cols = [c for c in bs_df.columns if c.startswith('20')]
print(f"Date columns: {date_cols}")

# Show all BS rows (consolidated only)
cons = bs_df[(bs_df['dimension'] == False) & (bs_df['abstract'] == False)]
print(f"\nConsolidated BS rows ({len(cons)}):")
for _, row in cons.iterrows():
    concept = row['concept']
    label = row.get('label', '')
    sc = row.get('standard_concept', '')
    vals = {col: row[col] for col in date_cols}
    print(f"  {label:50s} concept={concept:60s} sc={sc}  {vals}")

# Check CF sign convention
print("\n" + "=" * 60)
print("MSFT FY2020 CASH FLOW - sign convention check")
print("=" * 60)
cf = stmts.cash_flow_statement()
cf_df = cf.to_dataframe()
cf_date_cols = [c for c in cf_df.columns if c.startswith('20')]
print(f"CF Date columns: {cf_date_cols}")

cf_cons = cf_df[(cf_df['dimension'] == False) & (cf_df['abstract'] == False)]
for _, row in cf_cons.iterrows():
    concept = row['concept']
    label = row.get('label', '')
    sc = row.get('standard_concept', '')
    vals = {col: row[col] for col in cf_date_cols}
    # Show weight/preferred_sign too
    weight = row.get('weight', '')
    ps = row.get('preferred_sign', '')
    if any(kw in concept.lower() for kw in ['capex', 'payment', 'purchase', 'repurchase', 'dividend', 'acquire']):
        print(f"  {label:50s} concept={concept:60s} weight={weight} ps={ps} {vals}")

# Check if the FY2022 filing has BS data for 2020
print("\n" + "=" * 60)
print("MSFT FY2022 filing - does it have 2020 BS data?")
print("=" * 60)
xbrl2 = fy2022_filing.xbrl()
stmts2 = xbrl2.statements
bs2 = stmts2.balance_sheet()
bs_df2 = bs2.to_dataframe()
date_cols2 = [c for c in bs_df2.columns if c.startswith('20')]
print(f"Date columns in FY2022 BS: {date_cols2}")
print("(BS typically only has current + prior year, not 3 years back)")
