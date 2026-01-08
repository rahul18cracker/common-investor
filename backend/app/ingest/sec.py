import os
import httpx
from app.db.session import execute

SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", "CommonInvestor/0.1 you@example.com"),
    "Accept-Encoding": "gzip, deflate",
}
BASE = "https://www.sec.gov"


def fetch_json(url: str) -> dict:
    with httpx.Client(timeout=30.0, headers=SEC_HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


def ticker_map():
    data = fetch_json(BASE + "/files/company_tickers.json")
    # SEC returns {"0": {"cik_str": ..., "ticker": ...}, "1": {...}, ...}
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def company_facts(cik: int) -> dict:
    # CompanyFacts API is on data.sec.gov subdomain
    return fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")


IS_TAGS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "RevenuesNetOfInterestExpense",
    ],
    "cogs": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfServices",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "sga": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "rnd": [
        "ResearchAndDevelopmentExpense",
    ],
    "depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    "ebit": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense"],
    "taxes": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "shares_diluted": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
}
BS_TAGS = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "receivables": ["ReceivablesNetCurrent", "AccountsReceivableNetCurrent"],
    "inventory": ["InventoryNet"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "total_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtCurrent",
        "DebtCurrent",
        "ShortTermBorrowings",
    ],
    "shareholder_equity": [
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity",
    ],
}
CF_TAGS = {
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditures",
        "PaymentsToAcquireProductiveAssets",
    ],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "dividends": ["PaymentsOfDividends"],
    "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
}

STATEMENT_SCHEMAS = {
    "is": {
        "table": "statement_is",
        "fields": [
            "revenue",
            "cogs",
            "gross_profit",
            "sga",
            "rnd",
            "depreciation",
            "ebit",
            "interest_expense",
            "taxes",
            "net_income",
            "eps_diluted",
            "shares_diluted",
        ],
        "units": {
            "revenue": "USD",
            "cogs": "USD",
            "gross_profit": "USD",
            "sga": "USD",
            "rnd": "USD",
            "depreciation": "USD",
            "ebit": "USD",
            "interest_expense": "USD",
            "taxes": "USD",
            "net_income": "USD",
            "eps_diluted": "USD/shares",
            "shares_diluted": "shares",
        },
    },
    "bs": {
        "table": "statement_bs",
        "fields": [
            "cash",
            "receivables",
            "inventory",
            "total_assets",
            "total_liabilities",
            "total_debt",
            "shareholder_equity",
        ],
        "units": {
            "cash": "USD",
            "receivables": "USD",
            "inventory": "USD",
            "total_assets": "USD",
            "total_liabilities": "USD",
            "total_debt": "USD",
            "shareholder_equity": "USD",
        },
    },
    "cf": {
        "table": "statement_cf",
        "fields": ["cfo", "capex", "buybacks", "dividends", "acquisitions"],
        "units": {
            "cfo": "USD",
            "capex": "USD",
            "buybacks": "USD",
            "dividends": "USD",
            "acquisitions": "USD",
        },
    },
}


def upsert_company(cik: str, ticker: str, name: str | None = None):
    execute(
        """
        INSERT INTO company (cik, ticker, name) VALUES (:cik, :ticker, :name)
        ON CONFLICT (cik) DO UPDATE SET ticker=EXCLUDED.ticker, name=COALESCE(EXCLUDED.name, company.name)
    """,
        cik=cik,
        ticker=ticker,
        name=name,
    )


def upsert_filing(
    cik: str, form: str | None, accession: str | None, period_end: str | None
):
    # Convert date objects to ISO format strings for SQLite compatibility
    from datetime import date

    if isinstance(period_end, date):
        period_end = period_end.isoformat()

    # For SQLite, skip CAST and just insert as string (SQLite doesn't enforce types)
    row = execute(
        """
        INSERT INTO filing (cik, form, accession, period_end)
        VALUES (:cik, :form, :accession, :period_end)
        ON CONFLICT (accession) DO NOTHING
        RETURNING id
    """,
        cik=cik,
        form=form,
        accession=accession,
        period_end=period_end,
    ).first()
    return int(row[0]) if row else None


def _pick_first_units(facts: dict, tag_list: list[str]) -> dict | None:
    f = facts.get("facts", {}).get("us-gaap", {})
    for t in tag_list:
        if t in f:
            return f[t]["units"]
    return None


def _annual_value(units: dict, unit_key: str, fy: int) -> float | None:
    if not units or unit_key not in units:
        return None
    best = None
    best_end = None
    for item in units[unit_key]:
        if item.get("fy") != fy:
            continue
        if item.get("form") not in ("10-K", "20-F"):
            continue
        v = item.get("val")
        end = item.get("end", "")
        # Prefer the latest period end date for this fiscal year
        if isinstance(v, (int, float)):
            if best_end is None or end > best_end:
                best = float(v)
                best_end = end
    return best


def _insert_statement(filing_id: int, fy: int, stmt_type: str, units_cache: dict):
    """Generic statement insertion using schema configuration.
    
    Args:
        filing_id: ID of the filing record
        fy: Fiscal year
        stmt_type: Statement type key ('is', 'bs', or 'cf')
        units_cache: Nested dict with units data for each statement type
    """
    schema = STATEMENT_SCHEMAS[stmt_type]
    table = schema["table"]
    fields = schema["fields"]
    units_map = schema["units"]
    
    # Build field values dynamically
    values = {"filing_id": filing_id, "fy": fy}
    for field in fields:
        unit_key = units_map[field]
        values[field] = _annual_value(units_cache[stmt_type][field], unit_key, fy)
    
    # Build SQL dynamically
    field_names = ", ".join(["filing_id", "fy"] + fields)
    placeholders = ", ".join([f":{name}" for name in ["filing_id", "fy"] + fields])
    sql = f"INSERT INTO {table} ({field_names}) VALUES ({placeholders})"
    
    execute(sql, **values)


def ingest_companyfacts_richer_by_ticker(ticker: str):
    t2c = ticker_map()
    cik = t2c.get(ticker.upper())
    if not cik:
        raise ValueError(f"No CIK found for {ticker}")
    facts = company_facts(cik)
    entity = facts.get("entityName", "")
    upsert_company(f"{cik:010d}", ticker.upper(), name=entity)

    units_cache = {"is": {}, "bs": {}, "cf": {}}
    for k, tags in IS_TAGS.items():
        units_cache["is"][k] = _pick_first_units(facts, tags)
    for k, tags in BS_TAGS.items():
        units_cache["bs"][k] = _pick_first_units(facts, tags)
    for k, tags in CF_TAGS.items():
        units_cache["cf"][k] = _pick_first_units(facts, tags)

    years = set()
    for units, key in (
        (units_cache["is"]["revenue"], "USD"),
        (units_cache["is"]["eps_diluted"], "USD/shares"),
    ):
        if units and key in units:
            for item in units[key]:
                fy = item.get("fy")
                form = item.get("form", "")
                if fy and form in ("10-K", "20-F"):
                    years.add(int(fy))
    years = sorted(years)

    for fy in years:
        filing_id = upsert_filing(
            cik=f"{cik:010d}",
            form="10-K",
            accession=f"FACTS-{cik}-{fy}",
            period_end=f"{fy}-12-31",
        )
        _insert_statement(filing_id, fy, "is", units_cache)
        _insert_statement(filing_id, fy, "bs", units_cache)
        _insert_statement(filing_id, fy, "cf", units_cache)
    return {"ticker": ticker.upper(), "cik": f"{cik:010d}", "years": years}
