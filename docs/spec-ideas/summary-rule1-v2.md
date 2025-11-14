# Phil Town’s *Rule #1* — Comprehensive Notes, Methods, and Worked Examples
*A deeply detailed playbook to implement Rule #1 investing logic for the “Common Investor” app.*

> **Purpose of this document**  
> This is a **practitioner-grade breakdown** of Phil Town’s Rule #1 methods and how they translate into product features and computations for a web app that analyzes public companies. It consolidates the qualitative and quantitative framework (the **Four Ms**, **Big Five Numbers**, and **Valuation Methods**) into step-by-step checklists, precise formulas, EDGAR data mappings, edge cases, and fully worked examples you can reproduce and test.

> **Disclaimer**  
> This material is an interpretation synthesized from publicly available summaries of Rule #1 ideas and widely used valuation practices. It’s intended for educational/product-design purposes, **not** investment advice. Numbers used in examples are **illustrative** and not tied to real companies. Always verify with primary sources (SEC filings).

---

## Table of Contents

1. Philosophy & Mental Models  
2. The Four Ms (Meaning, Moat, Management, Margin of Safety)  
   2.1 Meaning — Circle of Competence Checklist  
   2.2 Moat — Types, Proxies, and Red Flags  
   2.3 Management — Quality Indicators, Owner-Orientation, Incentives  
   2.4 Margin of Safety — Why 50% Buffer Is Common  
3. The Big Five Numbers  
   3.1 ROIC  
   3.2 Revenue (Sales) Growth  
   3.3 EPS Growth  
   3.4 Free Cash Flow (Owner Earnings)  
   3.5 Debt & Solvency (Debt/Equity, Net Debt, Interest Coverage)  
4. Valuation Methods  
   4.1 “Sticker Price” (Rule #1 style: Future EPS × Future PE, discounted)  
   4.2 Margin of Safety Price (MOS)  
   4.3 Payback Time (Cash-Return Horizon)  
   4.4 Ten Cap (Owner-Earnings Yield @ 10%)  
   4.5 Cross-Checks: DCF & Multiples  
5. Signals & Timing (Secondary)  
6. EDGAR/XBRL Data Mapping (10‑K/10‑Q line items & common alternatives)  
7. Worked Example (End-to-End)  
8. Implementation Notes for “Common Investor”  
9. Formula Reference (Cheat Sheet)  
10. Edge Cases & Anti-Patterns  
11. QA/Validation: Sanity Tests & Unit Checks  
12. Glossary

---

## 1) Philosophy & Mental Models

- **Rule #1**: *Don’t lose money.* **Rule #2**: *Don’t forget Rule #1.*  
- **Buy wonderful businesses** at prices that build in **safety**. Think like an owner.  
- Prioritize **quality + price**: only invest when **all Four Ms** check out and the **price is below** a conservatively estimated value (MOS).  
- Focus on **long-term compounding** (target often ~15% annualized) rather than trading hype or short-term noise.

---

## 2) The Four Ms

### 2.1 Meaning — Circle of Competence Checklist
**Goal**: Only buy what you truly understand.

**Guiding questions (record answers in app):**
- What does the company do? Who are its customers? Why do they buy?  
- Which industry is the company in ? what type of business is it ? is it cyclical ?
- What are the primary revenue streams? Subscription vs usage vs hardware vs services?  
- What are the core unit economics (ARPU, gross margin, retention, CAC/LTV)?  
- Key risks: regulation, commoditization, technological disruption, supplier concentration, customer concentration.  
- Would you be proud to own this business for 10+ years?

**App implementation ideas:**
- “**Understanding Score**” panel fed by structured Q&A prompts.  
- Link to company’s business segment disclosures (10‑K Item 1: Business).  
- Maintain a **risk checklist** (toggle known risks, see valuation auto-tighten when risks high).

---

### 2.2 Moat — Types, Proxies, and Red Flags
**Common moat types:**
- **Brand** (pricing power, repeat purchase)  
- **Network Effects** (value rises with users; switching deterrent)  
- **Cost Advantage** (economies of scale, process, supply)  
- **Switching Costs** (enterprise workflow/learning lock-in)  
- **Toll Bridge / Regulatory** (exclusive assets, licenses, rights)  
- **Patents / IP**

**Quant/qual proxies the app can surface:**
- **High, durable ROIC** over 10 yrs (≥15% consistently is strong).  
- **Stable or rising gross margin** → pricing power.  
- **Low churn/high retention** for subscription businesses.  
- **Market share** gains over multi-year windows.  
- **R&D output** (patents, approvals) **relative to spend**.  
- **Negative signals**: price wars, rapidly compressing margins, high incremental marketing just to hold share.

**UI:**
- Moat “heatmap” with tooltips referencing the relevant metrics.  
- Time‑series charts for margin stability and ROIC persistence.

---

### 2.3 Management — Quality Indicators
**Owner-orientation & integrity indicators:**
- Clear, *plain‑English* letters; consistent strategy; realistic guidance.  
- **Capital allocation**: sensible buybacks (when shares undervalued), prudent M&A, dividends only when excess cash.  
- **Incentives** aligned with long‑term value (not solely revenue/stock price).  
- **Skin in the game** (insider ownership), low related‑party issues, clean auditor history.  
- Response in downturns (cost discipline vs value destruction).

**Data hooks for the app:**
- 10‑K/Proxy statements: comp structure, share repurchases, related-party transactions.  
- Insider transactions (Form 4), auditor opinions, restatements.

---

### 2.4 Margin of Safety — Why a Big Buffer
- Forecasts are **imperfect**; MOS covers errors in growth, margins, or macro.  
- **50% discount** to intrinsic value is common in Rule #1 practice.  
- Lower certainty (new business models, cyclicals) ⇒ **require larger MOS**.

---

## 3) The Big Five Numbers

> These quantify quality & consistency. Wherever possible, compute across **10, 5, 3, 1‑year** windows and show **CAGR** and **volatility**.

### 3.1 ROIC (Return on Invested Capital)
**Purpose**: Measures how efficiently the company turns invested capital into after‑tax operating profit.

**Core formula (one common variant):**
- **ROIC = NOPAT ÷ Invested Capital**  
- **NOPAT = EBIT × (1 − Cash Tax Rate)**  
- **Invested Capital** (operating) ≈ Net Working Capital + Net PPE + Other Operating Assets − Non‑interest‑bearing Liabilities  
  - Practical proxy: **(Total Debt + Shareholders’ Equity − Cash & Equivalents)** (be consistent)

**Targets (heuristic):**
- **≥15%** sustained = strong; **10–15%** decent; **<10%** mediocre (context matters by industry).

**Notes:**
- Use **averages** (e.g., 2‑point or 5‑point average) for capital to reduce noise.  
- Exclude non‑operating assets where possible.

---

### 3.2 Revenue (Sales) Growth
**CAGR Formula:**
- **CAGR = (Ending / Beginning)^(1/n) − 1**

**What to watch:**
- **Consistency** more than raw speed.  
- Compare to **industry growth**; identify **mix shifts** (segment disclosures).

---

### 3.3 EPS Growth
- Same **CAGR** approach on **diluted EPS** (from continuing ops).  
- Adjust for big **one‑offs** (impairments, tax reform spikes).  
- Share count trends matter (buybacks can boost EPS). Highlight this in the app as to how many times this happens in the last 10 years.

---

### 3.4 Free Cash Flow (Owner Earnings)
**Owner Earnings (Buffett‑style proxy):**  
- **Owner Earnings ≈ Cash From Operations − Maintenance CapEx**  
- If maintenance CapEx not disclosed, conservative proxy is **total CapEx**.

**Why it matters:**  
- Cash drives value. Earnings can mislead.  
- Use **trailing 12 months** and **multi‑year medians** to smooth cycles.

---

### 3.5 Debt & Solvency
**Key ratios:**
- **Net Debt = (Short + Long Debt) − Cash**  
- **Debt/Equity** (context by industry)  
- **Interest Coverage = EBIT ÷ Interest Expense**  
  - **>5×** comfortable; **2–5×** cautious; **<2×** risky.

**Watch:**
- **Maturity wall** concentration; floating vs fixed rates; covenants.  
- For banks/insurers, use **capital ratios** rather than generic leverage.

---

## 4) Valuation Methods

> Combine multiple lenses; require **MOS** before acting.

### 4.1 “Sticker Price” (Rule‑of‑Thumb Intrinsic)
**Steps (10‑year horizon is common in Rule #1):**
1. **Current EPS** (diluted).  
2. **Growth rate (g)** (conservative, cross‑check historical vs TAM/maturity).  
3. **Future EPS (Year 10) = EPS₀ × (1+g)¹⁰**.  
4. **Future PE** (Rule #1 often uses **min(2×g, historical PE, 30)** as a cap).  
5. **Future Price (Year 10) = Future EPS × Future PE**.  
6. **Present Value (“Sticker Price”) = Future Price ÷ (1 + r)¹⁰**, with **r** your required return (often **15%**).

**Interpretation:** If market price < MOS price (see 4.2), stock may be “on sale”.

---

### 4.2 Margin of Safety (MOS) Price
- **MOS Price = Sticker Price × (1 − MOS%)**  
- Rule #1 convention: **MOS% ≈ 50%** (tighten/loosen based on certainty).

---

### 4.3 Payback Time
**Question**: If I buy today, **how many years** until cumulative **Owner Earnings** (FCF) return my purchase price?

**Process:**
1. Start with **Owner Earnings₀** (base year).  
2. Apply **conservative growth** each year (or flat if uncertain).  
3. Sum yearly cash flows until sum ≥ purchase price.  
4. **Target**: ~**7–8 years** or less is attractive by Rule #1 conventions.

**Use cases:** Useful reality check vs DCF and Sticker/MOS.

---

### 4.4 Ten Cap (10% Owner‑Earnings Yield)
- **Value = Owner Earnings ÷ 0.10**  
- Compare current **market cap** (or enterprise value variant) to this “Ten Cap Value.”  
- If market cap « Ten Cap value, attractive (all else equal).

**Notes:**  
- For capital‑intensive or volatile cash flows, use **multi‑year median** owner earnings.

---

### 4.5 Cross‑Checks: DCF & Multiples
**DCF**: Build conservative cash‑flow forecasts, use a robust **discount rate**; triangulate with Sticker/MOS.  
**Multiples**: Cross‑check with **EV/EBIT**, **P/FCF**, **P/E** vs **own history and peers** (beware of apples‑to‑oranges).

---

## 5) Signals & Timing (Secondary)
- Only evaluate signals **after** the business passes the Four Ms & valuation.  
- Tools: **moving averages (50/200‑day)**, **MACD**, **stochastic** (optional).  
- **Entry**: when price **falls below MOS** and signals are not flashing major deterioration.  
- **Exit**: business quality deteriorates, price far **exceeds** intrinsic, or better opportunity arises.

---

## 6) EDGAR/XBRL Data Mapping (Line Items)

> “Common Investor” will compute from **primary sources**. Mapping can vary by taxonomy; always reconcile definitions for consistency.

**Core filings:**  
- **10‑K** (annual), **10‑Q** (quarterly), **8‑K** (events), **Proxy (DEF 14A)**, **Form 4** (insiders).  
- **Ticker → CIK** mapping to query company filings.

**Typical line items (or close proxies):**
- **Income Statement**: Revenue, COGS, Gross Profit, SG&A, R&D, Depreciation & Amortization, Operating Income (EBIT), Interest Expense, Income Tax Expense, Net Income (diluted EPS).  
- **Balance Sheet**: Cash & Equivalents, Short/Long‑Term Debt, Total Assets, Total Liabilities, Shareholders’ Equity, Inventories, Receivables, Payables.  
- **Cash Flow**: **Net Cash from Operating Activities (CFO)**, **Capital Expenditures (CapEx)**, Share Repurchase, Dividends, Acquisitions.

**Derivations used in this doc:**
- **NOPAT** = EBIT × (1 − tax rate).  
- **Owner Earnings** ≈ CFO − Maintenance CapEx (use total CapEx as conservative proxy).  
- **Invested Capital** ≈ (Total Debt + Equity − Cash).  
- **Interest Coverage** = EBIT / Interest Expense.

---

## 7) Worked Example (End‑to‑End, Hypothetical Numbers)

**Company**: *Acme Tools Inc.* (ATI)  
**Today’s price**: \$40/share, **Shares**: 100M ⇒ **Market Cap** \$4.0B

**Selected financials (TTM or last FY):**
- Diluted **EPS₀** = \$2.00  
- **CFO** = \$850M; **CapEx** = \$300M ⇒ **Owner Earnings₀** ≈ \$550M  
- **EBIT** = \$900M; **Interest** = \$120M ⇒ **Interest Coverage** = 7.5×  
- **Tax Rate (cash)** ≈ 22% ⇒ **NOPAT** = \$900M × (1 − 0.22) = **\$702M**  
- **Debt** = \$2.0B; **Cash** = \$0.8B; **Equity** = \$3.0B  
  - **Invested Capital (proxy)** = 2.0 + 3.0 − 0.8 = **\$4.2B**  
  - **ROIC** ≈ 702 / 4,200 = **16.7%** (strong)  
- **Revenue growth** 10‑yr CAGR ≈ 9%; **EPS** 10‑yr CAGR ≈ 11% (consistent)

### 7.1 Sticker Price (10‑yr view)
Assumptions (conservative):  
- **g** = 10% (below historical 11%)  
- **Future EPS (Y10)** = 2.00 × (1.10)¹⁰ = 2.00 × 2.5937 = **\$5.19**  
- **Future PE** = min(2×g, hist PE, 30) ⇒ min(20, 24, 30) = **20**  
- **Future Price (Y10)** = 5.19 × 20 = **\$103.8**  
- **Discount r** = 15% ⇒ **Sticker Price** = 103.8 / (1.15)¹⁰  
  - (1.15)¹⁰ ≈ 4.0456  
  - Sticker ≈ **\$25.66**

> Interpretation: With these inputs, the *intrinsic present value* (sticker) is \$25.66/share.

### 7.2 MOS Price (50% buffer)
- **MOS 50%** ⇒ **MOS Price** = 25.66 × 0.5 = **\$12.83**  
- Current price = \$40 → **not on sale** per these conservative inputs.

*(If you believe growth is 12% and fair PE 22, Sticker rises; but Rule #1 prefers conservatism.)*

### 7.3 Payback Time
Assume **Owner Earnings₀ = \$550M**, growth **g = 6%** (more conservative than EPS):  
- Year‑by‑year cash flows (M): 550, 583, 618, 655, 695, 737, 781, 828, 878, 931…  
- **Cumulative** vs **Market Cap** (\$4.0B):  
  - Y1: 550  
  - Y2: 1,133  
  - Y3: 1,751  
  - Y4: 2,406  
  - Y5: 3,101  
  - Y6: 3,838  
  - **Y7: 4,619** (≥ 4,000) ⇒ **Payback ≈ 7 years** (at today’s market cap)

> Attractive by Rule #1 payback convention. (Note: we compared to market cap; you can also use **enterprise value** or **equity value** per‑share — be consistent across companies.)

### 7.4 Ten Cap
- **Ten Cap Value** = Owner Earnings / 0.10 = 550 / 0.10 = **\$5.5B**  
- Compare to **Market Cap** \$4.0B ⇒ **undervalued** by this lens.

> Tension: Ten Cap & Payback look favorable; Sticker/MOS looks conservative relative to price. In practice, triangulate and probe assumptions (growth quality, cyclicality, reinvestment needs).

---

## 8) Implementation Notes for “Common Investor”

### 8.1 Data Ingestion & Normalization
- **Ticker → CIK** mapping (cache locally).  
- Retrieve **10‑K/10‑Q XBRL** facts for 10+ years where available.  
- Normalize into canonical schema: `income_statement`, `balance_sheet`, `cash_flow`, `meta` (dates, shares).  
- **Fair access policy**: obey SEC rate limits; include descriptive **User‑Agent**; implement retries/backoff.  
- **Corporate actions**: reverse splits, ticker changes—maintain symbol history table.

### 8.2 Computation Layer
- **Metrics engine** computes: ROIC, CAGRs, FCF/Owner Earnings, leverage, coverage, etc.  
- **Valuation engine** implements Sticker/MOS, Payback, Ten Cap, and optional DCF/multiples.  
- **Assumptions manager**: user overrides for growth, PE cap, discount rate, owner‑earnings normalization.

### 8.3 Quality/Flags
- Show **data completeness** badges (e.g., “8 of 10 years available”).  
- **Red‑flag detector**: big goodwill impairments, negative CFO, frequent restatements, debt spikes, new share issuance surges.  
- **Industry adapters**: banks/insurers — switch to sector‑appropriate ratios.

### 8.4 UX/Presentation
- **Single search field** (company or ticker) → dashboard tabs: *Overview*, *Four Ms*, *Financials*, *Valuation*, *Signals*, *Filings*.  
- **Explainability**: always show **formula cards** with inputs and sources (line items used).  
- **What‑if sliders** for growth/PE/discount; instant recalculation of Sticker/MOS.  
- Export **PDF/CSV**; shareable analysis links.

---

## 9) Formula Reference (Cheat Sheet)

- **CAGR(x₀→xₙ, n yrs)** = (xₙ / x₀)^(1/n) − 1  
- **NOPAT** = EBIT × (1 − Cash Tax Rate)  
- **ROIC** = NOPAT ÷ Invested Capital  
- **Invested Capital (proxy)** = Total Debt + Equity − Cash  
- **Owner Earnings** ≈ CFO − Maintenance CapEx (≈ CapEx if maintenance unknown)  
- **Interest Coverage** = EBIT ÷ Interest Expense  
- **Sticker Price** = (EPS₀ × (1+g)¹⁰ × PE_future) ÷ (1 + r)¹⁰  
- **MOS Price** = Sticker × (1 − MOS%)  
- **Ten Cap Value** = Owner Earnings ÷ 0.10

---

## 10) Edge Cases & Anti‑Patterns

- **Cyclicals/commodities**: smooth with **10‑year medians**; avoid extrapolating peak margins/growth.  
- **High‑growth, negative FCF**: Sticker depends on EPS path—apply **larger MOS**; prefer unit‑economics proof.  
- **GAAP quirks**: capitalized R&D, stock‑based comp; adjust carefully and remain consistent.  
- **Buybacks at high prices**: can **destroy** value despite EPS optics.  
- **Financials**: banks/insurers require sector‑specific ratios (ROE, CET1, combined ratio).

---

## 11) QA/Validation: Sanity Tests & Unit Checks

- **Accounting identity** checks: CFO + CFI + CFF = ΔCash.  
- **Restatement** detection: compare prior vs updated period facts.  
- **Range guards**: Coverage usually >0; ROIC rarely >50% for long periods (investigate if it is).  
- **Recalc audit**: show each input used (link to filing and page/footnote when possible).

---

## 12) Glossary (selected)

- **CFO**: Net cash from operating activities.  
- **CapEx**: Capital expenditures (cash outflow for PPE/intangibles).  
- **EBIT**: Earnings before interest and taxes (Operating Income).  
- **NOPAT**: After‑tax operating profit (pre‑financing).  
- **ROIC**: Return on invested capital—efficiency of core operations.  
- **Owner Earnings**: Cash available to owners after maintenance re‑investment.  
- **Sticker Price**: Present value of conservative 10‑yr projection (Rule #1 heuristic).  
- **Margin of Safety (MOS)**: Discount buffer below intrinsic value to protect against errors.

---

**End of Document**