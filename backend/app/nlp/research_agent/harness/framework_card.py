"""Framework reference cards for the qualitative agent harness.

Two constants distilled from Phil Town's Rule #1 and Vitaliy Katsenelson's QVG framework.
These cards are prepended to system prompts to ensure consistent analytical lens.
"""

FRAMEWORK_CARD = """
## RULE #1 + QVG FRAMEWORK REFERENCE

Two investing lenses applied simultaneously:
- **Rule #1 (Phil Town)**: Four Ms + Big Five Numbers + conservative valuation
- **QVG (Katsenelson)**: Quality-Valuation-Growth scorecard emphasizing durability

---

### FOUR MS (Rule #1)

**Meaning**: Understand how the business makes money. Extract products, customer segments, revenue drivers, pricing model.

**Moat**: Five types — brand, network effects, cost advantage, switching costs, regulatory/toll bridge.
Evidence: ROIC ≥15% sustained, gross margin stable/rising, pricing power. Red flag: declining ROIC, collapsing margins.

**Management**: Reinvestment ratio (CapEx/CFO) sweet spot 0.3-0.7. Payout ratio (buybacks+dividends/CFO) sweet spot 0-0.6.
Look for insider ownership, honest guidance. Red flag: empire-building M&A, heavy dilution, misaligned incentives.

**Margin of Safety**: Default 50% MOS — buy at half intrinsic value. Require 60-70% when moat/management weak or balance sheet poor.

---

### BIG FIVE NUMBERS (exact thresholds)

- **ROIC** ≥15% sustained (NOPAT/Invested Capital). Check consistency across 1y/3y/5y/10y — declining trend = moat erosion.
- **Revenue CAGR** — consistency across windows matters more than point-in-time speed.
- **EPS CAGR** — same multi-window check. Net income growing but CFO flat = accrual risk.
- **Owner Earnings** = CFO − CapEx. Negative/shrinking while net income rises = earnings quality gap.
- **Interest Coverage** (EBIT/Interest): >5x comfortable, 2-5x cautious, <2x risky.

---

### QVG QUALITY SCORING RUBRIC (0-100 pts)

- Moat & Durability: 0-25
- Management & Capital Allocation: 0-20
- Revenue Quality: 0-15
- Pricing Power: 0-15
- Industry Structure: 0-15
- Balance Sheet Resilience: 0-10

---

### COMPUTED METRICS → FRAMEWORK MAPPING

- `roic_avg_10y` → ROIC target ≥0.15. Below 0.10 = weak moat.
- `roic_persistence_score` (0-5) → durability; score <3 = suspect even if headline ROIC ok.
- `pricing_power_score` (0-1) → QVG Pricing Power dimension.
- `management.score` (0-1) → reinvestment + payout discipline.
- `balance_sheet_resilience.score` (0-5) → 40% coverage, 30% D/E, 30% net debt trend.
- `mos_recommendation.recommended_mos_pct` (0.3-0.7) → higher = more safety margin needed.
- `gross_margin_trend` stable/improving/declining → pricing power signal.
- `share_dilution` buyback/neutral/dilution → management quality signal.

---

### RED FLAGS CHECKLIST

1. ROIC declining or consistently <10%
2. Revenue CAGR inconsistent across windows (10y strong, 1y/3y collapsing)
3. Owner Earnings negative/shrinking while net income positive
4. Interest coverage <2x or net debt trend worsening
5. Share dilution trend (not buyback)
6. Gross margin trend declining
7. Narrative growth claims without timeseries evidence
8. Moat claim not backed by ROIC persistence (score <3)
9. Management praise without capital allocation evidence
10. Story stock language — vision claims lacking concrete unit economics

---

### HOW TO USE THIS CARD

Builder: Four Ms guide each sprint; Big Five ground every moat/management claim in data.
Synthesis: Validate all 6 QVG categories. Red flag present → flag explicitly, raise MOS requirement.
"""

EVALUATOR_FRAMEWORK_ADDENDUM = """
## QUICK RUBRIC FOR EVALUATOR (QVG SCORING + RED FLAGS)

### QVG QUALITY SCORE (0–100)
Grade the thesis output against these weights:

- **Moat & Durability** (0–25): ROIC persistence + moat narrative + margin stability
- **Revenue Quality** (0–15): Recurrence + visibility + growth consistency
- **Pricing Power** (0–15): Margin level/trend + churn + industry dynamics
- **Industry Structure** (0–15): Fragmentation + barriers + cyclicality
- **Management & Allocation** (0–20): Reinvestment + payout + incentive alignment
- **Balance Sheet** (0–10): Interest coverage + debt/equity + net debt trend

---

### RED FLAGS (AUTO-FAIL IF UNADDRESSED)

1. ROIC declining or <10%
2. Revenue CAGR inconsistent across windows
3. Owner Earnings negative while net income positive
4. Interest coverage <2x or net debt worsening
5. Share dilution (not buyback)
6. Gross margin trend declining
7. Growth claim without timeseries evidence
8. Moat claim without ROIC persistence backing (score <3)
9. Management praise without capital allocation proof
10. "Story stock" language lacking concrete unit economics

---

### SCORING RULE
- If 1+ red flags unaddressed → quality_score ≤ 40
- If all red flags addressed with nuance → quality_score ≥ 50 (moat/management/balance sheet permitting)
- If high-quality evidence on all six QVG dimensions → quality_score ≥ 70
"""
