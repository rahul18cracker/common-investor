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
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "ebit": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense"],
    "taxes": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss"],
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
        # IS
        execute(
            """
            INSERT INTO statement_is (filing_id, fy, revenue, ebit, interest_expense, taxes, net_income, eps_diluted, shares_diluted)
            VALUES (:filing_id, :fy, :revenue, :ebit, :interest_expense, :taxes, :net_income, :eps_diluted, :shares_diluted)
        """,
            filing_id=filing_id,
            fy=fy,
            revenue=_annual_value(units_cache["is"]["revenue"], "USD", fy),
            ebit=_annual_value(units_cache["is"]["ebit"], "USD", fy),
            interest_expense=_annual_value(
                units_cache["is"]["interest_expense"], "USD", fy
            ),
            taxes=_annual_value(units_cache["is"]["taxes"], "USD", fy),
            net_income=_annual_value(units_cache["is"]["net_income"], "USD", fy),
            eps_diluted=_annual_value(
                units_cache["is"]["eps_diluted"], "USD/shares", fy
            ),
            shares_diluted=_annual_value(
                units_cache["is"]["shares_diluted"], "shares", fy
            ),
        )
        # BS
        execute(
            """
            INSERT INTO statement_bs (filing_id, fy, cash, receivables, inventory, total_assets, total_liabilities, total_debt, shareholder_equity)
            VALUES (:filing_id, :fy, :cash, :receivables, :inventory, :total_assets, :total_liabilities, :total_debt, :shareholder_equity)
        """,
            filing_id=filing_id,
            fy=fy,
            cash=_annual_value(units_cache["bs"]["cash"], "USD", fy),
            receivables=_annual_value(units_cache["bs"]["receivables"], "USD", fy),
            inventory=_annual_value(units_cache["bs"]["inventory"], "USD", fy),
            total_assets=_annual_value(units_cache["bs"]["total_assets"], "USD", fy),
            total_liabilities=_annual_value(
                units_cache["bs"]["total_liabilities"], "USD", fy
            ),
            total_debt=_annual_value(units_cache["bs"]["total_debt"], "USD", fy),
            shareholder_equity=_annual_value(
                units_cache["bs"]["shareholder_equity"], "USD", fy
            ),
        )
        # CF
        execute(
            """
            INSERT INTO statement_cf (filing_id, fy, cfo, capex, buybacks, dividends, acquisitions)
            VALUES (:filing_id, :fy, :cfo, :capex, :buybacks, :dividends, :acquisitions)
        """,
            filing_id=filing_id,
            fy=fy,
            cfo=_annual_value(units_cache["cf"]["cfo"], "USD", fy),
            capex=_annual_value(units_cache["cf"]["capex"], "USD", fy),
            buybacks=_annual_value(units_cache["cf"]["buybacks"], "USD", fy),
            dividends=_annual_value(units_cache["cf"]["dividends"], "USD", fy),
            acquisitions=_annual_value(units_cache["cf"]["acquisitions"], "USD", fy),
        )
    return {"ticker": ticker.upper(), "cik": f"{cik:010d}", "years": years}
