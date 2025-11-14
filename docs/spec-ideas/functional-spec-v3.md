# Functional Specification — “Common Investor”
*A production-ready product spec distilled from the Rule #1 comprehensive notes.*

## 0) Product Summary

**Name**: Common Investor  
**One‑liner**: Analyze any public company using Rule #1 principles with explainable math, primary‑source data (EDGAR), and conservative valuation tools.

**Primary Outcome**: Help users determine whether a business is high quality (Four Ms), quantify its economics (Big Five), and decide if the **current price** offers a **Margin of Safety**.

---

## 1) Personas & Use Cases

**P1 — Serious Retail Investor (“DIY Analyst”)**  
- Wants defensible long‑term decisions, transparent inputs/outputs, and MOS alerts.

**P2 — Financial Content Creator/Coach**  
- Needs clean charts, exportable reports, and consistent methodology for teaching.

**P3 — PM/Engineer building quant screens**  
- Needs APIs & reproducible metrics to integrate into tools/dashboards.

**Key Jobs-to-be-Done**  
- “Tell me if this company passes the Four Ms.”  
- “Show me Big Five trends and where they break.”  
- “Calculate Sticker, MOS, Payback, Ten Cap using transparent inputs.”  
- “Alert me when price < MOS.”  
- “Export my analysis to share.”

---

## 2) High-Level Requirements

1. **Search** by company name or ticker; resolve to **CIK**.  
2. **Ingest** 10‑K/10‑Q filings (10+ years when available) with respectful rate limiting.  
3. **Normalize** statements and compute **canonical metrics**.  
4. **Valuation Engine**: Sticker, MOS, Payback, Ten Cap; optional DCF/multiples.  
5. **Four Ms** panel with qualitative prompts and quantitative proxies.  
6. **Explainability**: show formulas, intermediate numbers, and filing links.  
7. **Scenario** sliders/overrides for growth, PE, discount rate, CapEx normalization.  
8. **Signals**: simple technical overlays (optional).  
9. **Export**: PDF (report), CSV (metrics), JSON (API).  
10. **Watchlist & Alerts** for MOS thresholds (phase 2).

Out of Scope (v1): Brokerage integration, trade execution, options trading execution.

---

## 3) Detailed Feature Specs

### 3.1 Search & Resolve
- **Input**: free‑text (ticker, name).  
- **Process**: fuzzy match → preferred ticker → **CIK** map. Cache locally.  
- **Empty states**: no match, multiple matches; show selector.

**Acceptance Criteria**  
- Given “MSFT”, app finds Microsoft CIK and loads the latest 10‑K/10‑Q set within 3s on cache hit, 10–20s on cold load (dependent on network).

---

### 3.2 Data Ingestion Service
- **Sources**: SEC EDGAR (JSON/XBRL), price history provider (e.g., vendor/OSS).  
- **Scheduler**: daily refresh; backfill 10‑year history on first request.  
- **Compliance**: SEC fair access policy; descriptive **User‑Agent**; exponential backoff; concurrency caps.

**Data Canonicalization**
- `income_statement`: revenue, cogs, gross_profit, sga, rnd, depreciation, ebit, interest_expense, taxes, net_income, diluted_eps, shares_diluted.  
- `balance_sheet`: cash, receivables, inventory, total_assets, total_liabilities, total_debt, shareholder_equity.  
- `cash_flow`: cfo, capex, buybacks, dividends, acquisitions.

**Acceptance Criteria**  
- For companies with XBRL, app extracts **≥90%** of target fields; missing fields are flagged with “source not available” and sensible fallbacks.

---

### 3.3 Metrics Engine (Big Five & More)
**Computations (per year & TTM):**
- **ROIC**: `nopat = ebit * (1 - cash_tax_rate)`; `invested_capital = debt + equity - cash` (proxy, documented).  
- **Revenue CAGR**: 10y/5y/3y/1y.  
- **EPS CAGR**: same windows on diluted EPS.  
- **Owner Earnings**: `owner_earnings ≈ cfo - capex` (flag if maintenance estimate unknown).  
- **Leverage & Solvency**: net_debt, debt/equity, interest_coverage.

**UI**  
- Trend charts with tooltips showing raw values and formulas.  
- “Traffic lights” based on thresholds (configurable per industry).

**Acceptance Criteria**  
- Unit tests reproduce a reference example (Section 7 of summary) within rounding tolerance (<1%).

---

### 3.4 Valuation Engine
**Sticker Price**  
- Inputs: EPS₀ (diluted), growth g, future PE cap (min(2×g, hist avg, 30)), discount r (default 15%).  
- Output: **Sticker** and **MOS Price** (default 50%).  
- Show the **exact equation** and each input value.

**Payback Time**  
- Inputs: Owner Earnings₀, growth g (default: min of revenue/EPS CAGR, capped), compare to chosen base (market cap, equity value, or per‑share).  
- Output: **years to payback** and cash‑flow table.

**Ten Cap**  
- Inputs: Owner Earnings (TTM or median).  
- Output: **Ten Cap Value** vs market cap (and per‑share equivalent).

**Optional DCF** (cross‑check)  
- Two‑stage model (g1 for 5–10 yrs, terminal g2), discount r; display range.

**Acceptance Criteria**  
- For the Acme example, Sticker/MOS/Payback/Ten Cap match the walkthrough within tolerance.

---

### 3.5 Four Ms Panel

#### 3.5.1 Meaning — Circle of Competence: **Data Sources & Methods**

**Objective (P1 DIY Analyst):** Auto-fill as much of Section 2.1 as possible from authoritative sources; clearly separate facts (auto) from opinions (user input).

**Primary Sources (Phase 1 – built-in):**
- **SEC 10‑K Item 1 (Business)**: business model, products/services, customers, distribution channels.
- **SEC 10‑K Item 1A (Risk Factors)**: risk list; to be classified into categories (regulatory, tech disruption, customer concentration, etc.).
- **SEC 10‑K Item 7 (MD&A)**: narrative for revenue drivers and business mix.
- **10‑K/10‑Q Segment & Geography Notes**: revenue by category/geography (recurring vs transactional tag).
- **NAICS/SIC Codes**: industry classification for cyclicality heuristics.

**Supplementary Sources (Phase 2 – third-party & IR):**
- **Investor Relations (IR) decks & Annual Reports**: revenue stream charts, subscription vs transactional %.
- **Earnings call transcripts**: ARPU/churn/CAC/LTV disclosures when available.
- **Industry datasets** (e.g., IBISWorld/Statista) to validate customer segments, market size, and cyclicality context.
- **Macro data** (e.g., FRED/BEA) to tag industries as cyclical/defensive with supporting indicators.
- **ESG/Controversy feeds** (e.g., MSCI, Sustainalytics) to aid “proud to own” judgment.

**Manual/Assisted Inputs (Phase 1 & 2):**
- **ARPU / Retention / CAC / LTV** (rarely in 10‑K): user can enter or paste from transcripts/decks; system stores provenance (URL/date).
- **Personal alignment** (“Would I be proud to own this?”): free-text note + optional ESG snapshot.

**Extraction & NLP (Phase 1):**
- **Highlight & Summarize** Item 1 into a 2-line “What the company does” + bullets for products and customer segments.
- **Risk Classifier**: parse Item 1A headings → buckets (regulatory, disruption, supplier/customer concentration, FX, litigation).
- **Revenue Mix Builder**: from segment notes, compute % recurring (subscription) vs non-recurring, when determinable; otherwise flag as “unknown”.

**Cyclicality Heuristic (Phase 1):**
- Combine **NAICS** with **historical revenue volatility** and **gross margin volatility** → tag: *Cyclical/Moderate/Defensive*.
- Expose evidence panel (metrics + references).

**UI/UX (Phase 1):**
- **Meaning Panel** layout:
  - “What they do” summary (auto) with “View source” → opens 10‑K Item 1.
  - Industry & cyclicality chips with tooltips (NAICS + volatility evidence).
  - Revenue mix widget (recurring vs transactional) + confidence badge.
  - Risks checklist (auto-filled) with on/off toggles and notes.
  - “Personal fit” note area; optional ESG cards.
  - Provenance badges for each statement (filing name, period, page/section).

**Acceptance Criteria (Phase 1):**
- For a Fortune‑500 test set, extract Item 1/1A headings ≥90% of the time.
- Risk classifier achieves ≥80% precision on category labels in QA set.
- Revenue mix flag displays either computed % or “unknown (needs IR/transcript)” with one click to attach evidence.

**Phase 2 Enhancements:**
- IR deck scraper (PDF/slide OCR) for revenue stream charts; map to categories.
- Transcripts connector to extract KPIs (ARPU/churn/CAC/LTV) via pattern library; highlight confidence and allow user confirmation.
- ESG provider integration (read-only snapshot; click-through to provider).

**Phase 3 Enhancements:**
- Community annotations with credibility scoring.
- ML topic models that auto-detect new product lines or risk themes over time.

- **Meaning**: guided Q&A; saved notes; “understanding score.”  
- **Moat**: show ROIC persistence, margin stability, market share notes, qualitative moat type picker.  
- **Management**: comp & capital‑allocation cards; insider ownership (if available); interest coverage trend.  
- **MOS**: show MOS choice + rationale; dynamic link to valuation.

**Acceptance Criteria**  
- Users can save/edit notes; changes persist with company profile.

---

### 3.6 Signals (Optional, Read‑Only)
- Moving averages (50/200‑day), MACD histogram, simple stochastic.  
- **No** trading recommendations; just visuals and definitions.

---

### 3.7 Filings & Traceability
- Filings tab listing last 10‑K/10‑Q (links), proxy, 8‑K.  
- For each metric on hover: show **source fact** and fiscal period used.

**Acceptance Criteria**  
- From a chart point, user can click through to the period’s filing link.

---

### 3.8 Scenario & Sensitivity
- Sliders / inputs for **g, PE cap, r, MOS%, owner‑earnings normalization**.  
- “Conservative / Base / Optimistic” presets with saved scenarios.  
- Tornado chart for sensitivity (phase 2).

---

### 3.9 Exports & Sharing
- **PDF** report: overview + Four Ms + key charts + valuation.  
- **CSV**: raw yearly metrics table.  
- **JSON**: full analysis object (for API users).

---

### 3.10 Watchlist & Alerts (Phase 2)
- Add company to watchlist; set **MOS alert** (e.g., “Notify when price < MOS by 5%”).  
- Delivery: email / in‑app notifications.

---

## 4) Non‑Functional Requirements

- **Performance**: Cached loads <3s; cold loads gated by ingestion; show progress.  
- **Scalability**: Stateless services behind load balancer; background jobs for ingestion.  
- **Security**: OAuth for auth; least‑privilege; encrypted at rest/in transit; no PII beyond account.  
- **Reliability**: Retries, circuit breakers, data checksums.  
- **Compliance**: Display **“Not investment advice”** disclaimer; respect EDGAR policies.  
- **Observability**: Structured logs, metrics, traces; red‑flag dashboards.  
- **A11y/i18n**: WCAG‑AA basics; English v1.

---

## 5) System Architecture (Proposed)

- **Frontend**: React/Next.js; charts with Recharts; UI library (e.g., shadcn/ui).  
- **Backend**: Python/Node microservices: `ingest`, `metrics`, `valuation`, `report`.  
- **Storage**: Postgres (normalized facts & results), S3 (exports/cache).  
- **Jobs**: Worker queue for ingestion & refresh.  
- **APIs**: REST/GraphQL  
  - `GET /company/:ticker/summary`  
  - `GET /company/:ticker/metrics?window=10y`  
  - `POST /valuation/sticker` (body: eps0, g, pe_cap, r)  
  - `POST /valuation/payback` (owner_earnings0, g, basis)  
  - `POST /valuation/ten-cap` (owner_earnings)  
  - `GET /filings/:cik`

---

## 6) Data Model (Sketch)

- **Company**(id, cik, ticker, name, sector, currency)  
- **Filing**(id, cik, form, period, url, accepted_at)  
- **Fact**(id, filing_id, statement, tag, value, unit, fy, fq)  
- **MetricsYearly**(company_id, fy, revenue, eps, ebit, cfo, capex, debt, equity, cash, shares, …)  
- **Derived**(company_id, fy, roic, coverage, owner_earnings, …)  
- **ValuationScenario**(company_id, ts, eps0, g, pe_cap, r, sticker, mos_pct, mos_price, …)  
- **UserNote**(company_id, m_type, body, created_by, updated_at)

---

## 7) Edge Cases & Industry Notes

- **Financials**: switch to ROE, CET1, NIM; custom module.  
- **Cyclicals**: use **10‑yr medians**, warn users about cycle position.  
- **Negative EPS/FCF**: block Sticker/Payback; ask for alternative approach or larger MOS.  
- **M&A heavy**: treat goodwill/intangibles with caution; show organic vs acquired growth when possible.

---

## 8) QA Plan & Acceptance Tests

- **Deterministic Example**: Reproduce the “Acme Tools Inc.” example from the summary doc:  
  - ROIC ≈ 16.7%  
  - Sticker ≈ \$25.66 at r=15%, g=10%, PE=20  
  - MOS (50%) ≈ \$12.83  
  - Payback ≈ 7 years (owner_earnings₀=550, g=6%)  
  - Ten Cap Value = \$5.5B  
- **Data Integrity**: CFO + CFI + CFF ≈ ΔCash (± rounding) for each year.  
- **UI**: All formula cards display inputs and sources; hover reveals period; click opens filing.

---

## 9) Release Plan

**Phase 1 (MVP)**  
- Search, ingest, metrics, Sticker/MOS, Payback, Ten Cap, Four Ms notes, exports.

**Phase 2**  
- Watchlist/alerts, DCF, sensitivity analysis, sector specializations, richer signals.

**Phase 3**  
- Public API, mobile app, community features.

---

## 10) Open Questions

1. Which price/history vendor for reliable EOD prices?  
2. Do we standardize all currency to USD or display native + USD?  
3. How to estimate **maintenance** vs **growth** CapEx defensibly (footnote parsing? heuristics?)  
4. Will we support ADRs and foreign GAAP mappings at MVP?

---

## 11) Appendix — Mapping Rule #1 → Features

| Rule #1 Concept | “Common Investor” Feature | Algorithm/Data |
|---|---|---|
| Meaning | Understanding Questionnaire | Saved notes, risk tags, links to Item 1 of 10‑K |
| Moat | Moat Heatmap | ROIC persistence, margin stability, market share notes |
| Management | Scorecard | Interest coverage trend, buyback quality, insider ownership |
| MOS | MOS Price | Sticker × (1 − MOS%) |
| Big Five | Metrics Dashboards | ROIC, CAGR(Rev/EPS), Owner Earnings, Leverage |
| Payback | Payback Calculator | Owner earnings growth table vs basis |
| Ten Cap | Ten Cap Calculator | Owner earnings ÷ 0.10 |
| Signals | Technical Overlays | MA(50/200), MACD, stochastic |
| Traceability | Filings Tab | EDGAR links, period mapping |

---

**End of Specification**

## 12) Data Providers & Integrations (Tracking & Phasing)

- **Primary (Phase 1):** SEC EDGAR (10‑K/10‑Q/Proxy), NAICS/SIC registries; price history vendor (EOD).  
- **Supplementary (Phase 2):** IR websites (presentations/annual reports), earnings call transcripts provider, industry datasets (market size & structure), macro (FRED/BEA), ESG rating providers.  
- **Governance & Compliance:** Respect robots.txt & terms; store **provenance** (URL, section, date) for each extracted fact; display provider attribution in UI.  
- **Feature Flags:** Each integration is behind a feature flag to ensure fallbacks are in place when a provider is unavailable.