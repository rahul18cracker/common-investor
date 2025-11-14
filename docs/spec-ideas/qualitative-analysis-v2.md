# Qualitative Analysis Playbook — Version 2 (Agent-Ready)

A concise, **actionable** framework an AI research agent can follow to perform deep **qualitative** analysis of any public company.  
Focus on: **business model, unit economics, durability (moat), industry structure, management quality, peer comparison, risk**, and **decision rules**.  
This playbook is **source-agnostic**: gather evidence from primary disclosures (annual/quarterly filings, presentations, transcripts), product docs, reputable trade data, and credible media — but *do not* include external branding or author attributions in outputs.

---

## 0) Deliverables & Acceptance Criteria

### 0.1 Required outputs
1) **Executive Brief (≤1 page):** plain-English summary of business model, moat, industry, management, and key risks; final **Quality score** (0–100) and **Confidence** (Low/Med/High).  
2) **Peer Scorecard (table):** subject company vs top 3 peers across the QVG dimensions below.  
3) **Structured JSON bundle:** see schemas in §8 (business_profile.json, unit_economics.json, industry.json, moat.json, management.json, peers.json, risks.json).  
4) **Thesis File:** Buy/Hold/Avoid stance with explicit **falsifiers** (what would disprove the thesis).  
5) **Monitoring Triggers:** 5–10 metrics/events to watch and their thresholds.

### 0.2 Acceptance checks
- Every claim in the brief is **evidence-backed** (quote or figure) in the JSON bundle.  
- All JSON schemas validate; no `null` where a qualitative string or `"unknown"` is expected.  
- Peer Scorecard has **at least 3** direct competitors, comparable business mix/region.  
- Risk section includes **concentration** risks (customer/supplier), **cyclicality**, **regulatory**, **FX/commodity**, and **technology disruption**.

---

## 1) Workflow Overview (Do in Order)

1) **Scoping & Inputs** → ticker, time horizon, reporting currency, major segments/geographies.  
2) **Business Profile** → what the company **does**, who it **serves**, and how it **earns** cash.  
3) **Unit Economics** → revenue drivers, pricing model, cost structure, cash conversion.  
4) **Industry Structure** → competitive forces, supply/demand, regulation, cyclicality.  
5) **Moat & Durability** → switching costs, network effects, scale, brand, regulatory licenses, cost advantages; persistence of returns.  
6) **Management & Culture** → capital allocation, incentives, governance, long-term orientation.  
7) **Peer Comparison** → rank vs 3 peers on standardized criteria.  
8) **Risks & Fragility** → where/why the thesis could break; map to monitoring.  
9) **Synthesis** → Executive Brief + Quality score + Confidence + Falsifiers.  
10) **Monitoring Plan** → triggers and cadence.

---

## 2) Business Profile (Meaning)

**Goal:** Explain the economic engine in <10 sentences. Avoid marketing language.

**Agent tasks**
- Extract: products/services, customer segments, geographies, distribution channels.  
- Identify revenue recognition patterns (subscription, usage/consumption, one-time, blended).  
- Map revenue by segment and region (directionally, if exact shares missing).  
- Note any embedded **recurrence** (contracts, renewals, replacement cycles) and **pricing power** levers.

**Prompt template**
```
Summarize the company's business model in 8–10 sentences. 
List: products, primary customers, geographies, pricing model, and top 3 revenue drivers. 
State where revenue is recurring and why. 
Avoid marketing jargon; be concrete.
```

---

## 3) Unit Economics

**Goal:** Understand revenue → gross profit → operating profit → free cash flow mechanics.
Different models require different lenses; use what fits.

**Agent tasks**
- **Pricing model:** subscription tiers, usage pricing, per-unit economics, take rates, or contract terms.  
- **Revenue drivers:** volume vs price/mix; backlog/renewal mechanics; average selling price (ASP).  
- **Cost structure:** COGS components, gross margin drivers; fixed vs variable mix.  
- **Cash conversion:** working capital dynamics; maintenance vs growth capex; seasonality.  
- **If applicable** (SaaS/consumer/marketplace/industrial), capture LTV/CAC or payback heuristics when disclosed; mark `"not_applicable"` if model doesn’t use them.

**Prompt template**
```
Describe unit economics in 10–12 sentences: pricing, volume, cost structure, gross margin drivers, operating leverage, 
and cash conversion (WC, capex). Identify the single most important lever to improve FCF over the next 2–3 years.
```

---

## 4) Industry Structure

**Goal:** Qualitatively score the industry’s inherent economics.

**Agent tasks**
- Define the competitive set (at least 3 direct peers).  
- Characterize **bargaining power** (customers/suppliers), **threat of substitution**, **barriers to entry**, and **regulatory** constraints.  
- Describe **pricing power at the industry level** (commoditized vs differentiated).  
- Assess **cyclicality** and demand drivers (GDP-sensitive, rates, tech cycles, reimbursement, etc.).

**Prompt template**
```
Explain the industry structure in 8–10 sentences: fragmentation vs concentration, pricing dynamics, 
customer/supplier power, substitution, regulation, and cyclicality. State a one-sentence industry verdict (good/neutral/poor) with rationale.
```

---

## 5) Moat & Durability

**Goal:** Identify durable advantages and their evidence; judge persistence.

**Agent tasks**
- **Switching costs**: data lock-in, integration depth, training, ecosystem dependencies.  
- **Network effects**: direct/indirect; evidence (e.g., density metrics, multi-sided adoption).  
- **Scale/cost**: distribution, procurement, manufacturing scale; unit cost advantages.  
- **Brand**: pricing premium vs peers; trust/safety certifications.  
- **Regulatory**: licenses, approvals, exclusive rights; compliance capabilities.  
- **Return persistence**: multi-year **ROIC above cost of capital** and margin stability (qualitative verdict).

**Prompt template**
```
List each moat source (switching costs, network, scale/cost, brand, regulatory) and provide 1–2 sentences of evidence for each. 
Conclude with a 0–5 Durability rating and explain why.
```

---

## 6) Management & Culture

**Goal:** Evaluate capital allocation skill and alignment.

**Agent tasks**
- **Capital allocation**: reinvestment vs M&A vs buybacks vs dividends; evidence of discipline or empire-building.  
- **Incentives & alignment**: ownership, comp metrics, long-term orientation (language in letters/calls).  
- **Governance**: board independence, related-party transactions, audit issues.  
- **Operational credibility**: meeting stated milestones, transparency during setbacks.

**Prompt template**
```
Assess management in 10–12 sentences: capital allocation track record, incentive alignment, governance, 
and transparency. Rate 0–5 and justify.
```

---

## 7) Peer Comparison (Top 3 Peers)

**Goal:** Position the company vs peers on QVG-aligned criteria.

**Criteria (0–5 each)**  
- **Pricing Power** (ability to raise price with minimal volume loss)  
- **Recurrence** (contractual/behavioral)  
- **ROIC Persistence** (multi-year, qualitative)  
- **Balance Sheet Strength** (net leverage, liquidity, maturity ladder)  
- **Management/Allocation** (discipline & alignment)  
- **Industry Positioning** (share, differentiation)  
- **Valuation Flex** (room for rerating given quality; qualitative)  

**Output:** ranked table + 2–3 sentence commentary per peer.

**Prompt template**
```
Build a table comparing the company to three peers across the seven criteria (0–5). 
Add a short commentary per peer highlighting the 1–2 decisive differences.
```

---

## 8) Structured Output Schemas (JSON)

> Fill these; never leave fields `null`. Use `"unknown"` or empty arrays if unavailable.

### 8.1 `business_profile.json`
```json
{
  "ticker": "", "name": "", "reporting_currency": "",
  "products_services": ["", ""],
  "customer_segments": ["", ""],
  "geographies": ["", ""],
  "pricing_model": ["subscription", "usage", "one_time", "hybrid"],
  "revenue_drivers": ["", ""],
  "recurrence_mechanisms": ["contracts", "replacement_cycle", "ecosystem", "unknown"],
  "distribution_channels": ["", ""],
  "narrative": ""
}
```

### 8.2 `unit_economics.json`
```json
{
  "revenue_model": "",
  "price_levels_or_take_rate": "unknown",
  "volume_drivers": ["", ""],
  "gross_margin_drivers": ["", ""],
  "fixed_variable_mix": "unknown",
  "operating_leverage_drivers": ["", ""],
  "cash_conversion_notes": "",
  "working_capital_factors": ["", ""],
  "capex": { "maintenance": "unknown", "growth": "unknown" },
  "optional_metrics": { "ltv": "unknown", "cac": "unknown", "payback_months": "unknown" },
  "key_improvement_lever": ""
}
```

### 8.3 `industry.json`
```json
{
  "definition": "",
  "peer_candidates": ["", "", ""],
  "concentration": "fragmented|moderate|concentrated",
  "pricing_power": "weak|mixed|strong",
  "customer_power": "low|medium|high",
  "supplier_power": "low|medium|high",
  "substitution_threat": "low|medium|high",
  "regulatory_burden": "low|medium|high",
  "cyclicality": "low|medium|high",
  "verdict": "good|neutral|poor",
  "notes": ""
}
```

### 8.4 `moat.json`
```json
{
  "switching_costs": { "present": false, "evidence": "" },
  "network_effects": { "present": false, "type": "none|direct|indirect", "evidence": "" },
  "scale_or_cost_advantage": { "present": false, "evidence": "" },
  "brand": { "present": false, "evidence": "" },
  "regulatory_assets": { "present": false, "evidence": "" },
  "durability_rating_0_to_5": 0,
  "notes": ""
}
```

### 8.5 `management.json`
```json
{
  "capital_allocation_style": "",
  "track_record_examples": ["", ""],
  "incentives_alignment": "",
  "governance_highlights": "",
  "transparency_notes": "",
  "rating_0_to_5": 0
}
```

### 8.6 `peers.json`
```json
{
  "subject": "",
  "peers": [
    {
      "name": "",
      "pricing_power_0_to_5": 0,
      "recurrence_0_to_5": 0,
      "roic_persistence_0_to_5": 0,
      "balance_sheet_0_to_5": 0,
      "management_0_to_5": 0,
      "industry_positioning_0_to_5": 0,
      "valuation_flex_0_to_5": 0,
      "commentary": ""
    }
  ]
}
```

### 8.7 `risks.json`
```json
{
  "concentration": { "customers": "", "suppliers": "", "geography": "" },
  "cyclicality": "",
  "regulatory": "",
  "fx_commodity": "",
  "technology_disruption": "",
  "other": "",
  "top_five_risks": ["", "", "", "", ""],
  "monitoring_triggers": [
    { "name": "", "metric_or_event": "", "threshold": "", "action_if_breached": "" }
  ]
}
```

### 8.8 `thesis.json`
```json
{
  "stance": "buy|hold|avoid",
  "quality_score_0_to_100": 0,
  "confidence": "low|medium|high",
  "key_points": ["", "", ""],
  "falsifiers": ["", ""],
  "time_horizon_months": 36
}
```

---

## 9) Scoring Rubric (0–100 Quality Score)

- **Moat & Durability (0–25)**: evidence of structural advantages; persistence.  
- **Revenue Quality (0–15)**: recurrence, diversification, visibility.  
- **Pricing Power (0–15)**: demonstrated and defensible ability to raise price.  
- **Industry Structure (0–15)**: attractive force dynamics; low commodity exposure.  
- **Management & Allocation (0–20)**: track record, incentives, governance.  
- **Balance Sheet Resilience (0–10)**: liquidity, leverage, maturity profile.

**Computation:** sum category subscores. **Confidence** is a qualitative call based on evidence breadth, disclosure quality, and consistency.

---

## 10) Red Flags Checklist

- Aggressive accounting or frequent metric redefinitions.  
- Customer or supplier concentration >30% without compensating moat.  
- Chronically negative cash conversion without plausible runway.  
- Leverage up + deteriorating margins.  
- Price increases trigger material volume loss (weak pricing power).  
- Growth by serial M&A with thin disclosure; integration issues.  
- Regulatory probes, sanctions, or unresolved audit issues.

---

## 11) Final Synthesis Prompts

**Executive Brief**
```
Produce a one-page brief summarizing business model, unit economics, industry structure, moat, management, 
peer ranking, and top risks. Include the Quality score (0–100), Confidence (Low/Med/High), 
and three falsifiers that would change the stance.
```

**Monitoring Plan**
```
List 5–10 monitoring triggers with thresholds and what action to take if breached.
```

---

## 12) Directory Structure for Outputs

```
qualitative/
  business_profile.json
  unit_economics.json
  industry.json
  moat.json
  management.json
  peers.json
  risks.json
  thesis.json
  EXECUTIVE_BRIEF.md
```

---

## 13) Operating Notes for Agents

- Prefer **primary disclosures** and transcripts; corroborate with credible trade/market data.  
- Quote evidence succinctly inside JSON `notes` fields; avoid external logos, author names, or promotional language.  
- When uncertain, state `"unknown"` and add a follow-up task; do not infer quantitative facts without evidence.  
- Keep revisions atomic; maintain a changelog of assumptions and updates.

---

**End of Playbook.**