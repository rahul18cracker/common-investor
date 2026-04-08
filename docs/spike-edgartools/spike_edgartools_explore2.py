"""Task 1b: Deep dive into edgartools statement objects."""

from edgar import Company, set_identity

set_identity("CommonInvestor/1.0 spike@example.com")

company = Company("MSFT")
financials = company.get_financials()

print("=" * 80)
print("CALLING income_statement()")
print("=" * 80)

inc = financials.income_statement()
print(f"Type: {type(inc)}")
print(f"Dir: {[a for a in dir(inc) if not a.startswith('_')]}")
print(f"\nRepr:\n{inc}")

print("\n\nAll non-private attrs:")
for attr in sorted(dir(inc)):
    if not attr.startswith('_'):
        val = getattr(inc, attr)
        if not callable(val):
            print(f"  {attr} = {type(val).__name__}: {repr(val)[:300]}")

print("\n\nCallable methods:")
for attr in sorted(dir(inc)):
    if not attr.startswith('_'):
        val = getattr(inc, attr)
        if callable(val):
            print(f"  {attr}()")

# Try to_dataframe
print("\n" + "=" * 80)
print("TO DATAFRAME")
print("=" * 80)
if hasattr(inc, 'to_dataframe'):
    df = inc.to_dataframe()
    print(f"Shape: {df.shape}")
    print(df.to_string())

# Try get_dataframe
if hasattr(inc, 'get_dataframe'):
    df = inc.get_dataframe()
    print(f"Shape: {df.shape}")
    print(df.to_string())

# Check if it has a data attribute
if hasattr(inc, 'data'):
    print(f"\nData type: {type(inc.data)}")
    print(f"Data:\n{inc.data}")

# Check periods
if hasattr(inc, 'periods'):
    print(f"\nPeriods: {inc.periods}")

# Check columns
if hasattr(inc, 'columns'):
    print(f"\nColumns: {inc.columns}")

# Try helper methods from Financials
print("\n" + "=" * 80)
print("FINANCIALS HELPER METHODS")
print("=" * 80)

helpers = [
    'get_revenue', 'get_net_income', 'get_operating_income',
    'get_operating_cash_flow', 'get_capital_expenditures',
    'get_free_cash_flow', 'get_total_assets', 'get_total_liabilities',
    'get_stockholders_equity', 'get_shares_outstanding_diluted',
    'get_shares_outstanding_basic', 'get_current_assets',
    'get_current_liabilities', 'get_financial_metrics',
]

for method_name in helpers:
    if hasattr(financials, method_name):
        try:
            result = getattr(financials, method_name)()
            print(f"  {method_name}() = {result}")
        except Exception as e:
            print(f"  {method_name}() -> ERROR: {e}")

# Try balance sheet
print("\n" + "=" * 80)
print("BALANCE SHEET")
print("=" * 80)
bs = financials.balance_sheet()
print(f"Type: {type(bs)}")
print(f"\n{bs}")

# Try cash flow
print("\n" + "=" * 80)
print("CASH FLOW")
print("=" * 80)
cf = financials.cash_flow_statement()
print(f"Type: {type(cf)}")
print(f"\n{cf}")

# Check quarterly financials
print("\n" + "=" * 80)
print("QUARTERLY FINANCIALS")
print("=" * 80)
try:
    qf = company.get_quarterly_financials()
    print(f"Type: {type(qf)}")
    if qf:
        qi = qf.income_statement()
        print(f"Quarterly IS: {qi}")
except Exception as e:
    print(f"ERROR: {e}")

# Multiple years - check get_filings approach
print("\n" + "=" * 80)
print("MULTI-YEAR: Getting financials from specific filings")
print("=" * 80)
filings_10k = company.get_filings(form="10-K")
for f in list(filings_10k)[:5]:
    print(f"\n--- Filing: {f.filing_date} ---")
    try:
        xbrl = f.xbrl()
        if xbrl:
            stmts = xbrl.statements
            print(f"  Statements type: {type(stmts)}")
            print(f"  Statements dir: {[a for a in dir(stmts) if not a.startswith('_')]}")
            # Try to list available statements
            if hasattr(stmts, 'list'):
                print(f"  Statement list: {stmts.list()}")
            print(f"  Repr: {repr(stmts)[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    break  # Just check one for now
