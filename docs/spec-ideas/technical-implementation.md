# Common Investor - Technical Implementation Document

**Version:** 0.1.0 | **Date:** 2025-01-12 | **Source:** Deep code analysis

---

## 1. System Architecture Overview

### 1.1 Docker Compose Stack

```
┌─────────────────────────────────────────────────────┐
│                  DOCKER COMPOSE                      │
├──────────┬──────────┬──────────┬────────────────────┤
│ UI       │ API      │ Worker   │ Scheduler          │
│ Next.js  │ FastAPI  │ Celery   │ Celery Beat        │
│ :3000    │ :8080    │          │                    │
└────┬─────┴────┬─────┴────┬─────┴──────┬─────────────┘
     │          │          │            │
     │  ┌───────┴──────────┴────────────┘
     │  │                 │
  ┌──▼──▼────┐    ┌──────▼────┐
  │PostgreSQL│    │   Redis   │
  │(pgvector)│    │  (Broker) │
  └──────────┘    └───────────┘
```

**Services:**
- **postgres**: ankane/pgvector:latest - Data persistence with vector search
- **redis**: redis:7-alpine - Celery message broker
- **api**: Python 3.11 + FastAPI + Uvicorn - REST API
- **worker**: Python 3.11 + Celery - Background task execution
- **scheduler**: Python 3.11 + Celery Beat - Periodic tasks
- **ui**: Next.js + TypeScript - Web frontend

**Key Configuration (docker-compose.yml):**
- Database URL: `postgresql+psycopg2://ci:ci_pass@postgres:5432/ci_db`
- Redis URL: `redis://redis:6379/0`
- SEC User-Agent: Configurable via `SEC_USER_AGENT` env var
- API startup: Runs Alembic migrations before Uvicorn

---

## 2. Database Schema

### 2.1 Core Tables

**Company** (Primary Entity)
- `id` (PK), `cik` (UNIQUE), `ticker` (UNIQUE), `name`, `sector`, `industry`, `currency`

**Filing** (SEC Filings)
- `id` (PK), `cik`, `form`, `accession` (UNIQUE), `period_end`, `accepted_at`, `source_url`, `checksum`

**StatementIS** (Income Statement)  
- `id` (PK), `filing_id` (FK), `fy`, `revenue`, `cogs`, `gross_profit`, `sga`, `rnd`, `depreciation`, `ebit`, `interest_expense`, `taxes`, `net_income`, `eps_diluted`, `shares_diluted`

**StatementBS** (Balance Sheet)
- `id` (PK), `filing_id` (FK), `fy`, `cash`, `receivables`, `inventory`, `total_assets`, `total_liabilities`, `total_debt`, `shareholder_equity`

**StatementCF** (Cash Flow)
- `id` (PK), `filing_id` (FK), `fy`, `cfo`, `capex`, `buybacks`, `dividends`, `acquisitions`

**MetricsYearly** (Computed Metrics)
- `id` (PK), `company_id` (FK), `fy`, `roic`, `rev_cagr_5y`, `eps_cagr_5y`, `owner_earnings`, `coverage`, `net_debt`, `debt_equity`

**ValuationScenario** (Valuation Results)
- `id` (PK), `company_id` (FK), `ts`, `eps0`, `g`, `pe_cap`, `r`, `sticker`, `mos_pct`, `mos_price`, `owner_earnings0`, `payback_years`, `ten_cap_ps`, `strategy`

**MeaningNote** (Four Ms Analysis)
- `id` (PK), `company_id` (FK), `ts`, `text`, `source_url`, `section`, `evidence_type`

**AlertRule** (Price Alerts)
- `id` (PK), `user_id`, `company_id` (FK), `rule_type`, `threshold`, `enabled`

**PriceSnapshot** (Market Prices)
- `id` (PK), `company_id` (FK), `ts`, `price`, `source`, `currency`

---

## 3. Backend Structure

### 3.1 Module Organization

```
backend/app/
├── main.py                    # FastAPI app, CORS config
├── api/v1/routes.py           # All API endpoints
├── core/
│   ├── errors.py              # ApiError exception
│   └── logging.py             # Logging setup
├── db/
│   ├── models.py              # SQLAlchemy models
│   └── session.py             # DB connection, execute()
├── ingest/sec.py              # SEC EDGAR data fetching
├── metrics/compute.py         # CAGR, ROIC, owner earnings
├── valuation/
│   ├── core.py                # Sticker, MOS, Payback formulas
│   └── service.py             # Valuation orchestration
├── nlp/fourm/
│   ├── service.py             # Moat, Management, MOS analysis
│   └── sec_item1.py           # Meaning extraction
├── pricefeed/provider.py      # yfinance integration
├── alerts/engine.py           # Alert evaluation
└── workers/
    ├── celery_app.py          # Celery config + beat schedule
    └── tasks.py               # Background tasks
```

### 3.2 Database Session (db/session.py)

**Key Features:**
- **Parameterized queries:** All SQL via `execute(sql, **params)` using SQLAlchemy `text()`
- **Auto-commit transactions:** Uses `engine.begin()` context manager
- **Cursor management:** AutoClosingResult wrapper prevents SQLite commit errors
- **Test support:** Thread-local session override for test isolation

**Execute Function:**
```python
def execute(sql: str, **params):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        if result.returns_rows:
            rows = result.fetchall()  # Fetch immediately to close cursor
            return FetchedResult(rows)  # Convenience wrapper
        return AutoClosingResult(result)
```

---

## 4. API Endpoints (api/v1/routes.py)

### 4.1 Company Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/company/{ticker}/ingest` | Queue SEC data ingestion |
| GET | `/company/{ticker}` | Get company summary + latest IS |
| GET | `/company/{ticker}/metrics` | Get growth metrics (CAGR) |
| GET | `/company/{ticker}/timeseries` | Get all time series data |

### 4.2 Valuation Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/company/{ticker}/valuation` | Run valuation scenario |
| GET | `/company/{ticker}/fourm` | Get Four Ms analysis |
| POST | `/company/{ticker}/fourm/meaning/refresh` | Extract SEC Item 1 |

### 4.3 Alert Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/company/{ticker}/alerts` | Create alert rule |
| GET | `/company/{ticker}/alerts` | List alert rules |
| PATCH | `/alerts/{alert_id}` | Toggle alert enabled/disabled |
| DELETE | `/alerts/{alert_id}` | Delete alert |

### 4.4 Export Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/company/{ticker}/export/metrics.csv` | CSV export |
| GET | `/company/{ticker}/export/valuation.json` | JSON export |

---

## 5. Data Ingestion (ingest/sec.py)

### 5.1 SEC EDGAR Integration

**APIs Used:**
- Ticker Map: `https://www.sec.gov/files/company_tickers.json`
- Company Facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json`

**Headers:**
```python
SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", "CommonInvestor/0.1 you@example.com"),
    "Accept-Encoding": "gzip, deflate"
}
```

### 5.2 XBRL Tag Mapping

**Income Statement:**
- `revenue`: Revenues, SalesRevenueNet, RevenueFromContractWithCustomerExcludingAssessedTax
- `eps_diluted`: EarningsPerShareDiluted
- `ebit`: OperatingIncomeLoss
- `net_income`: NetIncomeLoss
- `shares_diluted`: WeightedAverageNumberOfDilutedSharesOutstanding

**Balance Sheet:**
- `cash`: CashAndCashEquivalentsAtCarryingValue
- `total_assets`: Assets
- `total_debt`: LongTermDebtNoncurrent, LongTermDebtCurrent, DebtCurrent
- `shareholder_equity`: StockholdersEquity

**Cash Flow:**
- `cfo`: NetCashProvidedByUsedInOperatingActivities
- `capex`: PaymentsToAcquirePropertyPlantAndEquipment, CapitalExpenditures
- `buybacks`: PaymentsForRepurchaseOfCommonStock

### 5.3 Ingestion Process

```python
def ingest_companyfacts_richer_by_ticker(ticker: str):
    # 1. Resolve ticker → CIK
    cik = ticker_map().get(ticker.upper())
    
    # 2. Fetch CompanyFacts JSON
    facts = company_facts(cik)
    
    # 3. Upsert company record
    upsert_company(f"{cik:010d}", ticker, facts.get("entityName"))
    
    # 4. Build units cache for tag lookup
    units_cache = {statement: {tag: _pick_first_units(facts, tag_list)
                               for tag, tag_list in TAGS.items()}
                   for statement, TAGS in [(\"is\", IS_TAGS), ...]}
    
    # 5. Extract fiscal years from 10-K/20-F forms
    years = {item["fy"] for units in [revenue, eps] 
             for item in units if item.get("form") in ("10-K", "20-F")}
    
    # 6. For each year: create filing + insert statements
    for fy in sorted(years):
        filing_id = upsert_filing(cik, "10-K", f"FACTS-{cik}-{fy}", f"{fy}-12-31")
        execute("INSERT INTO statement_is (...) VALUES (...)", ...)
        execute("INSERT INTO statement_bs (...) VALUES (...)", ...)
        execute("INSERT INTO statement_cf (...) VALUES (...)", ...)
```

---

## 6. Metrics Engine (metrics/compute.py)

### 6.1 Growth Metrics

**CAGR Formula:**
```python
def cagr(first: float, last: float, years: int) -> Optional[float]:
    return (last/first)**(1.0/years) - 1.0
```

**Multi-Window CAGR:**
```python
def compute_growth_metrics(cik: str):
    series = _fetch_is_series(cik)  # Get revenue, EPS by year
    return {
        "rev_cagr_5y": window_cagr(revenue, 5),
        "rev_cagr_10y": window_cagr(revenue, 10),
        "eps_cagr_5y": window_cagr(eps, 5),
        "eps_cagr_10y": window_cagr(eps, 10)
    }
```

### 6.2 ROIC Calculation

```python
def roic_series(cik: str):
    rows = _fetch_cf_bs_for_roic(cik)
    for r in rows:
        ebit, taxes, debt, equity, cash = r["ebit"], ...
        tax_rate = max(0.0, min(0.35, taxes/abs(ebit)))  # Capped 0-35%
        nopat = ebit * (1.0 - tax_rate)
        inv_cap = equity + debt - cash
        roic = nopat / inv_cap if inv_cap != 0 else None
```

### 6.3 Owner Earnings

```python
def owner_earnings_series(cik: str):
    rows = _fetch_cf_bs_for_roic(cik)
    return [{"fy": r["fy"], 
             "owner_earnings": r["cfo"] - r["capex"],
             "owner_earnings_ps": (r["cfo"] - r["capex"]) / r["shares"]}
            for r in rows]
```

### 6.4 Coverage Ratio

```python
def coverage_series(cik: str):
    rows = execute("SELECT fy, ebit, interest_expense FROM statement_is ...")
    return [{"fy": fy, "coverage": ebit / interest if interest != 0 else None}
            for fy, ebit, interest in rows]
```

---

## 7. Valuation Engine

### 7.1 Sticker Price (valuation/core.py)

**Formula:**
```python
def sticker_and_mos(inp: StickerInputs, mos_pct: float = 0.5):
    g = max(0.0, min(inp.g, 0.5))  # Cap growth at 50%
    future_eps = inp.eps0 * ((1.0 + g) ** 10.0)
    terminal_pe = min(inp.pe_cap, max(5.0, 2.0 * (g * 100.0)))
    future_price = future_eps * terminal_pe
    sticker = future_price / ((1.0 + inp.discount) ** 10.0)
    mos_price = sticker * (1.0 - mos_pct)
    return StickerResult(future_eps, terminal_pe, future_price, sticker, mos_price)
```

**Inputs:**
- `eps0`: Current diluted EPS
- `g`: Annual growth rate (default 0.15)
- `pe_cap`: P/E ratio cap (default 20)
- `discount`: Discount rate (default 0.15)

### 7.2 Ten Cap

```python
def ten_cap_price(owner_earnings_per_share: float) -> float:
    return owner_earnings_per_share / 0.10
```

### 7.3 Payback Time

```python
def payback_time(purchase_price: float, owner_earnings_ps: float, 
                 growth: float, max_years: int = 10) -> Optional[int]:
    cum = 0.0
    cur = owner_earnings_ps
    for year in range(1, max_years + 1):
        cum += cur
        if cum >= purchase_price:
            return year
        cur *= (1.0 + max(0.0, growth))
    return None  # Payback > max_years
```

### 7.4 Valuation Service (valuation/service.py)

**Orchestration:**
```python
def run_default_scenario(ticker: str, mos_pct: float = 0.5, 
                        g_override: float = None, ...):
    cik = get_cik(ticker)
    
    # Get latest EPS
    eps0 = latest_eps(cik)
    
    # Get owner earnings for payback
    oe_ps = latest_owner_earnings_ps(cik)
    
    # Use override or compute growth from historical CAGRs
    g = g_override or min(compute_growth_metrics(cik).values())
    
    # Run sticker calculation
    sticker_result = sticker_and_mos(StickerInputs(eps0, g, pe_cap, discount), mos_pct)
    
    # Compute payback and ten cap
    payback = payback_time(sticker_result.sticker, oe_ps, g)
    ten_cap = ten_cap_price(oe_ps)
    
    return {"inputs": {...}, "results": {...}}
```

---

## 8. Workers and Queue System

### 8.1 Celery Configuration (workers/celery_app.py)

```python
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("ci", broker=REDIS_URL, backend=REDIS_URL,
                    include=['app.workers.tasks'])

celery_app.conf.beat_schedule = {
    "snapshot-popular": {
        "task": "app.workers.tasks.snapshot_prices",
        "schedule": 6*60*60,  # Every 6 hours
        "args": (["MSFT", "AAPL", "AMZN"],)
    },
    "evaluate-alerts-daily": {
        "task": "app.workers.tasks.run_alerts_eval",
        "schedule": 24*60*60  # Daily
    }
}
```

### 8.2 Background Tasks (workers/tasks.py)

**Ingest Task:**
```python
@celery_app.task(name="app.workers.tasks.ingest_company")
def ingest_company(ticker: str):
    res = ingest_companyfacts_richer_by_ticker(ticker)
    print(f"Ingested {res}")
```

**Price Snapshot Task:**
```python
@celery_app.task(name="app.workers.tasks.snapshot_prices")
def snapshot_prices(tickers: list[str]):
    for t in tickers:
        snapshot_price_for_ticker(t)
```

**Alert Evaluation Task:**
```python
@celery_app.task(name="app.workers.tasks.run_alerts_eval")
def run_alerts_eval():
    return evaluate_alerts()
```

---

## 9. Alerts System (alerts/engine.py)

### 9.1 Price Snapshot

```python
def snapshot_price_for_ticker(ticker: str):
    p = price_yfinance(ticker)  # Fetch from yfinance
    if p is None: return None
    
    cid = get_company_id(ticker)
    execute("""
        INSERT INTO price_snapshot (company_id, price, source, currency)
        VALUES (:cid, :p, 'yfinance', 'USD')
    """, cid=cid, p=p)
```

### 9.2 Alert Evaluation

```python
def evaluate_alerts():
    rules = execute("""
        SELECT ar.id, c.ticker, ar.rule_type, ar.threshold, ar.enabled
        FROM alert_rule ar JOIN company c ON c.id=ar.company_id
        WHERE ar.enabled
    """).fetchall()
    
    triggered = []
    for rid, ticker, rtype, threshold, enabled in rules:
        p = price_yfinance(ticker)
        
        if rtype == "price_below_threshold" and p < threshold:
            triggered.append((rid, ticker, p, rtype))
        
        if rtype == "price_below_mos":
            val = run_default_scenario(ticker)
            mos = val["results"]["mos_price"]
            if p < mos:
                triggered.append((rid, ticker, p, rtype))
    
    # Log triggered alerts to meaning_note table
    for rid, ticker, p, typ in triggered:
        execute("""
            INSERT INTO meaning_note (company_id, ts, text, section, evidence_type)
            SELECT c.id, NOW(), :text, 'alerts', :typ FROM company c
            WHERE upper(c.ticker) = upper(:t)
        """, text=f"ALERT {typ}: price {p} triggered", typ=typ, t=ticker)
```

---

## 10. Price Feed (pricefeed/provider.py)

```python
def price_yfinance(ticker: str) -> Optional[float]:
    try:
        import yfinance as yf
        data = yf.Ticker(ticker).history(period="1d", interval="1d")
        if data is None or data.empty: return None
        return float(data["Close"].iloc[-1])
    except Exception:
        return None
```

---

## 11. Data Flow Diagrams

### 11.1 End-to-End Data Flow

```
User Input (Ticker)
      │
      ▼
┌──────────────────┐
│  FastAPI Route   │ POST /company/MSFT/ingest
│  (api layer)     │
└────────┬─────────┘
         │ enqueue_ingest(ticker)
         ▼
┌──────────────────┐
│  Celery Worker   │ ingest_company.delay(ticker)
│  (background)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  SEC EDGAR API   │ 1. Ticker → CIK
│  (ingest layer)  │ 2. Fetch CompanyFacts JSON
└────────┬─────────┘ 3. Parse XBRL tags
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │ INSERT: Company, Filing,
│   (persistence)  │ StatementIS/BS/CF
└──────────────────┘
```

### 11.2 Valuation Flow

```
User Request
      │
      ▼
GET /company/MSFT/valuation
      │
      ▼
┌──────────────────────────────┐
│  Valuation Service           │
│  run_default_scenario()      │
└────┬─────────────────────────┘
     │
     ├─► Query: latest_eps(cik)
     │
     ├─► Query: latest_owner_earnings_ps(cik)
     │
     ├─► Compute: compute_growth_metrics(cik)
     │
     ▼
┌──────────────────────────────┐
│  Valuation Core              │
│  sticker_and_mos()           │
│  payback_time()              │
│  ten_cap_price()             │
└────┬─────────────────────────┘
     │
     ▼
JSON Response to User
```

---

## 12. Implementation Status

### 12.1 ✅ Implemented

- Docker Compose orchestration with 5 services
- PostgreSQL database with 9 core tables
- SQLAlchemy ORM models with proper types
- FastAPI REST API with 15+ endpoints
- SEC EDGAR data ingestion via CompanyFacts API
- XBRL tag mapping for IS, BS, CF statements
- Parameterized SQL execution (SQL injection safe)
- Growth metrics: CAGR (5yr, 10yr) for revenue and EPS
- ROIC calculation with tax rate normalization
- Owner earnings computation (CFO - CapEx)
- Sticker Price formula with 10-year projection
- Margin of Safety calculation
- Payback Time with growth projection
- Ten Cap valuation
- Celery worker system with Redis broker
- Periodic tasks: price snapshots, alert evaluation
- Alert rules with price threshold and MOS triggers
- yfinance integration for market prices
- CSV and JSON export endpoints
- CORS configuration for localhost development

### 12.2 ❌ Not Implemented / Incomplete

- **Full XBRL Processing**: Arelle integration stubbed out
- **Four Ms Panel**: Moat, Management, Meaning analysis partially implemented
- **NLP/RAG**: SEC Item 1 extraction present but basic
- **Frontend UI**: Next.js structure exists but no actual components examined
- **User Authentication**: No auth middleware or user management
- **Rate Limiting**: No API rate limiting implemented
- **Input Validation**: Minimal validation on API endpoints
- **Error Handling**: Basic HTTPException usage, not comprehensive
- **Logging**: Basic setup, not production-grade
- **Tests**: Test infrastructure present but coverage unknown
- **XBRL Normalization**: Only basic extraction, missing advanced normalization
- **Multiple Statements Per Year**: Handles annual only, no quarterly support
- **Industry-Specific Strategies**: Generic valuation only
- **PDF Export**: Not implemented
- **Real-time Alerts**: Alerts logged to DB, no email/push notifications

---

## 13. Security Observations

### 13.1 ✅ Good Practices

- **SQL Injection Prevention**: All queries use parameterized execution via `execute(sql, **params)`
- **Environment Variables**: Database credentials and SEC User-Agent from env vars
- **CORS Configuration**: Explicitly configured for localhost:3000

### 13.2 ⚠️ Security Gaps

- **No Authentication/Authorization**: All endpoints publicly accessible
- **No Input Validation**: User inputs (ticker, parameters) not validated
- **No Rate Limiting**: API can be abused
- **HTTP Only**: No HTTPS enforcement (development setup)
- **No CORS Restrictions**: Wildcard allow_methods and allow_headers
- **Database Credentials**: Plain text in environment (acceptable for dev)
- **No Audit Logging**: User actions not logged
- **Error Information Leakage**: Stack traces may be exposed

---

## 14. Deployment Configuration

### 14.1 Environment Variables

**Required:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SEC_USER_AGENT`: SEC-compliant User-Agent header

**Optional:**
- `PYTHONPATH`: Set to `/app` in containers
- `NEXT_PUBLIC_API_URL`: API URL for frontend (default: http://localhost:8080)

### 14.2 Startup Sequence

1. **postgres** starts → Creates pgdata volume
2. **redis** starts → No dependencies
3. **api** starts → Waits 10s, runs `alembic upgrade head`, starts Uvicorn
4. **worker** starts → Connects to Redis, waits for tasks
5. **scheduler** starts → Connects to Redis, schedules periodic tasks
6. **ui** starts → Runs `npm install`, starts Next.js dev server

---

## 15. Key Technical Decisions

1. **Modular Monolith**: Single codebase with clear module boundaries for future microservices split
2. **SQLAlchemy with Raw SQL**: ORM for models, parameterized raw SQL for queries (flexibility + safety)
3. **Celery + Redis**: Industry-standard for Python background tasks
4. **CompanyFacts API**: Avoids complex XBRL parsing, simpler but less flexible
5. **No ORM Query Builder**: Direct SQL for performance and explicit control
6. **Synchronous Workers**: No async Celery workers, simpler debugging
7. **Single Database**: No read replicas or sharding, suitable for MVP scale
8. **No Caching Layer**: Direct database queries, acceptable for current load
9. **yfinance for Prices**: Free but rate-limited, good for development

---

**Document Status:** Based on actual code inspection as of 2025-01-12. All facts derived from source code analysis.
