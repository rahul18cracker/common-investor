# Qualitative Agent Harness — Design Plan v1.1

> **Date:** 2026-04-21 | **Updated:** 2026-04-21
> **Status:** Draft — pending review
> **Depends on:** `qualitative-analysis-v2.md` (JSON schemas, prompts, scoring rubric), `AGENT-ITERATION-PLAN-V1.md` (phased rollout)
> **Design principles:** Anthropic Harness Design Guide (generator/evaluator separation, pre-negotiated contracts, file-based state, harness simplification), PE System Design Guide §12 (GenAI mental models, cost optimization, eval tiers, silent quality degradation)

---

## Context

The quantitative foundation is complete (11 timeseries metrics, Four Ms scoring, industry classification, agent-bundle API). An experimental agent (`exp_01_business_profile.py`) already generates `business_profile.json` for AAPL/WMT at ~$0.05-0.15/run using deepagents + Claude + Tavily. The goal is to evolve this into a harness that produces all 8 JSON outputs from the `qualitative-analysis-v2.md` playbook with build-verify-review loops, applying Anthropic harness design principles from the start.

**What prompted this:** Quantitative phases 1A-1C are merged. The spec (`qualitative-analysis-v2.md`) and iteration plan (`AGENT-ITERATION-PLAN-V1.md`) are written. Time to design the agent system properly before writing more code.

**Intended outcome:** A lean, observable, cost-effective harness that produces high-quality qualitative analysis for a 25-company pilot, with clear pass/fail criteria and full audit trail. The 25 companies validate the harness — if quality and cost meet thresholds, expand to the broader S&P 500 universe.

**Pilot validation purpose:**
1. Measure harness quality, cost, and failure patterns across diverse industries
2. Calibrate contracts — are pass/fail thresholds too strict or too loose?
3. Build a **golden set** of human-reviewed outputs to calibrate the LLM evaluator
4. Make a go/no-go decision before investing in Docker/UI integration

---

## A. Architecture: 3 Roles, File-Based State

### Roles

| Role | Responsibility | Model | Failure mode it solves |
|------|---------------|-------|----------------------|
| **Orchestrator** | Python script. Drives sprint sequence, manages retries, enforces budget/timeout guards, routes sprints to appropriate model tier. | None (deterministic) | Prevents infinite loops, enforces cost caps |
| **Builder** | LLM agent. Produces one JSON output per sprint. Gets lean context: contract + agent-bundle + Item 1 text + prior sprint outputs. | Per-sprint model routing (see below) | N/A — this is the generator |
| **Evaluator** | LLM agent. Grades builder output against pre-negotiated contract. Adversarial framing ("find failures"). | Claude Haiku 4.5 (cheap, fast, sufficient for grading) | Prevents self-evaluation bias (Failure Mode 2 from harness guide) |

### Per-Sprint Model Routing

Not all sprints are equally difficult. Extraction tasks (business_profile, industry) are simpler than judgment tasks (moat, thesis). Each contract specifies a `model_tier` field:

| Sprint | Difficulty | Default model | Rationale |
|--------|-----------|---------------|-----------|
| 1. business_profile | Low (extraction) | Haiku 4.5 | Mostly extracting facts from Item 1 + agent-bundle |
| 2. unit_economics | Low-Medium | Haiku 4.5 | Structured extraction with some inference |
| 3. industry | Low-Medium | Haiku 4.5 | Competitive set identification, force analysis |
| 4. moat | **High (judgment)** | Haiku 4.5 → Sonnet if needed | Requires synthesizing multiple inputs into durability assessment |
| 5. management | **High (judgment)** | Haiku 4.5 → Sonnet if needed | Capital allocation evaluation requires nuance |
| 6. peers | Medium | Haiku 4.5 | Comparative scoring across 7 criteria |
| 7. risks | Medium-High | Haiku 4.5 → Sonnet if needed | Cross-cutting synthesis of all prior analysis |
| 8. thesis | **High (synthesis)** | Haiku 4.5 → Sonnet if needed | Final integration — hardest task |

**Upgrade trigger:** After Phase 1A (5 companies), if a sprint's pass rate < 80%, upgrade that specific sprint to Sonnet. Not all-or-nothing — only upgrade where the failure mode is demonstrated.

**Why not a Planner agent?** The plan already exists as a human-authored spec (`qualitative-analysis-v2.md` with 10-step workflow, 8 JSON schemas, prompt templates, scoring rubric). A Planner agent solves the "sparse input" failure mode — the user says 5 words and the planner expands to a spec. Our input isn't sparse. The 8 sprints *are* the task breakdown. If builder consistently under-scopes, we add a planner later (harness simplification principle).

**Why not one monolithic agent?** Context window degradation (Failure Mode 1). A single agent generating all 8 JSONs would accumulate ~30K+ tokens of context. Sprint-per-JSON keeps each builder invocation at ~8-12K tokens.

**Data sources per builder:** Each builder receives (1) agent-bundle quantitative data, (2) SEC Item 1 text from `/fourm/meaning/refresh` (free, already in DB — richest primary source for business/moat/risks evidence), and (3) Tavily web search for gaps (recent news, competitive landscape, segments not in filings).

### Communication: File-Based State

Agents never see each other's reasoning. They communicate via files only.

```
state/{ticker}/
  manifest.json                    # Run metadata: status, cost, timing, per-sprint results
  agent_bundle.json                # Cached /agent-bundle response (fetched once)
  item1_text.txt                   # SEC Item 1 business description (fetched once)
  
  sprints/01_business_profile/
    contract.json                  # Pre-negotiated pass/fail criteria (frozen)
    builder_output.json            # Builder's generated JSON
    eval_result.json               # Evaluator's pass/fail + scores + failure details
    builder_trace.json             # Full prompt/response log (optional, for debugging)
    
  sprints/02_unit_economics/
    ...same pattern...
    
  sprints/08_thesis/
    ...same pattern...
    
  final/
    EXECUTIVE_BRIEF.md             # Synthesized from all JSONs
    quality_summary.json           # Aggregated scores across all sprints
```

**State root is parameterized** in `state_manager.py` — defaults to `state/{ticker}/` but accepts a configurable root path. This ensures multi-tenancy (Phase 3) is a one-line config change: `state/{user_id}/{ticker}/`, not an architectural rewrite.

**Why files not messages:** Files survive context resets, are inspectable post-hoc, and prevent context accumulation. The manifest.json is the single source of truth for run state.

---

## B. Sprint Structure & Dependencies

### Sprint Order (8 sprints)

| Sprint | Output | Depends On | Rationale |
|--------|--------|------------|-----------|
| 1 | `business_profile.json` | agent-bundle only | Foundation — everything else builds on understanding the business |
| 2 | `unit_economics.json` | #1 | Needs business model context for pricing/cost analysis |
| 3 | `industry.json` | #1 | Needs products/segments to define competitive set |
| 4 | `moat.json` | #1, #2, #3 | Moat assessment needs business model + industry context + unit economics |
| 5 | `management.json` | #1 + agent-bundle | Capital allocation analysis needs business context + quantitative data |
| 6 | `peers.json` | #3 | Peer comparison needs industry/competitive set defined first |
| 7 | `risks.json` | #1-#6 | Risk assessment synthesizes all prior analysis |
| 8 | `thesis.json` | #1-#7 | Final synthesis of everything |

**Parallelization opportunity (future):** Sprints 2, 3, 5 could run in parallel since they depend only on #1. Not worth the complexity for Phase 1A — sequential is simpler to debug and cheaper to build.

### Builder Context Per Sprint

Each builder gets ONLY:
1. **Contract** for this sprint (~500 tokens) — schema + pass/fail criteria
2. **Agent-bundle** (~2-3K tokens) — quantitative data from API
3. **SEC Item 1 text** (~3-5K tokens, truncated) — primary source business description from latest 10-K
4. **Prior sprint outputs** that this sprint depends on (~1-3K tokens) — just the JSONs, not builder reasoning
5. **Sprint-specific system prompt** (~1K tokens) — from qualitative-analysis-v2.md prompts

Total: ~8-12K tokens input. Well within efficient range for Haiku. No context accumulation across sprints.

### Prompt Caching Strategy

For 8 sequential builder calls on the same ticker, the agent-bundle and Item 1 text are identical each time. Anthropic's prompt caching gives **90% cost reduction on cached prefixes**.

**Prompt structure (cache-optimized):**
```
[CACHED PREFIX — identical across all 8 sprints for same ticker]
  System prompt: role definition + general rules
  Agent-bundle data (~2-3K tokens)
  Item 1 text (~3-5K tokens)
  
[DYNAMIC SUFFIX — changes per sprint]
  Sprint-specific contract + schema
  Prior sprint outputs (dependencies)
  Sprint-specific prompt template
```

**Impact:** ~5-8K tokens cached at 90% off for sprints 2-8. Estimated savings: 40-60% reduction in builder input token cost across a full run. For Haiku at $0.25/1M input tokens, this saves ~$0.01-0.03 per company. Small per-company but meaningful across 25+ companies and retries.

---

## C. Evaluator & Contract Design

### Pre-Negotiated Contracts (one per sprint, frozen before pilot)

Each contract specifies four layers of checks:

**Layer 1: Deterministic Schema (no LLM needed, free)**
- JSON schema validation (all required fields present, correct types)
- No null values (must be string/array/number or "unknown")
- Array minimums (e.g., `products_services` >= 2, `top_five_risks` == 5, `peers` >= 3)
- Enum validation (e.g., `stance` in ["buy", "hold", "avoid"])
- Score bounds (e.g., `quality_score_0_to_100` in 0-100, `durability_rating_0_to_5` in 0-5)

**Layer 2: Cross-reference (deterministic, checks consistency)**
- Ticker/name match agent-bundle data
- Peer names in `peers.json` match `peer_candidates` in `industry.json`
- `monitoring_triggers` in `risks.json` reference actual metrics from agent-bundle

**Layer 3: Grounding Check (deterministic, catches hallucinations against our own data)**

This is the most important gap filled from the PE guide §12 insight on silent quality degradation. An LLM that hallucates returns a 200 with valid JSON — deterministic schema checks pass, but the content is wrong.

The grounding check extracts numeric claims from builder output and verifies them against agent-bundle values:

| Check | Example | Source |
|-------|---------|--------|
| ROIC claim vs actual | Builder says "strong 18% ROIC" but agent-bundle shows roic_avg_10y = 8% | `agent_bundle.metrics.roic_avg_10y` |
| Margin claim vs actual | Builder says "expanding margins" but operating_margin trend is declining | `agent_bundle.timeseries.operating_margin` |
| Growth claim vs actual | Builder says "double-digit growth" but rev_cagr_5y = 4% | `agent_bundle.metrics.growths_extended` |
| Debt claim vs actual | Builder says "conservative balance sheet" but debt_to_equity > 3.0 | `agent_bundle.metrics.debt_to_equity` |
| Score vs evidence | moat durability_rating = 4 but ROIC is below 10% and declining | Cross-check score against underlying data |

**Implementation:** Parse builder_output for numeric values and qualitative claims (e.g., "strong", "growing", "conservative"). Compare against thresholds derived from agent-bundle. Flag contradictions. This is deterministic — no LLM cost.

**Why this matters:** This is the difference between "the JSON has the right shape" and "the analysis is factually consistent with the data we gave it." The most dangerous failure mode is plausible-looking wrong analysis that passes structural checks.

**Layer 4: LLM Evaluator (adversarial, ~500 tokens output)**
- Evidence quality: Are claims backed by specific data/quotes, not vague assertions?
- Internal consistency: Do conclusions follow from stated evidence?
- Completeness: Are there obvious gaps for this industry/company?
- Red flag check: Would any red flags from spec §10 apply but were missed?

### Contract Format (with new fields)

```json
{
  "sprint": "01_business_profile",
  "model_tier": "haiku",
  "output_schema": {
    "required_fields": ["ticker", "name", "products_services", "narrative"],
    "array_minimums": {"products_services": 2, "geographies": 2},
    "enums": {"pricing_model": ["subscription", "usage", "one_time", "hybrid"]}
  },
  "cross_references": {
    "ticker_must_match": "agent_bundle.company.ticker"
  },
  "grounding_checks": [
    {"claim_pattern": "revenue_drivers", "verify_against": "agent_bundle.timeseries.is", "check": "drivers mentioned should relate to actual revenue segments"},
    {"claim_pattern": "narrative.*growth", "verify_against": "agent_bundle.metrics.growths_extended", "check": "growth claims must align with actual CAGR data"}
  ],
  "llm_eval_criteria": {
    "evidence_quality": "Are revenue drivers backed by specific figures?",
    "completeness": "Does narrative explain HOW the company earns, not just WHAT it does?",
    "consistency": "Do pricing_model and recurrence_mechanisms align with narrative?"
  },
  "pass_threshold": {
    "deterministic": "all_pass",
    "grounding": "zero_contradictions",
    "llm_score_minimum": 12,
    "llm_score_maximum": 20
  }
}
```

### Evaluator Output Format (eval_result.json)

```json
{
  "sprint": "business_profile",
  "pass": true,
  "deterministic_checks": {
    "schema_valid": true,
    "no_nulls": true,
    "array_minimums": true,
    "enum_valid": true,
    "details": []
  },
  "cross_reference_checks": {
    "ticker_match": true,
    "peer_consistency": true,
    "details": []
  },
  "grounding_checks": {
    "pass": true,
    "contradictions_found": 0,
    "details": []
  },
  "llm_evaluation": {
    "evidence_quality": {"score": 4, "max": 5, "notes": "..."},
    "internal_consistency": {"score": 3, "max": 5, "notes": "..."},
    "completeness": {"score": 4, "max": 5, "notes": "..."},
    "red_flags_check": {"score": 5, "max": 5, "notes": "..."},
    "overall": 16,
    "max": 20,
    "pass": true,
    "failures": []
  },
  "cost_usd": 0.003,
  "duration_seconds": 8
}
```

**Pass threshold:** All deterministic checks pass AND zero grounding contradictions AND LLM overall >= 12/20 (60%).

> **Note:** The 12/20 (60%) LLM threshold is **provisional**. It will be calibrated during Phase 1A-review (human calibration step, §G). If human review shows outputs scoring 12/20 are garbage, we raise to 15/20. If outputs scoring 10/20 are acceptable, we lower. The 60% number is a starting point, not a fixed bar. The real quality bar is grounding checks — zero contradictions means 100% factual accuracy against our own data. The LLM threshold handles the subjective remainder (evidence depth, analytical coherence).

**Adversarial framing for evaluator prompt:**
> "You are a skeptical investment analyst reviewing a colleague's work. Your job is to find errors, unsupported claims, and gaps. Score harshly — a mediocre analysis that passes is worse than a good one that fails and gets revised."

### Why this four-layer approach?

| Layer | Cost | Catches | % of failures caught |
|-------|------|---------|---------------------|
| Schema (L1) | Free | Missing fields, wrong types, nulls | ~40% |
| Cross-reference (L2) | Free | Inconsistencies between sprints | ~20% |
| Grounding (L3) | Free | **Hallucinations against our own data** | ~20% |
| LLM adversarial (L4) | ~$0.003 | Weak evidence, missing analysis, subtle gaps | ~20% |

Layers 1-3 are deterministic and free. They catch ~80% of failures before the LLM evaluator runs. Layer 4 handles the subjective 20%.

---

## D. Quality Dimensions (from spec §9, mapped to evaluator)

| Dimension | Weight | What it grades | Source sprint(s) |
|-----------|--------|---------------|-----------------|
| Moat & Durability | 25% | Structural advantages with evidence | moat.json |
| Revenue Quality | 15% | Recurrence, diversification, visibility | business_profile, unit_economics |
| Pricing Power | 15% | Demonstrated ability to raise prices | unit_economics, moat |
| Industry Structure | 15% | Force dynamics, commodity exposure | industry.json |
| Management & Allocation | 20% | Track record, incentives, governance | management.json |
| Balance Sheet Resilience | 10% | Liquidity, leverage, maturity | agent-bundle quantitative data |

**Quality score (0-100):** Computed deterministically in thesis sprint from per-sprint subscores. The evaluator for thesis.json verifies the score math, not the score itself.

---

## E. Iteration Loop & Cost Guards

### On evaluator failure:

```
Sprint N: Builder generates output
  -> Layer 1-3: Deterministic checks (schema, cross-ref, grounding)
    -> FAIL: Return specific failures to builder (no LLM eval needed, free)
  -> Layer 4: LLM evaluation
    -> FAIL: Return failure list + scores to builder
  -> Builder retries with: original contract + prior output + failure list
  -> Max 2 retries per sprint (3 total attempts)
  -> After 3 failures: Mark sprint as "degraded" in manifest, proceed to next sprint
```

**Why proceed on degraded?** Downstream sprints (especially thesis) can still synthesize from partial data. A degraded business_profile doesn't mean moat analysis is impossible — it means the moat analysis should note lower confidence. Blocking the entire pipeline on one sprint failure is over-engineering.

### Cost Budget

| Component | Per-sprint cost | 8 sprints | With retries (worst case) |
|-----------|----------------|-----------|--------------------------|
| Builder (Haiku 4.5) | ~$0.01-0.02 | ~$0.08-0.16 | ~$0.12-0.24 |
| Builder (with prompt caching, sprints 2-8) | ~$0.005-0.01 | ~$0.04-0.08 | ~$0.06-0.12 |
| Evaluator (Haiku 4.5) | ~$0.002-0.005 | ~$0.016-0.04 | ~$0.024-0.06 |
| Tavily searches | ~$0.01-0.02 | ~$0.08-0.16 | ~$0.12-0.24 |
| **Total (with caching)** | | **~$0.14-0.28** | **~$0.22-0.46** |

**Budget guard:** Orchestrator tracks cumulative cost in manifest.json. If cost exceeds $0.50, skip retries on remaining sprints (first-pass only). Hard abort at $0.75.

**If select sprints upgraded to Sonnet:** moat + management + thesis at Sonnet adds ~$0.12-0.18. Total with mixed routing: ~$0.30-0.55. Still manageable.

**Scaling cost estimate (from PE guide §12.9 framework):**

| Scope | Companies | One-time cost | Quarterly re-run |
|-------|-----------|--------------|-----------------|
| Pilot | 25 | ~$7-12 | N/A |
| S&P 500 | 500 | ~$100-175 | ~$400-700/year |
| Full universe | 2,000 | ~$400-700 | ~$1,600-2,800/year |

**Key insight from harness guide:** Evaluator is cheap (~$0.003/round vs ~$0.01-0.02/build round). Never skip evaluation to save cost.

### Timeout Guards

- Per-sprint builder: 120 seconds
- Per-sprint evaluator: 30 seconds
- Full run: 15 minutes
- Hard abort on any timeout; mark sprint as "timeout" in manifest

---

## F. Observability

### manifest.json (source of truth for every run)

```json
{
  "ticker": "AAPL",
  "started_at": "2026-04-21T10:00:00Z",
  "completed_at": "2026-04-21T10:08:32Z",
  "status": "completed",
  "total_cost_usd": 0.32,
  "total_duration_seconds": 512,
  "model_routing": {"01_business_profile": "haiku", "04_moat": "sonnet"},
  "sprints": {
    "01_business_profile": {
      "status": "passed",
      "model": "haiku",
      "attempts": 1,
      "cost_usd": 0.04,
      "duration_seconds": 45,
      "eval_score": 18,
      "grounding_contradictions": 0,
      "tool_calls": {"agent_bundle": 1, "tavily": 2, "save": 1}
    },
    "02_unit_economics": {
      "status": "passed",
      "model": "haiku",
      "attempts": 2,
      "cost_usd": 0.07,
      "duration_seconds": 82,
      "eval_score": 14,
      "grounding_contradictions": 0,
      "tool_calls": {"agent_bundle": 0, "tavily": 1, "save": 1}
    }
  },
  "quality_score": 72,
  "confidence": "medium"
}
```

### Full Prompt/Response Logging (optional, per-sprint)

Each sprint directory can optionally include `builder_trace.json`:

```json
{
  "model": "claude-haiku-4-5-20251001",
  "input_tokens": 8432,
  "output_tokens": 1256,
  "cached_tokens": 6100,
  "prompt_sections": {
    "system": "hash:abc123",
    "agent_bundle": "hash:def456",
    "item1_text": "hash:ghi789",
    "contract": "hash:jkl012",
    "prior_outputs": ["01_business_profile.json"]
  },
  "tool_calls": [
    {"tool": "internet_search", "query": "AAPL customer segments 2025", "tokens": 340}
  ],
  "duration_ms": 4200
}
```

**When to enable:** Always during Phase 1A (we need to understand how the builder behaves). Optional in Phase 1B (enable for failed/degraded sprints only). Disabled by default in production (Phase 2+).

### Pilot Metrics CSV (aggregated across 25 companies)

```
ticker,industry,status,total_cost,duration_min,quality_score,confidence,sprints_passed,sprints_degraded,retries_total,grounding_fails,model_upgrades
AAPL,technology,completed,0.32,8.5,72,medium,8,0,1,0,0
JPM,banking,completed,0.45,11.2,65,low,7,1,3,2,2
```

### Post-hoc debugging

Every file in `state/{ticker}/` is a snapshot. To debug a failed sprint:
1. Read `contract.json` — what was expected
2. Read `builder_output.json` — what was produced
3. Read `eval_result.json` — what specifically failed (including grounding contradictions)
4. Read `builder_trace.json` — what the builder actually saw and did
5. All in plain JSON, no context reconstruction needed

---

## G. Implementation Phases

### Phase 1A: Single Sprint E2E (Weeks 1-2)

**Goal:** One sprint (business_profile) working with full build->evaluate->retry loop on 5 companies.

**Build order:**
1. `harness/contracts/01_business_profile.json` — Hand-author the contract (co-authored), including grounding checks
2. `harness/state_manager.py` — File I/O: create state dirs, read/write JSONs, update manifest. **Parameterized root path** for future multi-tenancy
3. `harness/evaluator.py` — 4-layer evaluation: schema + cross-reference + grounding + LLM adversarial
4. `harness/builder.py` — Contract-driven generator with prompt caching structure (static prefix, dynamic suffix)
5. `harness/orchestrator.py` — Single-sprint loop: build -> eval -> retry -> write manifest. Per-sprint model routing from contract
6. `harness/cost_tracker.py` — Token counting (input/output/cached) + Tavily cost tracking
7. Run on: AAPL, WMT, MSFT, JPM, SBUX (one per major industry category)

**Success criteria:**
- 5/5 produce valid business_profile.json
- Mean cost < $0.06 per company (single sprint, with caching)
- Mean eval score >= 12/20
- Zero grounding contradictions on 4/5 companies (1 allowed for edge case calibration)
- All state files written and inspectable
- builder_trace.json logged for all runs

**Key files to create:**
- `backend/app/nlp/research_agent/harness/` — new directory
- Import tool functions (`get_quantitative_data`, `internet_search`, `save_json_output`) from `experimental/exp_01_business_profile.py`
- Keep `experimental/` intact as reference/sandbox

### Phase 1A-review: Human Calibration (end of Week 2)

**Goal:** Build a golden set to calibrate the LLM evaluator.

**Process:**
1. Manually review all 5 business_profile.json outputs ourselves
2. Score each on the same 4 LLM eval criteria (evidence quality, consistency, completeness, red flags) — 0-5 each
3. Compare our scores to the LLM evaluator's scores
4. If gap > 2 points on any dimension: tune evaluator prompt
5. Save our human scores as `state/{ticker}/sprints/01_business_profile/human_eval.json`

**Success criteria:**
- Human-LLM evaluator score correlation > 0.7 across dimensions
- If evaluator is consistently too lenient: tighten adversarial prompt
- If evaluator is consistently too harsh: loosen thresholds

**Why this matters (from PE guide §12.8):** LLM-as-judge is only as good as its calibration. Without a human baseline, we can't tell if the evaluator is catching real problems or missing them. 5 companies is enough to calibrate — we're not training a model, just tuning a prompt.

### Phase 1B: All 8 Sprints (Weeks 3-4)

**Goal:** Full pipeline on 25 companies.

**Build order:**
1. Author 7 more contracts (one per remaining JSON), each with model_tier and grounding checks
2. Add sprint-specific system prompts (from qualitative-analysis-v2.md §2-§11)
3. Add dependency resolution (each builder gets only the prior JSONs it needs)
4. Implement prompt caching: static prefix (agent-bundle + Item 1) cached across sprints 2-8
5. Add `EXECUTIVE_BRIEF.md` generation as final step (template-driven from thesis.json)
6. Add `pilot_runner.py` — batch runner for 25 companies, outputs metrics CSV
7. Run pilot, collect metrics, iterate on prompts/contracts

**Success criteria:**
- >= 22/25 companies complete (88%)
- Mean cost <= $0.40 per company (with prompt caching)
- Mean quality score >= 65
- Mean duration <= 12 minutes per company
- Zero infinite loops or unrecoverable crashes
- Grounding contradiction rate < 10% across all sprints

**Per-sprint model routing decision:** After Phase 1A results, set `model_tier` per contract. High-judgment sprints (moat, management, thesis) may need Sonnet; extraction sprints (business_profile, industry) stay on Haiku.

**25-company pilot set (diverse industries):**
AAPL, MSFT, CRM, GOOG (tech) | JPM, BAC (banking) | O, SPG (REITs) | NEE, DUK (utilities) | XOM, CVX (energy) | LMT, RTX (defense) | JNJ, UNH (healthcare) | SBUX, MCD (consumer/neg equity) | WMT, COST (retail) | NOW, ADBE (SaaS) | PG, KO (consumer staples) | AMZN (e-commerce)

### Phase 1B-review: Pilot Retrospective (end of Week 4)

1. Generate pilot metrics CSV
2. Human spot-check 5 companies (one per industry cluster): read all 8 JSONs + EXECUTIVE_BRIEF.md
3. Identify systematic failure patterns (e.g., "moat sprint fails on banks consistently")
4. Tune contracts, prompts, grounding checks based on findings
5. **Go/no-go decision** for Phase 2

### Phase 2: Docker Integration (Weeks 5-6, after pilot validates quality)

- Celery task wrapper for `orchestrator.py`
- DB model for `QualitativeReport` (store manifest + output JSONs), with `user_id` FK from day one
- API endpoints: `POST /company/{ticker}/qualitative/start`, `GET .../status`, `GET .../report`
- All API endpoints require auth and scope by `user_id` (ownership verification pattern from PE guide §12.11)
- State files move from local disk to MinIO/S3

### Phase 3: UI Integration + Multi-Tenancy (Week 7-8)

- React tab "Qualitative Analysis" on company page
- Render EXECUTIVE_BRIEF.md + JSON explorer
- Trigger button for on-demand analysis
- Auth middleware on qualitative endpoints
- State path: `state/{user_id}/{ticker}/` (one-line change in state_manager since root is parameterized)
- Per-user cost tracking in manifest

---

## H. Key Design Decisions & Tradeoffs

| Decision | Alternative | Why this choice |
|----------|-------------|-----------------|
| Sequential sprints | Parallel sprints 2/3/5 | Simpler to debug; parallel saves ~2 min but adds orchestration complexity. Revisit in Phase 2 |
| Per-sprint model routing | Same model for all sprints | Not all sprints are equally hard. Route extraction to Haiku, judgment to Sonnet. Saves cost on easy sprints, improves quality on hard ones |
| Haiku first, upgrade per-sprint | Start with Sonnet everywhere | Start cheapest, measure quality per sprint, upgrade only where failure mode is demonstrated |
| 4-layer evaluation | 2-layer (schema + LLM) | Grounding check (Layer 3) catches the most dangerous failure: plausible-looking wrong analysis. Free to run |
| Prompt caching | No caching | 40-60% input token cost reduction for sprints 2-8 on same ticker. Just requires ordering prompt sections correctly |
| Human calibration step | Trust LLM evaluator blindly | LLM-as-judge needs a baseline. 5 human-reviewed outputs is enough to tune the evaluator prompt |
| Item 1 text as input | Tavily-only for context | Item 1 is free, primary-source, and already in DB. Provides the richest evidence for business/moat/risks |
| 2 retries max | Unlimited retries | Diminishing returns after 2 retries. If 3 attempts fail, the prompt/contract needs revision, not more retries |
| Proceed on degraded sprint | Block pipeline | Downstream sprints can work with partial data. Thesis notes lower confidence. More useful than no output |
| Parameterized state root | Hardcoded `state/{ticker}/` | Multi-tenancy becomes a config change, not an architecture rewrite. Zero cost now, saves weeks later |
| deepagents framework | Raw Anthropic API | Already working in exp_01. Tool calling and tracing built in. Switch to raw API only if deepagents becomes a bottleneck |
| Import tools from experimental/ | Copy or refactor in-place | Avoids code duplication. experimental/ stays as sandbox. Harness builds fresh orchestration on top of proven tool functions |

---

## I. Critical Files

### Existing (reference/reuse)
- `backend/app/nlp/research_agent/experimental/exp_01_business_profile.py` — Working builder pattern + tool functions to import
- `docs/spec-ideas/qualitative-analysis-v2.md` — JSON schemas, prompts, scoring rubric (source of truth)
- `backend/app/api/v1/routes.py:258-331` — `/agent-bundle` endpoint
- `backend/app/core/industry.py` — SIC->category->agent notes
- `backend/app/nlp/fourm/service.py` — Four Ms scoring (moat, management, balance sheet, MOS)
- `backend/app/metrics/compute.py` — All metric functions

### New (to create)
- `backend/app/nlp/research_agent/harness/__init__.py`
- `backend/app/nlp/research_agent/harness/orchestrator.py` — Sprint loop, model routing, retry logic
- `backend/app/nlp/research_agent/harness/builder.py` — Contract-driven generator with prompt caching
- `backend/app/nlp/research_agent/harness/evaluator.py` — 4-layer evaluation (schema, cross-ref, grounding, LLM)
- `backend/app/nlp/research_agent/harness/grounding.py` — Deterministic grounding checks (numeric claims vs agent-bundle)
- `backend/app/nlp/research_agent/harness/state_manager.py` — Parameterized root path, file I/O
- `backend/app/nlp/research_agent/harness/cost_tracker.py` — Token counting (input/output/cached) + Tavily
- `backend/app/nlp/research_agent/harness/contracts/*.json` — 8 contract files with model_tier + grounding rules
- `backend/app/nlp/research_agent/harness/prompts/` — 8 sprint-specific prompt files
- `backend/app/nlp/research_agent/harness/pilot_runner.py` — Batch runner, metrics CSV output

---

## J. Verification Plan

### Phase 1A verification (single sprint)
1. Run `orchestrator.py AAPL` — check all state files created (including builder_trace.json)
2. Validate `builder_output.json` against JSON schema manually
3. Verify `eval_result.json` has correct pass/fail, including grounding check results
4. Check `manifest.json` has accurate cost/timing/model routing
5. Force a failure (corrupt builder output) — verify retry loop works
6. Force a grounding contradiction (e.g., stub bad ROIC in agent-bundle) — verify Layer 3 catches it
7. Force budget exceeded — verify graceful degradation
8. Run on 5 companies, compare outputs for industry-appropriate content

### Phase 1A-review verification (human calibration)
1. Manually score all 5 outputs on 4 dimensions (0-5 each)
2. Compare against LLM evaluator scores
3. Correlation > 0.7 = evaluator is calibrated
4. Correlation < 0.7 = tune evaluator prompt, re-run, re-compare

### Phase 1B verification (full pipeline)
1. Run `pilot_runner.py` on 25 companies
2. Generate metrics CSV — check all columns populated
3. Spot-check 5 companies (one per industry cluster): read all 8 JSONs + EXECUTIVE_BRIEF.md
4. Check cross-references: peers.json names match industry.json peer_candidates
5. Check thesis.json quality_score matches rubric math
6. Review degraded sprints: understand WHY they failed, iterate prompts/contracts
7. Compare AAPL/WMT outputs with existing exp_01 outputs — quality should be equal or better
8. Check grounding contradiction rate across all sprints — target < 10%

---

## K. Resolved Decisions

1. **Model choice:** Start with Haiku 4.5 for all sprints. Per-sprint routing — upgrade individual sprints to Sonnet based on Phase 1A pass rates (< 80% = upgrade). Not all-or-nothing.
2. **Data sources:** Agent-bundle + SEC Item 1 text + Tavily. Item 1 is free primary-source evidence.
3. **Contract authoring:** Co-author business_profile contract together first. Once pattern is validated, draft remaining 7 for review.
4. **Experimental code:** Import tool functions from experimental/, build fresh harness. experimental/ stays as reference.
5. **Multi-tenancy:** Deferred to Phase 3. Low retrofit cost because state_manager parameterizes the root path from day one. API endpoints (Phase 2) include user_id FK from the start.
6. **Prompt caching:** Structure all builder prompts with static prefix (agent-bundle + Item 1) and dynamic suffix (contract + prior outputs) to maximize cache hits.
7. **Grounding checks:** Layer 3 deterministic verification of builder claims against agent-bundle data. Free, catches hallucinations against our own data.
8. **Human calibration:** Manual review of 5 outputs after Phase 1A to calibrate LLM evaluator accuracy.

---

## L. Implementation Start — Phase 1A First Steps

1. **Co-author `contracts/01_business_profile.json`** — Define schema checks, cross-references, grounding checks, and LLM evaluation rubric together
2. **Build `state_manager.py`** — Parameterized root path, file I/O for state dirs, manifest, sprint files
3. **Build `grounding.py`** — Deterministic checks: extract numeric claims from builder output, verify against agent-bundle
4. **Build `evaluator.py`** — 4-layer evaluation: schema + cross-reference + grounding + Haiku adversarial
5. **Build `builder.py`** — Contract-driven generator with prompt caching structure (static prefix, dynamic suffix)
6. **Build `orchestrator.py`** — Single-sprint loop: build -> eval (4 layers) -> retry -> manifest update. Model routing from contract
7. **Build `cost_tracker.py`** — Token counting (input/output/cached) + Tavily
8. **Test on AAPL** — Validate full loop end-to-end, verify builder_trace.json logged
9. **Run on 5 companies** (AAPL, WMT, MSFT, JPM, SBUX) — Measure cost/quality/time
10. **Human calibration** — Manually score 5 outputs, compare to LLM evaluator, tune if needed

---

## M. Risks & Open Questions

### Known risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Haiku too weak for judgment sprints (moat, thesis) | Medium | Quality scores < 12/20 | Per-sprint Sonnet upgrade; Phase 1A is the test |
| 8 sequential JSONs feel like a checklist, not integrated analysis | Medium | Thesis lacks coherence | Sprint 8 (thesis) gets all prior outputs; if still poor, add cross-sprint revision step |
| Grounding checks too brittle (false positives on edge cases) | Medium | Valid outputs flagged as failures | Tune thresholds per industry during pilot; allow 1-2 soft contradictions before fail |
| Evaluator can't catch financial reasoning errors | High | Wrong analysis passes as correct | Human calibration step; expand golden set over time |
| Tavily search returns stale/irrelevant results | Low | Builder fills gaps with bad data | Agent-bundle + Item 1 are primary sources; Tavily is supplementary |

### Open questions (to resolve during Phase 1A)

1. **Grounding check granularity:** How aggressively do we extract/verify numeric claims? Start strict, loosen if false positive rate > 15%?
2. **Cross-sprint coherence:** Will sprint 8 (thesis) naturally produce an integrated narrative, or will it need explicit instructions to reconcile contradictions between earlier sprints?
3. **Industry-specific contract tuning:** Should bank/REIT/utility contracts have different grounding thresholds? (e.g., ROIC < 10% is normal for banks, not a contradiction)

---

## N. Implementation Approach — Sub-Agent Loops

Not all modules need the same implementation rigor. Simple file I/O modules can be written directly. Complex modules with edge cases, multi-layer logic, or quality-critical behavior benefit from a 3-agent iteration loop: **code writer → test generator → critic**.

### Module Classification

| Module | Approach | Rationale |
|--------|----------|-----------|
| `state_manager.py` | Direct write | Simple file I/O (mkdir, read/write JSON, update manifest). No ambiguity in behavior |
| `cost_tracker.py` | Direct write | Simple arithmetic (sum tokens, multiply by rate). Straightforward tests |
| `grounding.py` | **3-agent loop** | Complex claim extraction from free-text JSON values. Needs thorough tests for edge cases (e.g., "double-digit" vs "12%", negations like "not growing", industry-normal values). Most novel code in the harness |
| `evaluator.py` | **3-agent loop** | 4-layer logic with many edge cases per layer. Layer 3 calls grounding.py. Layer 4 manages LLM prompt construction. Needs tests for pass/fail boundary conditions |
| `builder.py` | **3-agent loop** | Prompt caching structure (static prefix, dynamic suffix), contract handling, dependency injection of prior sprint outputs. Quality-critical — builder bugs produce bad analysis at scale |
| `orchestrator.py` | **3-agent loop** | Retry logic, model routing from contracts, budget/timeout guards, manifest updates. Integration-heavy — coordinates all other modules |
| Contracts (JSON) | Co-author together | Domain judgment calls (grounding thresholds, eval criteria). Not code — needs human review |
| Integration test | Separate pass | Runs full single-sprint pipeline (AAPL). Catches boundary bugs between modules that unit tests miss |

### 3-Agent Loop Structure

For complex modules, the implementation loop works as follows:

```
Code Writer: Writes the module implementation based on contract (the module's spec + plan section)
     ↓
Test Generator: Reads the implementation, generates comprehensive test cases
     including edge cases, boundary conditions, and failure scenarios
     ↓
Critic: Reviews both code and tests against the module's contract
     Checks: correctness, edge case coverage, consistency with plan,
     no unnecessary abstractions, no missing error paths
     ↓
If critic finds issues → Code Writer revises → loop (max 2 iterations)
```

### Critic Contract (what the critic checks)

The critic is not a general-purpose reviewer. It grades against a specific checklist per module:

1. **Contract compliance:** Does the code do what the plan says? No more, no less
2. **Edge case coverage:** Are the test cases thorough? Do they cover the examples in the plan?
3. **Interface consistency:** Do the function signatures match what other modules expect? (e.g., `evaluator.py` must accept `builder_output` dict and return `eval_result` dict matching the schema in §C)
4. **No gold-plating:** No unnecessary abstractions, no features not in the plan, no "future-proofing" beyond what the plan explicitly calls for (e.g., parameterized root path in state_manager — yes; generic plugin system — no)

### When NOT to use the loop

- **Contracts (JSON):** These are domain judgment, not code. We co-author them together with discussion
- **Prompts:** Same — prompt engineering needs human judgment
- **Direct write modules:** state_manager and cost_tracker are simple enough that a single pass with review is sufficient. If bugs surface during integration testing, fix them directly

### Integration Testing

After all modules are built, a separate integration test validates the full pipeline:

1. Start with a real AAPL agent-bundle (cached, not live API call)
2. Run orchestrator for a single sprint (business_profile)
3. Verify: state directory created → builder_output.json written → eval_result.json written → manifest.json updated → cost tracked → builder_trace.json logged
4. Force a builder failure (invalid JSON) → verify retry loop fires → verify manifest shows attempt count
5. Force a grounding contradiction → verify Layer 3 catches it → verify eval_result shows the failure

This catches interface mismatches between modules that unit tests cannot.

---

## Appendix: Design Principles Applied

Each component maps to a specific failure mode:

| Component | Failure Mode Solved | Source |
|-----------|-------------------|--------|
| Sprint-per-JSON structure | Context window degradation | Anthropic Harness Guide, Failure Mode 1 |
| Separate Evaluator agent | Self-evaluation bias | Anthropic Harness Guide, Failure Mode 2 |
| Pre-negotiated contracts | Subjective acceptance conditions | Anthropic Harness Guide, Failure Mode 3 |
| File-based state | Implementation drift in multi-agent | Anthropic Harness Guide, Part 3 |
| Deterministic checks first | Wasted LLM cost on structural failures | Anthropic Harness Guide, Part 2 |
| Budget/timeout guards | Runaway costs, infinite loops | Anthropic Harness Guide, Part 4 |
| Adversarial evaluator framing | Optimism bias in review | Anthropic Harness Guide, Part 2 (GAN pattern) |
| **Per-sprint model routing** | Over-paying for easy tasks, under-powering hard tasks | PE Guide §12.9.3 (model routing) |
| **Prompt caching** | Redundant token costs across sprints | PE Guide §12.9.1 (prompt caching) |
| **Grounding checks** | Silent quality degradation — valid JSON with wrong content | PE Guide §12 (hallucination returns 200) |
| **Human calibration (golden set)** | Uncalibrated LLM evaluator | PE Guide §12.8 (eval tiers) |
| **Full prompt/response logging** | Can't debug quality regressions without seeing exact inputs | PE Guide §12.8 (observability) |
| **Parameterized state root** | Expensive multi-tenancy retrofit | PE Guide §12.11 (isolation architecture) |
