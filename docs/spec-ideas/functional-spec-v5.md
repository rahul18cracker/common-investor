# Common Investor — Functional Specification (v5)

**Purpose:** This version adds a **Qualitative Analysis (Agent-Ready)** section that integrates with the existing quantitative pipeline. It clarifies **what is available in Phase 1**, how an **AI research agent** can access it, and **what is missing** (plus how to obtain or derive it in later phases or via research).

---

## 0) Change Log (v5)
- Added **§3.5A Qualitative Research (Agent-Ready Data Plan)** with data lineage, APIs, storage, and acceptance criteria.
- Added **§3.5A.1 Available Now (Phase 1)** — enumerates each qualitative-relevant metric/feature and how to access it.
- Added **§3.5A.2 Missing / To‑Be‑Built** — clearly marks gaps and whether they are (a) derivable from existing quantitative data, (b) agent‑researched, or (c) Phase 2 integrations.
- Added **schemas & export** pointers for agent outputs compatible with `qualitative-analysis-v2.md` (business_profile.json, unit_economics.json, industry.json, moat.json, management.json, peers.json, risks.json, thesis.json).

---

## 3) Detailed Feature Specs (Addendum)

### 3.5A Qualitative Research (Agent‑Ready Data Plan)

**Goal:** Enable a research agent to produce a complete qualitative picture using **built‑in** data first and to clearly know where **manual research** or **Phase 2** integrations are required.

#### 3.5A.0 Concepts (recap)
- **Meaning (Business profile)** — “What the company does,” segments/geographies, recurrence, risk headings, and provenance.
- **Moat** — durability via proxies such as ROIC persistence and margin stability; textual evidence for switching costs, network effects, brand, regulatory assets.
- **Management** — capital allocation behavior, incentives/alignment, governance.
- **Industry** — structure, cyclicality, pricing power at an industry level.
- **Risks & Monitoring** — risk categories and alert triggers.

---

#### 3.5A.1 Available Now (Phase 1) — *What the Agent Can Use Today*

> **How to access:** unless noted otherwise, use REST endpoints under `/api/v1` and the normalized tables in Postgres.

| Feature / Metric (Qual use) | Definition / Notes | DB Source (tables/cols) | API Access | Agent Usage Pattern |
|---|---|---|---|---|
| **Income Statement core** (revenue, COGS, gross profit, EBIT, EPS diluted, net income) | Base for unit economics & margin stability | `StatementIS` (`revenue`, `cogs`, `gross_profit`, `ebit`, `eps_diluted`, `net_income`, `shares_diluted`) | `GET /company/{ticker}` (latest), `GET /company/{ticker}/timeseries` (multi‑year) | Pull for business model narrative and trend charts; compute gross/operating margin trajectories. |
| **Balance Sheet core** (cash, total assets/liabilities, total debt, equity) | Resilience & leverage proxies | `StatementBS` (`cash`, `total_assets`, `total_liabilities`, `total_debt`, `shareholder_equity`) | `GET /company/{ticker}/timeseries` | Use for leverage/solvency commentary (e.g., net debt, debt/equity). |
| **Cash Flow core** (CFO, CapEx, buybacks, dividends, acquisitions) | Capital allocation signals; cash conversion | `StatementCF` (`cfo`, `capex`, `buybacks`, `dividends`, `acquisitions`) | `GET /company/{ticker}/timeseries` | Discuss payout discipline, reinvestment mix, buyback quality. |
| **Computed metrics (yearly)** — **ROIC**, **owner earnings**, **coverage**, **rev/eps CAGR** | Moat proxies & growth quality | `MetricsYearly` (`roic`, `owner_earnings`, `coverage`, `rev_cagr_5y`, `eps_cagr_5y`, `net_debt`, `debt_equity`) | `GET /company/{ticker}/metrics` (growth); `GET /company/{ticker}/timeseries` (series) | ROIC persistence, revenue/EPS growth quality, interest coverage. |
| **Valuation scenarios** (Sticker, MOS, Payback, Ten Cap) | Guardrails for MOS/stance | `ValuationScenario` (various) | `POST /company/{ticker}/valuation` | Reference MOS/valuation context in qualitative “stance” and falsifiers. |
| **Meaning extraction (Item 1)** | Auto‑summary & notes; creates evidence records | `MeaningNote` (`text`, `section`, `source_url`) | `POST /company/{ticker}/fourm/meaning/refresh`, `GET /company/{ticker}/fourm` | Seed **business profile** and **risk headings**; attach provenance links. |
| **Risk headings (Item 1A)** | Headline risks (unclassified) | `MeaningNote` (`section="risk"`) | `GET /company/{ticker}/fourm` | Feed **risks.json** → categorize manually if classifier not enabled. |
| **Price snapshots + alerts** | In‑app alerts (price < MOS/threshold) | `PriceSnapshot`, `AlertRule` | `/company/{ticker}/alerts` (CRUD) | Use for monitoring triggers; price series is snapshots (not full EOD history). |
| **Exports** | CSV metrics; JSON valuation | N/A (API‑built) | `/company/{ticker}/export/metrics.csv`, `/company/{ticker}/export/valuation.json` | Assemble the **agent bundle** with quantitative attachments. |

**Notes for agents**
- Always cache multi‑year series from `timeseries` to compute **volatility** (gross margin, revenue) used in cyclicality heuristics.  
- When a field is truly unavailable, emit `"unknown"` and create a follow‑up task (see §3.5A.3).

---

#### 3.5A.2 Missing / To‑Be‑Built — *How to Cover the Gaps*

| Missing qualitative item | Why it matters | Status | How to obtain in v5 | Long‑term plan (Phase) |
|---|---|---|---|---|
| **NAICS/SIC codes** (canonical industry tag) | Anchor for industry mapping & cyclicality chips | Not ingested | Agent: fetch from public registry or SEC header and store as a `MeaningNote` (temp). | Add NAICS/SIC registry ingestion + map to `Company.industry` (Phase 1 provider hookup). |
| **Segment & geography breakdown** (revenue mix; **recurring vs transactional** flag) | Business profile; recurrence signal | Not parsed from notes | Derive partial from MD&A/Item 1 narrative; agent marks confidence. | Build note parser for segment/geography footnotes; store breakdown; expose via `/timeseries` (Phase 2). |
| **Item 1A risk classifier (categorization)** | Normalized **risks.json** output | Headings only (no classifier) | Agent labels risks into categories with short evidence quotes. | Implement classifier (regex+ML) and persist normalized categories (Phase 2). |
| **Peer set (top 3)** | Required for `peers.json` and scorecard | No peer mapping yet | Agent proposes initial peer list with justification; store in notes. | Add peer‑resolution (NAICS+size+overlap) + peer table; UI override (Phase 2). |
| **Insider ownership & comp** (Proxy/DEF 14A) | Management alignment | Provider listed; ingestion not wired | Agent extracts from latest Proxy PDF/HTML; add to `management.json`. | Implement Proxy parser/ingestion; persist (`insider_ownership`, `comp_metrics`) (Phase 2). |
| **Transcripts (earnings calls)** | Capital allocation intent; KPIs | Not integrated | Agent pulls quotes for incentives/strategy; add to `management.json`. | Add transcripts connector; KPI pattern library (ARPU/churn/CAC/LTV) (Phase 2). |
| **Industry & macro datasets** | Industry pricing power, cyclicality context | Not integrated | Agent provides brief industry verdict using public sources. | Integrate selected industry/macro providers (Phase 2). |
| **Historical price series (EOD)** | Additional risk overlays | Snapshots only | Optional: agent fetches EOD for specific analyses. | Add vendor adapter for EOD history; cache & chart (Phase 2). |
| **Maintenance vs growth CapEx** | Cleaner owner‑earnings view | Open question | Agent flags unknown; may infer directional notes from MD&A. | Footnote parsing / heuristics toggled by flag (Phase 2). |

---

#### 3.5A.3 Agent Output & Storage Mapping

- Agent produces the **v2 JSON bundle**:  
  `business_profile.json`, `unit_economics.json`, `industry.json`, `moat.json`, `management.json`, `peers.json`, `risks.json`, `thesis.json`.
- **Numbers** tie back to `Statement*` + `MetricsYearly`.  
- **Textual evidence** (quotes, URLs, section names) is persisted as **`MeaningNote`** rows (`company_id`, `section`, `text`, `source_url`).  
- Exports: deliver CSV/valuation JSON via existing endpoints; a combined “Qual‑Quant Bundle” export endpoint can aggregate all JSONs in a zip in Phase 2.

---

#### 3.5A.4 API Quick Reference (for Agents)

```
# Ingest & refresh core data
POST /api/v1/company/{ticker}/ingest
POST /api/v1/company/{ticker}/fourm/meaning/refresh

# Quantitative substrate
GET  /api/v1/company/{ticker}               # latest snapshot
GET  /api/v1/company/{ticker}/timeseries    # multi-year IS/BS/CF series
GET  /api/v1/company/{ticker}/metrics       # ROIC, CAGR, coverage, owner earnings

# Valuation & exports
POST /api/v1/company/{ticker}/valuation
GET  /api/v1/company/{ticker}/export/metrics.csv
GET  /api/v1/company/{ticker}/export/valuation.json

# Qual bundle (current)
GET  /api/v1/company/{ticker}/fourm         # notes + risk headings
```

---

#### 3.5A.5 Acceptance Criteria (Phase 1)

1. For a 25‑name pilot set, **Meaning refresh** succeeds; Item 1 summary and Item 1A headings saved as `MeaningNote` entries.  
2. Agent can populate `business_profile.json`, `moat.json` (numeric proxies + notes), and `risks.json` (headings) using only Phase 1 endpoints.  
3. Agent can compute cyclicality verdict using **revenue/gross margin volatility** from `timeseries`.  
4. Peer scorecard is created with a proposed peer set (human‑reviewed).  
5. A combined export (CSV + valuation JSON + agent bundle) is available via UI actions; if a single ZIP endpoint is unavailable, the UI provides per‑file downloads.

---

## 9) Release Plan (aligned milestones)
- **Phase 1 (MVP):** Search, ingest, metrics, Sticker/MOS, Payback, Ten Cap, Four Ms notes, exports, **Qualitative Agent outputs (bundle, manual peers, manual risk categorization)**.
- **Phase 2:** Watchlist/alerts, DCF & sensitivity, **NAICS/SIC ingest**, **segment/geography parser**, **transcripts connector**, **industry/macro providers**, **proxy ingestion**, EOD price history, ZIP export for the qual‑quant bundle.
- **Phase 3:** Public API, mobile, community annotations, ML topic detection.

---

## 12) Data Providers & Integrations (clarified)
- **Primary (Phase 1):** SEC EDGAR (10‑K/10‑Q/**Proxy**), NAICS/SIC registry (to be wired), price history vendor (snapshots in MVP).  
- **Supplementary (Phase 2):** IR decks, earnings call transcripts, industry datasets, macro (FRED/BEA), ESG ratings.

---

## 13) Appendix — Agent Mapping Cheatsheet

**From Quantitative → Qualitative**  
- ROIC, coverage, owner earnings → **Moat proxies** (durability & resilience).  
- Revenue/EPS CAGR → **Growth quality** (context for valuation guardrails).  
- CFO/capex/dividends/buybacks → **Capital allocation** narrative (management).  
- Price snapshots + valuation outputs → **Monitoring triggers** and **stance**.

**Agent must research** (until integrations land)  
- NAICS/SIC (if not ingested), segments/geographies recurrence %, peer set, risk categorization, insider ownership/comp, transcripts insights, and industry/macro context.