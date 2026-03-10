"""Task 1: Explore edgartools API surface using MSFT as test case."""

from edgar import Company, set_identity

set_identity("CommonInvestor/1.0 spike@example.com")

print("=" * 80)
print("TASK 1: edgartools Exploration (MSFT)")
print("=" * 80)

company = Company("MSFT")
print(f"\nCompany: {company.name} (CIK: {company.cik})")
print(f"Company dir (non-private): {[a for a in dir(company) if not a.startswith('_') and not a.startswith('__')]}")

# Get filings - check what types are available
filings = company.get_filings(form="10-K")
print(f"\n10-K filings found: {len(filings)}")
for f in filings[:3]:
    print(f"  {f.filing_date}  {f.form}  {f.accession_no}")

# Get financials
print("\n" + "=" * 80)
print("FINANCIALS API")
print("=" * 80)

financials = company.get_financials()
print(f"\nType of financials: {type(financials)}")
print(f"Dir: {[a for a in dir(financials) if not a.startswith('_')]}")

# Income statement
print("\n--- INCOME STATEMENT ---")
try:
    inc = financials.income_statement
    print(f"Type: {type(inc)}")
    print(f"Dir: {[a for a in dir(inc) if not a.startswith('_')]}")
    print(f"\nRepr:\n{inc}")
except Exception as e:
    import traceback; traceback.print_exc()

# Balance sheet
print("\n--- BALANCE SHEET ---")
try:
    bs = financials.balance_sheet
    print(f"Type: {type(bs)}")
    print(f"\nRepr:\n{bs}")
except Exception as e:
    import traceback; traceback.print_exc()

# Cash flow
print("\n--- CASH FLOW ---")
try:
    cf = financials.cash_flow_statement
    print(f"Type: {type(cf)}")
    print(f"\nRepr:\n{cf}")
except Exception as e:
    import traceback; traceback.print_exc()

# Explore the income statement object in depth
print("\n" + "=" * 80)
print("INCOME STATEMENT DEEP DIVE")
print("=" * 80)
try:
    inc = financials.income_statement
    print(f"\nAll non-private non-callable attrs:")
    for attr in sorted(dir(inc)):
        if not attr.startswith('_'):
            val = getattr(inc, attr)
            if not callable(val):
                print(f"  {attr} = {type(val).__name__}: {repr(val)[:200]}")

    print(f"\nCallable methods:")
    for attr in sorted(dir(inc)):
        if not attr.startswith('_'):
            val = getattr(inc, attr)
            if callable(val):
                print(f"  {attr}()")

    # Try to get as dataframe
    if hasattr(inc, 'to_dataframe'):
        df = inc.to_dataframe()
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Index: {list(df.index)}")
        print(f"\n{df.to_string()}")

    # Try to get as dict
    if hasattr(inc, 'to_dict'):
        print(f"\nto_dict: {inc.to_dict()}")

except Exception as e:
    import traceback; traceback.print_exc()

# Check annual vs quarterly
print("\n" + "=" * 80)
print("ANNUAL vs QUARTERLY")
print("=" * 80)
try:
    # Check if get_financials accepts period params
    import inspect
    sig = inspect.signature(company.get_financials)
    print(f"get_financials signature: {sig}")

    # Try annual explicitly
    for kwarg in [{'period': 'annual'}, {'form': '10-K'}, {}]:
        try:
            f = company.get_financials(**kwarg)
            print(f"  get_financials({kwarg}) -> {type(f)}")
        except Exception as e:
            print(f"  get_financials({kwarg}) -> ERROR: {e}")
except Exception as e:
    import traceback; traceback.print_exc()

# Check fiscal year handling (MSFT = June FY)
print("\n" + "=" * 80)
print("FISCAL YEAR HANDLING (MSFT = June FY)")
print("=" * 80)
try:
    inc = financials.income_statement
    if hasattr(inc, 'periods'):
        print(f"Periods: {inc.periods}")
    if hasattr(inc, 'end_date'):
        print(f"End date: {inc.end_date}")
    if hasattr(inc, 'period_end'):
        print(f"Period end: {inc.period_end}")
    if hasattr(inc, 'fiscal_year'):
        print(f"Fiscal year: {inc.fiscal_year}")
    if hasattr(inc, 'columns'):
        print(f"Columns: {inc.columns}")
except Exception as e:
    import traceback; traceback.print_exc()

# Try getting a specific filing's financials
print("\n" + "=" * 80)
print("FILING-LEVEL FINANCIALS")
print("=" * 80)
try:
    filing = filings[0]  # Most recent 10-K
    print(f"Filing: {filing.filing_date} {filing.form}")

    # Check if filing has financials
    if hasattr(filing, 'financials'):
        print(f"  filing.financials exists")
    if hasattr(filing, 'get_financials'):
        print(f"  filing.get_financials() exists")

    xbrl = filing.xbrl()
    if xbrl:
        print(f"  XBRL type: {type(xbrl)}")
        print(f"  XBRL dir: {[a for a in dir(xbrl) if not a.startswith('_')][:20]}")
    else:
        print("  No XBRL")
except Exception as e:
    import traceback; traceback.print_exc()

print("\n" + "=" * 80)
print("EXPLORATION COMPLETE")
print("=" * 80)
