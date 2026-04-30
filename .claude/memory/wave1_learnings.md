# Wave 1 Contract Authoring — Learnings & Patterns

> Captured 2026-04-30 from implementor→critique→verifier runs on 03_industry, 04_moat, 05_management

---

## Harness Schema Rules (ground truth from 01_business_profile.json)

These rules MUST be in every implementor prompt. Violations were caught in every Wave 1 contract.

### output_schema
- `field_types` values: "string" | "array[string]" | "boolean" | "integer" | "object" | "array[object]" — top-level keys ONLY
- No dot-notation keys (e.g., "switching_costs.present" is WRONG)
- No non-standard keys: `integer_ranges`, `nested_no_nulls`, `conditional_string_minimums` are all silently ignored by the harness
- Enforce nested object constraints and integer ranges via grounding_checks instead

### grounding_checks
Required fields: "id", "description", "claim_source", "verify_against", "contradiction_rule", "severity"
WRONG names used by implementors: "name" (should be "id"), "type" (should be "severity"), "condition" (should be "contradiction_rule"), "action"/"message" (remove), "rule"/"flag_text" (should be "description")
- Checks that operate only on output (no agent_bundle verify_against) → move to llm_eval_criteria
- Do NOT duplicate schema-enforced constraints (array_minimums already enforces min count — don't repeat in grounding_checks)

### cross_references
Required fields: "check", "rule", "source", "target", "match"
WRONG names used: "field" (should be "target"), "anchor" (should be "source")

### llm_eval_criteria
- Exactly 4 dimensions (deviations allowed if weights still sum to 20, but 4 is cleaner)
- Each key requires: "weight", "prompt", "score_5", "score_3", "score_1"
- WRONG names used: "description" (should be "prompt"), "scoring" (should be split into score_5/score_3/score_1)
- Weights MUST sum to llm_score_maximum (always 20)
- The 03_industry implementor produced weights summing to 15 (not 20) — BLOCKING

### Prior sprint output paths
Correct: `prior_outputs.02_unit_economics`, `prior_outputs.03_industry`
Wrong: `prior_sprint_output.unit_economics`
Format: zero-padded sprint name as the key

---

## Domain Learnings

### ROIC unit storage
- ROIC stored as decimals: 0.15 = 15%. Use threshold 0.10 for 10%, NOT 10.
- 05_management implementor wrote `roic_avg_5y < 10` — should be `< 0.10` (unit error)

### Grounding check design
- "verdict=poor AND cyclicality=low" is NOT a contradiction. Secular decline industries (newspapers, brick-and-mortar retail) can be low-cyclicality AND structurally poor. Downgrade to soft.
- "evidence contains generic words" is subjective — not mechanically enforceable. Belongs in llm_eval_criteria evidence_quality, not grounding_checks.
- "concentration=concentrated → supplier_power=low" is roughly correct (few large buyers have scale), but the contradiction check must be explicit: `concentration == 'concentrated' AND supplier_power == 'high'`.

### Cross-sprint data dependencies
- 06_peers has NO peer data in agent_bundle — LLM must score peers from general knowledge + prior_outputs.03_industry.peer_candidates
- Subject company scores CAN be anchored to agent_bundle (roic_persistence, balance_sheet, pricing_power_score, four_ms.management)
- This means peer grounding checks must verify peer names come from industry sprint, not hallucinated

### Moat contract specifics
- Five moat types: switching_costs, network_effects, scale_or_cost_advantage, brand, regulatory_assets
- network_effects.type must be "none" if present=false; must NOT be "none" if present=true (hard logical check)
- durability_rating 0-5 must correlate directionally with four_ms.moat (0-1 quantitative score)
- Strong moat claim (durability >= 4) contradicted by ROIC < 10% (< 0.10 decimal)
- Brand moat without pricing_power_score > 0.4 is suspicious (soft)

### Management contract specifics
- incentives_alignment field: no proxy statement data in agent_bundle — this field is LLM-inferred from general knowledge. Must note this in contract.
- track_record_examples are prime hallucination targets → weight evidence_quality higher (7/20 vs 5/20)
- "compounder" style with ROIC < 10% is empire building, not compounding (hard check)
- Rating 5/5 should require four_ms.management >= 0.85 (rare threshold)

### Industry contract specifics
- industry_notes field in agent_bundle contains category-specific guidance — LLM output should not contradict it (soft check)
- Peer candidates must be real, named companies — 03_industry enforces min 3 via array_minimums
- LLM eval must penalize generic Porter's Five Forces boilerplate — evidence_quality prompt should explicitly say "cite specific dynamics, not generic theory"

---

## The 3-Agent Pattern — What Works

**Implementor → Critique → Verifier** runs in parallel per contract, sequentially within each contract.

What the critique agent is good at:
- Catching structural schema violations (wrong field names, non-standard keys)
- Identifying weight-sum errors in llm_eval_criteria
- Flagging domain logic flaws (verdict_poor + low_cyclicality is valid, not a contradiction)
- Spotting unit errors (ROIC threshold 10 vs 0.10)
- Identifying redundant checks (schema already enforces what grounding_check tries to re-enforce)

What the verifier agent is good at:
- Applying all critique fixes systematically
- Producing valid JSON with correct structure
- Maintaining original good content while replacing broken parts

What the pattern does NOT catch (still needs human review):
- Whether the domain thresholds are well-calibrated (e.g., is 12/20 the right pass threshold?)
- Whether the llm_eval_criteria prompts are specific enough to distinguish good vs bad outputs
- Whether monitoring_triggers in 07_risks will produce actionable outputs
- Cross-contract consistency (does moat's durability_rating feed thesis correctly?)

---

## Efficiency Notes

- Wave 1 timing: implementors ~25s, critiques ~65-80s, verifiers ~68-75s
- All three chains run in parallel — total wall time ≈ longest chain ≈ ~3-4 min per wave
- Implementor prompts MUST include format rules explicitly — without them, 100% of contracts had BLOCKING schema violations
- Adding the format rules section to implementor prompts reduced rework in verifier stage
