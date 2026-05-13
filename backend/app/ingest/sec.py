import logging

import httpx

from app.core.config import settings
from app.core.industry import sic_to_category
from app.db.session import execute

log = logging.getLogger(__name__)

SEC_HEADERS = {
    "User-Agent": settings.sec_user_agent,
    "Accept-Encoding": "gzip, deflate",
}
BASE = "https://www.sec.gov"


def fetch_json(url: str) -> dict:  # type: ignore[type-arg]
    with httpx.Client(timeout=30.0, headers=SEC_HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()  # type: ignore[no-any-return]


def ticker_map():
    data = fetch_json(BASE + "/files/company_tickers.json")
    # SEC returns {"0": {"cik_str": ..., "ticker": ...}, "1": {...}, ...}
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def company_facts(cik: int) -> dict:
    # CompanyFacts API is on data.sec.gov subdomain
    return fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")


def company_submissions(cik: int) -> dict:
    """Fetch company metadata from SEC EDGAR submissions endpoint.

    Returns dict with keys including:
    - sic: SIC code (str, e.g. "7372")
    - sicDescription: Human-readable (e.g. "SERVICES-PREPACKAGED SOFTWARE")
    - category: Filing category
    - fiscalYearEnd: Month as MMDD string (e.g. "0630" for June)
    """
    return fetch_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")


# ── XBRL tag fallback lists ──────────────────────────────────────────
# Enriched from edgartools concept_mappings.json (MIT, 32K-filing study)
# and spike comparison across 10 industries. Tags are tried in order;
# _pick_first_units() returns the first that has 10-K/20-F data.
#
# See docs/spike-edgartools/SPIKE_EDGARTOOLS_REPORT.md for rationale.

IS_TAGS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "Revenue",
        "OperatingRevenue",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "RevenuesNetOfInterestExpense",
        "InterestAndDividendIncomeOperating",  # banks
    ],
    "cogs": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfServices",
        "CostOfSales",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
        "DirectOperatingCosts",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "sga": [
        "SellingGeneralAndAdministrativeExpense",
        # NOTE: if this tag misses, _resolve_sga_sum() will try summing
        # SellingAndMarketingExpense + GeneralAndAdministrativeExpense
    ],
    "rnd": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentCosts",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
        "ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost",
    ],
    "depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
        "DepreciationAmortizationAndAccretionNet",
    ],
    "ebit": [
        "OperatingIncomeLoss",
        "OperatingIncome",
        "IncomeLossFromContinuingOperationsBeforeInterestAndTaxes",
        # Last-resort proxy: pre-tax income — may include non-operating items (e.g. XOM commodity swings)
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestAndDebtExpense",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNet",
        # Utility/long-term debt fallbacks — LT interest only, understates if significant ST borrowings
        "InterestExpenseLongTermDebt",
        # Total interest incurred before capitalization — may overstate for capital builders (NEE, energy)
        "InterestCostsIncurred",
        # Cash-flow proxy: interest paid — approximates IS interest expense when no IS tag exists (NEE)
        "InterestPaidNet",
    ],
    "taxes": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxesPaidNet",
    ],
    "net_income": [
        "NetIncomeLoss",
        "NetIncome",
        "ProfitLoss",
    ],
    "eps_diluted": [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasic",
    ],
    "shares_diluted": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
}

# SGA component tags for summing when combined tag is missing (MSFT, etc.)
SGA_COMPONENT_TAGS = [
    ["SellingAndMarketingExpense", "GeneralAndAdministrativeExpense"],
    ["SellingExpense", "GeneralAndAdministrativeExpense"],
    ["MarketingExpense", "GeneralAndAdministrativeExpense"],
]

BS_TAGS = {
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashEquivalentsAtCarryingValue",
        "Cash",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "receivables": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
        "AccountsReceivableNet",
        "AccountsReceivableGross",
    ],
    "inventory": [
        "InventoryNet",
        "InventoryGross",
        "InventoryFinishedGoods",
    ],
    "total_assets": [
        "Assets",
        "AssetsTotal",
    ],
    "total_liabilities": [
        "Liabilities",
        "LiabilitiesTotal",
    ],
    "total_debt": [
        "LongTermDebt",
        # NOTE: if this tag misses, _resolve_total_debt_sum() will try
        # summing LongTermDebtNoncurrent + LongTermDebtCurrent
    ],
    "shareholder_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquityAttributableToParent",
        "EquityAttributableToParent",
    ],
}

# Debt component tags for summing when combined LongTermDebt tag is missing
DEBT_COMPONENT_TAGS = [
    ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
    ["LongTermDebtNoncurrent", "ShortTermBorrowings"],
    ["LongTermDebtNoncurrent", "DebtCurrent"],
]

# Depreciation fallback: look in CF adjustments if not on IS
DEPRECIATION_CF_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "Depreciation",
    "DepreciationAmortizationAndAccretionNet",
]

CF_TAGS = {
    "cfo": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditures",
        "PaymentsToAcquireProductiveAssets",
    ],
    "buybacks": [
        "PaymentsForRepurchaseOfCommonStock",
        "PaymentsForRepurchaseOfEquity",
    ],
    "dividends": [
        "PaymentsOfDividends",
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfOrdinaryDividends",
    ],
    "acquisitions": [
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
        "PaymentsToAcquireBusinessesAndInterestInAffiliates",
    ],
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


def upsert_company(
    cik: str,
    ticker: str,
    name: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    sic_code: str | None = None,
    fiscal_year_end_month: int | None = None,
):
    execute(
        """
        INSERT INTO company (cik, ticker, name, sector, industry, sic_code, fiscal_year_end_month)
        VALUES (:cik, :ticker, :name, :sector, :industry, :sic_code, :fy_end_month)
        ON CONFLICT (cik) DO UPDATE SET
            ticker=EXCLUDED.ticker,
            name=COALESCE(EXCLUDED.name, company.name),
            sector=COALESCE(EXCLUDED.sector, company.sector),
            industry=COALESCE(EXCLUDED.industry, company.industry),
            sic_code=COALESCE(EXCLUDED.sic_code, company.sic_code),
            fiscal_year_end_month=COALESCE(EXCLUDED.fiscal_year_end_month, company.fiscal_year_end_month)
    """,
        cik=cik,
        ticker=ticker,
        name=name,
        sector=sector,
        industry=industry,
        sic_code=sic_code,
        fy_end_month=fiscal_year_end_month,
    )


def upsert_filing(cik: str, form: str | None, accession: str | None, period_end: str | None) -> int | None:
    # Convert date objects to ISO format strings for SQLite compatibility
    from datetime import date

    if isinstance(period_end, date):
        period_end = period_end.isoformat()

    row = execute(
        """
        INSERT INTO filing (cik, form, accession, period_end)
        VALUES (:cik, :form, :accession, :period_end)
        ON CONFLICT (accession) DO UPDATE SET
            form = EXCLUDED.form,
            period_end = EXCLUDED.period_end
        RETURNING id
    """,
        cik=cik,
        form=form,
        accession=accession,
        period_end=period_end,
    ).first()
    return int(row[0]) if row else None


# Maximum staleness tolerance relative to the most-recent tag's data.
# A tag is accepted only if its most recent annual FY is within this many
# years of the overall frontier. Keeps stale tags (e.g. MA's old revenue
# tag, last filed FY2021) from blocking newer equivalents while still
# returning data for acquired/delisted companies where all tags are old.
_FRONTIER_TOLERANCE = 2


def _pick_first_units(facts: dict, tag_list: list[str]) -> dict | None:  # type: ignore[type-arg]
    """Return units dict for the first tag with recent 10-K/20-F annual data.

    Handles taxonomy changes where companies switch XBRL tags over time
    (e.g. MA, XOM, LMT moved to a different revenue tag after FY2021).
    The old tag still has historical 10-K entries, so a naive first-match
    would return stale data and write NULLs for every year after the switch.

    Algorithm:
      1. Scan all tags; record (tag, units_dict, max_fy) for each with any
         10-K/20-F annual entry. max_fy is the highest fiscal year present.
      2. Compute frontier = max(max_fy across all candidates).
      3. Filter: keep only candidates where max_fy >= frontier - tolerance.
         This allows recently-switched tags to be skipped while preserving
         data for acquired/delisted companies whose only tag is genuinely old.
      4. Return the units dict of the first surviving candidate, preserving
         tag_list priority order.

    The returned dict may contain multiple unit keys (e.g. "USD" and
    "USD/shares"). Callers use _annual_value() with a fixed unit key from
    STATEMENT_SCHEMAS, so extra keys are safely ignored.
    """
    f = facts.get("facts", {}).get("us-gaap", {})

    # Step 1: collect all candidates with their max annual FY
    candidates: list[tuple[dict, int]] = []  # (units_dict, max_fy)
    for t in tag_list:
        if t not in f:
            continue
        units = f[t]["units"]
        annual_fys = [
            e["fy"]
            for entries in units.values()
            for e in entries
            if e.get("form") in ("10-K", "20-F") and e.get("fy") is not None
        ]
        if not annual_fys:
            continue
        candidates.append((dict(units), max(annual_fys)))

    if not candidates:
        return None

    # Step 2: frontier = most recent FY seen across all candidate tags
    frontier = max(max_fy for _, max_fy in candidates)

    # Step 3 & 4: return first candidate within tolerance of frontier
    for units_dict, max_fy in candidates:
        if max_fy >= frontier - _FRONTIER_TOLERANCE:
            return units_dict

    return None


def _sum_annual_values(facts: dict, tag_groups: list[list[str]], unit_key: str, fy: int) -> float | None:
    """Sum values from multiple XBRL tags for a fiscal year.

    Tries each group in order. Within a group, ALL tags must have data
    for the sum to be valid. Returns the first successful group sum.
    Used for SGA (selling + G&A) and total_debt (LT + ST).
    """
    f = facts.get("facts", {}).get("us-gaap", {})
    for group in tag_groups:
        total = 0.0
        all_found = True
        for tag in group:
            if tag not in f:
                all_found = False
                break
            units = f[tag].get("units", {})
            val = _annual_value(units, unit_key, fy)
            if val is None:
                all_found = False
                break
            total += val
        if all_found:
            return total
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


def _insert_statement(filing_id: int, fy: int, stmt_type: str, units_cache: dict, facts: dict | None = None):
    """Generic statement insertion using schema configuration.

    Args:
        filing_id: ID of the filing record
        fy: Fiscal year
        stmt_type: Statement type key ('is', 'bs', or 'cf')
        units_cache: Nested dict with units data for each statement type
        facts: Raw CompanyFacts JSON for fallback summing logic
    """
    schema = STATEMENT_SCHEMAS[stmt_type]
    table: str = schema["table"]  # type: ignore[assignment]
    fields: list[str] = schema["fields"]  # type: ignore[assignment]
    units_map: dict[str, str] = schema["units"]  # type: ignore[assignment]

    # Build field values dynamically
    values: dict[str, object] = {"filing_id": filing_id, "fy": fy}
    for field in fields:
        unit_key = units_map[field]
        values[field] = _annual_value(units_cache[stmt_type][field], unit_key, fy)

    # ── Fallback enrichment (Option B from edgartools spike) ─────
    if facts is not None:
        # SGA: if combined tag missed, sum selling + G&A components
        if stmt_type == "is" and values.get("sga") is None:
            values["sga"] = _sum_annual_values(facts, SGA_COMPONENT_TAGS, "USD", fy)

        # total_debt: if combined LongTermDebt missed, sum LT noncurrent + current
        if stmt_type == "bs" and values.get("total_debt") is None:
            values["total_debt"] = _sum_annual_values(facts, DEBT_COMPONENT_TAGS, "USD", fy)

        # depreciation: if not on IS, look in CF adjustment section
        if stmt_type == "is" and values.get("depreciation") is None:
            depr_units = _pick_first_units(facts, DEPRECIATION_CF_TAGS)
            if depr_units:
                values["depreciation"] = _annual_value(depr_units, "USD", fy)

        # gross_profit: compute from revenue - cogs when not filed as a tag
        # (AMZN, NFLX, LLY don't tag GrossProfit as a separate line item)
        if stmt_type == "is" and values.get("gross_profit") is None:
            rev = values.get("revenue")
            cogs_val = values.get("cogs")
            if isinstance(rev, (int, float)) and isinstance(cogs_val, (int, float)):
                values["gross_profit"] = rev - cogs_val

    # Build SQL dynamically
    field_names = ", ".join(["filing_id", "fy"] + fields)
    placeholders = ", ".join([f":{name}" for name in ["filing_id", "fy"] + fields])
    sql = f"INSERT INTO {table} ({field_names}) VALUES ({placeholders})"

    execute(sql, **values)


def _parse_fiscal_year_end_month(fy_end: str | None) -> int | None:
    """Parse fiscal year end month from SEC submissions MMDD string.

    E.g. "0630" -> 6 (June), "1231" -> 12 (December).
    Returns None if unparseable.
    """
    if not fy_end or len(fy_end) < 2:
        return None
    try:
        return int(fy_end[:2])
    except (ValueError, TypeError):
        return None


def ingest_companyfacts_richer_by_ticker(ticker: str):
    t2c = ticker_map()
    cik = t2c.get(ticker.upper())
    if not cik:
        raise ValueError(f"No CIK found for {ticker}")
    facts = company_facts(cik)
    entity = facts.get("entityName", "")

    # Fetch SIC code + fiscal year end from submissions endpoint
    sic_code = None
    sic_description = None
    sector = None
    fy_end_month = None
    try:
        subs = company_submissions(cik)
        sic_code = subs.get("sic", None)
        sic_description = subs.get("sicDescription", None)
        sector = sic_to_category(sic_code) if sic_code else None
        fy_end_month = _parse_fiscal_year_end_month(subs.get("fiscalYearEnd"))
    except Exception as e:
        log.warning("Failed to fetch submissions for CIK %s: %s", cik, e)

    upsert_company(
        f"{cik:010d}",
        ticker.upper(),
        name=entity,
        sector=sector,
        industry=sic_description,
        sic_code=sic_code,
        fiscal_year_end_month=fy_end_month,
    )

    units_cache: dict[str, dict] = {"is": {}, "bs": {}, "cf": {}}
    for k, tags in IS_TAGS.items():
        units_cache["is"][k] = _pick_first_units(facts, tags)
    for k, tags in BS_TAGS.items():
        units_cache["bs"][k] = _pick_first_units(facts, tags)
    for k, tags in CF_TAGS.items():
        units_cache["cf"][k] = _pick_first_units(facts, tags)

    years_set: set[int] = set()
    for units, key in (
        (units_cache["is"]["revenue"], "USD"),
        (units_cache["is"]["eps_diluted"], "USD/shares"),
    ):
        if units and key in units:
            for item in units[key]:
                fy = item.get("fy")
                form = item.get("form", "")
                if fy and form in ("10-K", "20-F"):
                    years_set.add(int(fy))
    years = sorted(years_set)

    for fy in years:
        filing_id = upsert_filing(
            cik=f"{cik:010d}",
            form="10-K",
            accession=f"FACTS-{cik}-{fy}",
            period_end=f"{fy}-12-31",
        )
        if filing_id is None:
            log.warning("upsert_filing returned None for %s FY%s — skipping", ticker, fy)
            continue
        # Delete existing statement rows so re-ingest overwrites stale NULLs
        for tbl in ("statement_is", "statement_bs", "statement_cf"):
            execute(f"DELETE FROM {tbl} WHERE filing_id = :fid", fid=filing_id)  # nosec B608
        _insert_statement(filing_id, fy, "is", units_cache, facts=facts)
        _insert_statement(filing_id, fy, "bs", units_cache, facts=facts)
        _insert_statement(filing_id, fy, "cf", units_cache, facts=facts)
    return {"ticker": ticker.upper(), "cik": f"{cik:010d}", "years": years}
