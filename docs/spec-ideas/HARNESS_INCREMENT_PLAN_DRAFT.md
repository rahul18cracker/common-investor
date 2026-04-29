# Harness Increment Plan — Finalized

> **Date:** 2026-04-29 | **Status:** Finalized — approved for implementation
> **Context:** Phase 1A AAPL pilot passed (14/20, $0.005, 1 attempt). Identified gaps: no real API
> integration, hardcoded data, missing framework context, no sanitization, broken prompt caching.
> **Scope:** 3 increments to get from "mechanics validated" to "multi-company pilot with real data"

---

## Decisions Made (locked)

1. **Option B (programmatic pre-fetch)** — data fetched before LLM calls, not by the LLM as a tool
2. **No data caching** for now — always fetch fresh from API; snapshot caching deferred
3. **No cost estimator** before runs (Gap E deferred) — add once pipeline works end-to-end
4. **Option C for framework context** — shared framework card in system prompt + per-sprint focus in contracts
5. **Full sanitizer kept** — three-tier approach with fallbacks; data is scraped public text, injection risk is real
6. **Sprint restart mechanism** — `resume_from_sprint()` in orchestrator + `--resume / --cascade` CLI flags
7. **Suspicious taint tracking** — injection flags stop the sprint or mark it tainted for later review
8. **Live backend is the default** — `run_aapl.py` fetches from real API by default; `--snapshot` is an
   explicit opt-in for intentional offline work; CI uses mock fixtures injected directly into orchestrator
   (never touches the run script)
9. **Model routing is failure-driven, not complexity-classified** — three levels: (a) contract sets
   `model_tier` per sprint (human judgment at authoring time), (b) retry escalation upgrades to Sonnet
   on final retry within a run, (c) post-pilot contract updates lock in permanent upgrades where failure
   rate >50%. No real-time complexity classifier — sprint complexity is already captured in the contract.

---

## Increment 1: Data Fetcher + Validation Gate + Framework Card + Sanitizer

**Goal:** Agent consumes real data from backend APIs, validated and sanitized before LLM calls, with proper
framework knowledge baked in, and structural prompt architecture that minimizes injection surface.

---

### Step 1.1 — Framework Card (~800 tokens in system prompt)

**File:** `backend/app/nlp/research_agent/harness/framework_card.py`

Single Python string constant `FRAMEWORK_CARD` distilled from `docs/spec-ideas/summary-rule1-v3.md`
and `docs/spec-ideas/qualitative-analysis-v1.md`. Prepended to `BUILDER_SYSTEM_PROMPT` in `builder.py`.

**Sections (budget: 800-1000 tokens):**
- Framework identity: Rule #1 (Four Ms + Big Five) and QVG (Quality-Valuation-Growth)
- Four Ms: Meaning, Moat (5 types + evidence proxies), Management (capital allocation + governance), MOS (50% default, flex with quality)
- Big Five thresholds: ROIC ≥15% sustained, CAGR consistency 1/3/5/10yr, Owner Earnings = CFO − CapEx, coverage >5x comfortable
- QVG quality scoring rubric: Moat & Durability (0-25), Revenue Quality (0-15), Pricing Power (0-15), Industry Structure (0-15), Management & Allocation (0-20), Balance Sheet Resilience (0-10)
- Computed metric definitions: how ROIC, CAGR, pricing_power_score (0-1), roic_persistence (0-5), balance_sheet (0-5), management (0-1), MOS recommendation (0.3-0.7) are derived — so agent interprets the numbers correctly
- Red flags checklist (top 10 from both frameworks)

**Also update:** `EVALUATOR_SYSTEM_PROMPT` in `evaluator.py` — add the QVG scoring rubric so the
evaluator grades against the framework, not a generic "skeptical analyst" framing.

**Per-sprint focus:** Add `framework_focus` field to each contract JSON. Example for `04_moat`:
```json
"framework_focus": "Apply Rule #1 Five Moat Types (brand, network effects, cost advantage, switching
costs, regulatory/toll bridge). Evidence must link to ROIC persistence, gross margin stability, or
specific competitive barriers. Rate durability 0-5 per QVG methodology."
```

---

### Step 1.2 — DataFetcher Class

**File:** `backend/app/nlp/research_agent/harness/data_fetcher.py`

```python
@dataclass
class FetchResult:
    agent_bundle: dict | None
    item1_text: str | None
    errors: list[str]
    fetch_duration_seconds: float
    success: bool  # True only if both fetched without error

class DataFetcher:
    def __init__(self, base_url: str = "http://localhost:8080/api/v1"):
        ...
    def fetch_agent_bundle(self, ticker: str) -> dict
    def fetch_item1_text(self, ticker: str) -> str
    def fetch_all(self, ticker: str) -> FetchResult
```

**Error handling (all captured in FetchResult.errors, never raised):**
- 404 → "Company {ticker} not ingested. Run POST /company/{ticker}/ingest first."
- Connection refused → "Backend API not reachable at {base_url}. Is Docker running?"
- Timeout (30s) → "API timeout after 30s for {ticker}/{endpoint}"
- Unexpected status → "HTTP {status} from {endpoint}"

---

### Step 1.3 — Response Validators

**File:** `backend/app/nlp/research_agent/harness/data_validator.py`

**Level 1 — Schema validation (all sprints):**
- `validate_agent_bundle(bundle)` → list of issues
  - Required keys: company, metrics, timeseries
  - company must have: cik, ticker, name
  - metrics must have at least one non-None growth value
  - timeseries.is must have ≥1 entry with revenue
- `validate_item1_text(text)` → list of issues
  - Not empty, ≥100 chars, no HTML tags remaining

**Level 2 — Per-sprint completeness gates:**
```python
SPRINT_DATA_REQUIREMENTS = {
    "01_business_profile": {
        "agent_bundle": ["company.ticker", "company.name", "timeseries.is"],
        "item1_text": True,
    },
    "02_unit_economics": {
        "agent_bundle": ["metrics.latest_operating_margin", "metrics.latest_fcf_margin", "timeseries.is"],
        "item1_text": True,
    },
    "04_moat": {
        "agent_bundle": ["four_ms.moat", "metrics.roic_avg_10y", "quality_scores"],
        "item1_text": True,
    },
    "05_management": {
        "agent_bundle": ["four_ms.management", "quality_scores.share_count_trend"],
        "item1_text": False,
    },
    # ... all 8 sprints
}

@dataclass
class SprintReadiness:
    ready: bool
    missing_fields: list[str]
    warnings: list[str]  # e.g. "Only 3 years of timeseries data (5+ recommended)"
```

**Data gate in orchestrator:** sprint not ready → mark `data_incomplete`, log missing fields, skip
to next sprint. $0 LLM cost.

---

### Step 1.4 — Input Sanitizer (three-tier with fallback)

**File:** `backend/app/nlp/research_agent/harness/sanitizer.py`

#### Architecture

Three tiers always run in sequence. Each tier is independent; a failure in T2/T3 falls back gracefully.
Every hit is logged with tier, matched pattern/score, field path, and a truncated text excerpt.

```
Text in → [T1: Regex] → [T2: DeBERTa, optional] → [T3: Haiku, optional] → SanitizeResult out
```

#### SanitizeResult dataclass

```python
@dataclass
class SanitizeResult:
    clean: bool             # False if any hard block triggered
    tainted: bool           # True if suspicious but not blocked (logged for review)
    action: str             # "pass" | "blocked" | "suspicious"
    tier_fired: str | None  # "T1_regex" | "T2_deberta" | "T3_haiku" | None
    confidence: float       # 0.0-1.0 from whichever tier fired (1.0 for regex hits)
    details: list[str]      # what matched and where
    sanitized_text: str     # text after T1 cleanup (control chars stripped, truncated)
```

#### Tier 1 — Regex (always active, <1ms)

Two categories:

**Hard-block patterns** (clear injection, no financial document context):
```python
INJECTION_HARD = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\byou\s+are\s+now\s+a\b",
    r"```\s*system",
    r"<\s*/?\s*system\s*>",
    r"\bIMPORTANT:\s*override\b",
    r"\bACT\s+AS\b.*\bAI\b",
]
```

**SEC whitelist** — financial phrases that look like injection but are legitimate:
```python
SEC_FINANCIAL_WHITELIST = [
    r"\boverride.*agreement\b",        # "override the previous agreement" in contracts
    r"\bignore.*covenant\b",           # debt covenant language
    r"\bsystem.*risk\b",               # "systemic risk factors"
    r"\byou\s+are\s+now\s+required\b", # regulatory compliance language
    r"\bdisregard.*prior\b",           # "disregard prior period adjustments"
    r"\binstruction\s+\d+\b",          # "instruction 12(b)" in filing forms
]
```

Whitelist is checked first. If text matches a whitelist pattern AND an injection pattern, it is
classified as `suspicious` (not blocked) and routed to T2/T3 for secondary review.

T1 also performs cleanup regardless of injection verdict:
- Strip control characters (except `\n`, `\t`)
- Truncate to `max_length` (default 30000 for Item1, 10000 for bundle strings)
- Strip residual HTML tags

#### Tier 2 — DeBERTa classifier (optional, 50-150ms)

Model: `protectai/deberta-v3-base-prompt-injection-v2` (550MB, Apache 2.0, CPU-capable)

Loaded lazily at first use. If `transformers` is not installed, T2 silently skips (T1 result stands).

```python
try:
    from app.nlp.research_agent.harness._injection_classifier import classify_injection
    _T2_AVAILABLE = True
except ImportError:
    _T2_AVAILABLE = False
```

Threshold: confidence ≥ 0.80 → `suspicious`. Confidence ≥ 0.95 and no SEC whitelist match → `blocked`.

T2 is only called when T1 returned `pass` or `suspicious` (never after T1 hard-block — saves latency).

#### Tier 3 — Haiku edge case review (optional, ~1-3s per call)

Only activates when T2 flagged `suspicious` AND text also matched an SEC whitelist pattern (the ambiguous
case where T2 can't distinguish financial language from injection). Budget: ~$0.40 per 1000 calls.

Prompt: a minimal one-turn classification call asking Haiku to decide `injection | financial_language`
with a short rationale. Result stored in the `details` list of SanitizeResult.

T3 is off by default. Enabled via `ENABLE_T3_CLASSIFIER=1` env var.

#### Sprint taint propagation

`sanitize_agent_bundle()` and `sanitize_item1_text()` return `SanitizeResult` objects. The orchestrator
checks them before the sprint build:

```python
result = sanitize_item1_text(item1_text)
if result.action == "blocked":
    # hard stop — mark sprint tainted_blocked, skip LLM call
    state.update_sprint_in_manifest(sprint_name, {
        "status": "tainted_blocked",
        "taint_reason": result.details,
        "taint_tier": result.tier_fired,
    })
    continue

if result.action == "suspicious":
    # soft flag — continue but mark sprint tainted_suspicious for human review
    state.update_sprint_in_manifest(sprint_name, {
        "status": "tainted_suspicious",   # updated to passed/degraded after eval
        "taint_reason": result.details,
        "taint_tier": result.tier_fired,
        "taint_confidence": result.confidence,
    })
    # LLM call proceeds, but sprint is flagged in manifest
```

A run that completes with any `tainted_*` sprints gets overall status `completed_with_taint` instead of
`completed`. The final manifest lists which sprints are tainted so a human reviewer can inspect and
decide whether to discard those sprints' outputs.

**Sanitization also applied to prior sprint outputs** before feeding to downstream sprints — an injected
output from sprint 01 should not cascade into sprint 04.

---

### Step 1.5 — Fix Prompt Caching

**Structural isolation (dual benefit: caching + injection hardening)**

Move the agent-bundle + Item 1 from the user message into the system block as a separate cached block.
This achieves two things simultaneously:
- Prompt caching activates (≥1024 tokens once framework card + bundle is combined, ~6000 tokens total)
- Data is structurally separated from instructions (harness design guide principle: static trusted zone vs dynamic data zone)

```python
# llm_client.py — accept static_context as a second system block
system_blocks = []
if static_context:
    system_blocks.append({
        "type": "text",
        "text": static_context,          # agent-bundle + Item 1, XML-wrapped
        "cache_control": {"type": "ephemeral"},
    })
system_blocks.append({
    "type": "text",
    "text": system_prompt,               # framework card + builder instructions
})
```

```python
# builder.py — XML-wrap data before caching
def build_static_prefix(agent_bundle: dict, item1_text: str) -> str:
    return (
        "<financial_data>\n"
        + json.dumps(agent_bundle, indent=2)
        + "\n</financial_data>\n\n"
        "<item1_text>\n"
        + item1_text
        + "\n</item1_text>"
    )
```

XML wrapping (from PE guide 12.8) signals to the model that this content is data, not instructions —
a structural injection defense on top of the sanitizer.

**LLMCallable protocol update:** Add optional `static_context: str | None = None` parameter.
Mock LLMs in tests ignore it (backward compatible — no test changes needed).

---

### Step 1.6 — Wire Into Orchestrator

**`run_all_sprints()` gains optional `base_url` and fetch-from-API mode:**

```python
def run_all_sprints(
    ticker: str,
    agent_bundle: dict | None = None,   # None → fetch from API
    item1_text: str | None = None,       # None → fetch from API
    builder_llm: ...,
    evaluator_llm: ...,
    state_root: Path | None = None,
    sprint_names: list[str] | None = None,
    base_url: str = "http://localhost:8080/api/v1",
) -> dict[str, Any]:
```

Pre-flight sequence (before any LLM calls):
1. Fetch data if not provided (DataFetcher)
2. Validate schema (data_validator — abort if company/ticker missing)
3. Sanitize agent_bundle and item1_text (sanitizer — hard blocks abort, suspicious flags manifest)
4. Write sanitized data to disk (state_manager)
5. Run sprints with per-sprint readiness gates

**Model routing — failure-driven escalation within `run_sprint()`:**

The `AnthropicLLMClient` gains a `with_model(model: str)` method that returns a new client instance
with a different model tier but the same API key and config. This avoids re-constructing from scratch.

Routing logic inside the attempt loop:

```python
for attempt in range(1, max_attempts + 1):
    # Escalate to Sonnet on the final attempt if Haiku has been failing
    effective_model = contract.get("model_tier", "haiku")
    if attempt == max_attempts and attempt > 1 and effective_model == "haiku":
        effective_model = "sonnet"
        logger.info("Sprint %s: escalating to sonnet on final attempt", sprint_name)

    # Pass effective_model to build() so it uses the right client
    builder_result = build(
        contract=contract,
        agent_bundle=agent_bundle,
        item1_text=item1_text,
        prior_outputs=prior_outputs,
        eval_failures=eval_failures if attempt > 1 else None,
        attempt=attempt,
        llm_call=builder_llm.with_model(effective_model),
    )
```

The manifest's `model_routing` field (currently always `{}`) is populated at the end of each sprint
with the actual model used per attempt:

```json
"model_routing": {
  "04_moat": {"attempt_1": "haiku", "attempt_2": "haiku", "attempt_3": "sonnet"}
}
```

This gives visibility into which sprints triggered escalation — the pilot data in Increment 3 will
show which sprints consistently hit attempt 3, informing permanent contract-level upgrades.

**Evaluator model:** Always Haiku. The evaluator prompt is shorter and more structured — escalating
the evaluator too adds cost without meaningful quality gain. Only the builder escalates.

**Sprint restart via `resume_from_sprint()`:**

```python
def resume_from_sprint(
    ticker: str,
    sprint_name: str,
    builder_llm: Callable,
    evaluator_llm: Callable,
    state_root: Path | None = None,
    cascade: bool = False,  # if True, re-run sprint_name + all downstream dependents
) -> dict[str, Any]:
    """Re-run one or more sprints using existing state (agent_bundle, item1_text already on disk).

    Validates that all dependencies of sprint_name have status 'passed' before proceeding.
    Fresh CostTracker — budget reflects only the resumed spend.
    """
    state = StateManager(ticker, state_root=state_root)
    manifest = state.read_manifest()

    # Validate dependencies
    deps = SPRINT_DEPENDENCIES.get(sprint_name, [])
    for dep in deps:
        dep_status = manifest["sprints"].get(dep, {}).get("status")
        if dep_status != "passed":
            raise ValueError(
                f"Cannot restart {sprint_name}: dependency {dep} has status '{dep_status}'"
            )

    # Determine scope
    if cascade:
        sprints_to_run = _downstream_sprints(sprint_name)
    else:
        sprints_to_run = [sprint_name]

    # Clear old artifacts for each sprint to re-run
    for name in sprints_to_run:
        _clear_sprint_artifacts(state, name)

    cost_tracker = CostTracker()
    for name in sprints_to_run:
        state.copy_contract(name)
        run_sprint(name, state, cost_tracker, builder_llm, evaluator_llm)

    return state.read_manifest()
```

**CLI flags in `run_aapl.py`:**
```
--ticker AAPL       which company (default: AAPL)
--snapshot          use hardcoded data snapshot instead of live API (intentional offline opt-in)
--resume 04_moat    restart from this sprint using existing on-disk state
--cascade           with --resume: also re-run all downstream dependents
--debug             write full prompts to disk (default: hashes + preview only)
--base-url URL      override API base URL (default: http://localhost:8080/api/v1)
```

**Default (no flags): fetch from live backend API.** Docker must be up and ticker must be ingested.
If the backend is not reachable, the script fails immediately with a clear actionable error:

```
ERROR: Could not fetch live data from backend.
  - Backend API not reachable at http://localhost:8080/api/v1. Is Docker running?

To start the backend:  docker compose up -d
To ingest AAPL:        curl -X POST http://localhost:8080/api/v1/company/AAPL/ingest
To run offline:        python run_aapl.py --snapshot
```

**`--snapshot` is an explicit escape hatch**, not the comfortable default. The hardcoded snapshot
data stays in the file as a reference and for offline/demo use — it is never reached in normal dev.

**CI separation:** Tests inject `agent_bundle` and `item1_text` directly into `run_all_sprints()`
and `run_sprint()` via parameters. The test suite never calls `run_aapl.py` or `DataFetcher`.
Mock data lives only in pytest fixtures — it cannot bleed into developer runs.

---

### Step 1.7 — Full Prompt Logging in Builder Trace

Every attempt (success or failure) writes to `builder_trace.json`:

```python
{
    "model": builder_result.model,
    "input_tokens": builder_result.input_tokens,
    "output_tokens": builder_result.output_tokens,
    "cached_tokens": builder_result.cached_tokens,
    "duration_seconds": builder_result.duration_seconds,
    "attempt": attempt,
    "error": not builder_result.success,
    "system_prompt_hash": sha256(system_prompt)[:12],
    "static_context_hash": sha256(static_context)[:12],
    "user_prompt_hash": sha256(user_prompt)[:12],
    "raw_response_preview": raw_response[:1000],
}
```

When `--debug` is set, also writes full prompts to:
- `builder_prompt_attempt_{n}_system.txt`
- `builder_prompt_attempt_{n}_user.txt`

Default off — prompts contain the full agent-bundle (~5KB) and Item 1 (~25KB) and shouldn't
be written on every run.

---

### Step 1.8 — Tests for New Modules

| File | What it tests |
|------|--------------|
| `test_data_fetcher.py` | Mock httpx: 200, 404, timeout, connection refused. FetchResult fields. |
| `test_data_validator.py` | Valid bundles, missing fields, sparse timeseries, empty Item 1, sprint gates. |
| `test_sanitizer.py` | T1 hard blocks, SEC whitelist pass-through, suspicious category, taint propagation into manifest, T2 fallback when `transformers` absent, XML wrapping. |
| `test_framework_card.py` | Card is valid string, under 1200 tokens, contains key terms (ROIC, moat, QVG, Four Ms). |
| `test_builder.py` (update) | Framework card in system prompt. static_context passed separately. |
| `test_orchestrator.py` (update) | data_incomplete status. tainted_blocked aborts LLM call. tainted_suspicious lets LLM run but flags manifest. resume_from_sprint validates deps. cascade re-runs downstream. |

---

### Increment 1 Deliverables

| File | Type | Purpose |
|------|------|---------|
| `framework_card.py` | New | ~800 token Rule #1 + QVG reference card |
| `data_fetcher.py` | New | HTTP client for /agent-bundle + /fourm/meaning/refresh |
| `data_validator.py` | New | Schema validation + per-sprint completeness gates |
| `sanitizer.py` | New | Three-tier sanitizer (regex + DeBERTa + Haiku) with taint tracking |
| `_injection_classifier.py` | New | Lazy DeBERTa wrapper (optional dep on `transformers`) |
| `llm_client.py` | Modified | Accept static_context for prompt caching; add `with_model()` for escalation |
| `builder.py` | Modified | Prepend framework card, XML-wrap data, pass static_context, accept model override |
| `evaluator.py` | Modified | Add QVG rubric to evaluator system prompt |
| `orchestrator.py` | Modified | Data gate, sanitizer gate, taint tracking, failure-driven escalation, populate model_routing in manifest, resume_from_sprint() |
| `run_aapl.py` | Modified | Live default, --snapshot opt-in, --ticker, --resume, --cascade, --debug, --base-url |
| Contracts `01-08` | Modified | Add `framework_focus` field; set `model_tier: sonnet` for `08_thesis` |
| 6 test files | New/Modified | Full coverage of new modules |

### Increment 1 Success Criteria

- `python -m app.nlp.research_agent.harness.run_aapl` (no flags) fetches from live API — fails clearly if Docker is down
- `python -m app.nlp.research_agent.harness.run_aapl --snapshot` uses hardcoded data without touching the backend
- Data validation catches missing fields before LLM call ($0 cost on incomplete data)
- Framework card visible via `system_prompt_hash` in builder_trace
- Prompt caching shows `cached_tokens > 0` on sprint 2+ of a multi-sprint run
- Sanitizer: T1 blocks known patterns, SEC whitelist phrases pass through, suspicious cases appear in manifest
- Sprint marked `tainted_blocked` when hard injection detected — no LLM call made
- Model escalation: when a sprint exhausts Haiku retries, final attempt uses Sonnet; `model_routing` in manifest reflects actual models used
- `--resume 04_moat` works when dependencies are `passed`; `--cascade` re-runs downstream
- All existing 203 tests still pass; CI tests never touch DataFetcher or run_aapl.py
- New tests pass with >90% coverage on new modules

---

## Increment 2: Multi-Sprint Contracts + Debug Mode

**Goal:** All 8 sprint contracts authored, full prompt observability, AAPL runs end-to-end.

### Step 2.1 — Author Contracts 03-08

Each contract follows the `01_business_profile` pattern:
- `output_schema`: required_fields, field_types, enums, array_minimums, string_minimums
- `cross_references`: checks against agent_bundle + prior sprint outputs
- `grounding_checks`: sprint-specific hallucination detectors
- `llm_eval_criteria`: 4 dimensions × 5 points (evidence, completeness, consistency, red_flags)
- `framework_focus`: which Rule #1 / QVG concepts to emphasize
- `pass_threshold`: minimum combined score

**Authoring order** (hardest judgment tasks first):
1. `04_moat` — ROIC persistence, five moat types, durability scoring
2. `08_thesis` — synthesizes all prior sprints; most grounding surface
3. `03_industry` — competitive structure, SIC classification grounding
4. `05_management` — capital allocation, incentives, insider behavior
5. `07_risks` — depends on all prior sprints; widest dependency graph
6. `06_peers` — depends on industry; comparative scoring
7. `02_unit_economics` — upgrade from stub; margins, pricing power metrics

Each contract authored in a separate discussion session — these require domain judgment calls, not just coding.

### Step 2.2 — Full Prompt Capture (Debug Mode)

`--debug` flag (wired in Step 1.7) writes:
- `builder_prompt_attempt_{n}_system.txt` — full system prompt including framework card
- `builder_prompt_attempt_{n}_user.txt` — full user prompt including per-sprint contract + prior outputs
- `eval_prompt.txt` — full evaluator prompt

Enables post-hoc debugging: "what exactly did the LLM see on attempt 2?"

### Step 2.3 — Run AAPL Full Pipeline (8 Sprints)

With all contracts authored:
- Run `--live` against real AAPL data
- Verify sprint dependencies resolve correctly (moat gets business_profile + unit_economics + industry)
- Verify prompt caching activates on sprints 2-8
- Verify total cost within soft budget ($0.50)
- Compare evidence_quality scores to the 2/5 baseline (framework card should improve this)

### Increment 2 Deliverables

| File | Type | Purpose |
|------|------|---------|
| Contracts `03-08` | New | Full contracts for all remaining sprints |
| `02_unit_economics.json` | Modified | Upgrade from stub to full contract |
| `run_aapl.py` | Already modified | --debug flag (from Step 1.7) |

---

## Increment 3: Multi-Company Pilot with Real Data

**Goal:** Validate harness across 5 diverse companies, measure quality, calibrate evaluator.

### Step 3.1 — Ensure All 5 Companies Ingested

Boot Docker. Ingest: AAPL (tech), WMT (retail), MSFT (tech/SaaS), JPM (banking), SBUX (consumer/negative equity).
Verify each has: full agent-bundle, Item 1 text extracted, ≥5 years of timeseries.

### Step 3.2 — Create `pilot_runner.py`

Batch runner:
1. Takes list of tickers
2. Runs full 8-sprint pipeline per ticker (--live)
3. Outputs `pilot_metrics.csv`:

```
ticker,industry,status,total_cost,duration_min,sprints_passed,sprints_degraded,sprints_data_incomplete,sprints_tainted,evidence_quality_avg,grounding_contradictions,cache_hit_rate
AAPL,technology,completed,0.18,4.2,8,0,0,0,3.5,0,0.72
JPM,banking,completed_with_taint,0.22,5.1,7,1,0,1,3.0,1,0.68
```

Note: `completed_with_taint` status and `sprints_tainted` column added for the sanitizer integration.

### Step 3.3 — Run Pilot + Analyze

- Run all 5 companies
- Check: does JPM (banking) handle correctly? Does SBUX (negative equity) trigger appropriate warnings?
- Check: do any tainted sprints appear? What triggered them?
- Identify systematic failures: which sprints fail most? Which grounding checks fire?
- Measure: did the framework card improve evidence_quality from the 2/5 AAPL baseline?

### Step 3.4 — Human Calibration

- Manually review 5 business_profile outputs
- Score on same 4 dimensions (0-5 each)
- Compare human vs LLM evaluator scores
- If gap >2 points on any dimension: tune evaluator prompt or threshold

### Step 3.5 — Update `AGENT-ITERATION-PLAN-V1.md`

Revise with findings:
- What worked, what didn't
- Actual cost per company vs projected
- Which sprints need Sonnet upgrade (<80% pass rate)
- Revised thresholds from human calibration
- Go/no-go for Phase 1B (25-company pilot)

### Increment 3 Deliverables

| File | Type | Purpose |
|------|------|---------|
| `pilot_runner.py` | New | Batch runner with CSV output + taint reporting |
| `AGENT-ITERATION-PLAN-V1.md` | Modified | Updated with real pilot findings |
| 5× state directories | Generated | Full pilot results (gitignored) |
| `pilot_metrics.csv` | Generated | Aggregated metrics including taint column |

---

## Build Order (Increment 1 implementation sequence)

| Step | What | Depends On | Risk |
|------|------|------------|------|
| 1.1 | Framework card | Source docs read | Low — distillation |
| 1.2 | DataFetcher | API knowledge | Low — thin HTTP wrapper |
| 1.3 | Data validator | DataFetcher response schema | Low — deterministic checks |
| 1.4 | Sanitizer (T1 + T2 + taint) | None | Medium — DeBERTa optional dep |
| 1.5 | Fix prompt caching + XML wrap | LLM client | Medium — protocol change |
| 1.6 | Wire orchestrator (gates + resume) | 1.2, 1.3, 1.4 | Medium — integration point |
| 1.7 | Prompt logging + debug mode | 1.6 | Low — file writes |
| 1.8 | Tests | All above | Medium — httpx mocks, DeBERTa absent mock |

Parallel opportunities: 1.1 and 1.4 are fully independent. 1.2 and 1.3 are sequential. 1.5 is independent.
1.6 integrates everything.

---

## What This Plan Does NOT Include (Deferred)

- **Cost estimator before run** (Gap E) — add after pipeline works end-to-end
- **Data caching / snapshot mode** — deferred; always fetch fresh
- **Tavily web search integration** — deferred to Phase 1B
- **T3 Haiku classifier by default** — optional, env-var gated (`ENABLE_T3_CLASSIFIER=1`)
- **DeBERTa fine-tuning on SEC corpus** — deferred; monitor false positive rate in pilot first
- **Real-time complexity classifier for model routing** — not needed; sprint complexity is captured in
  contract `model_tier`; failure-driven escalation handles the dynamic case
- **Evaluator model escalation** — evaluator always Haiku; shorter structured prompt doesn't benefit
- **Permanent contract model upgrades** — decided post-Increment 3 pilot based on actual failure rates
- **Multi-tenancy (user_id namespacing)** — deferred to Phase 2
- **Celery task wrapper** — deferred to Phase 2
- **UI integration** — deferred to Phase 3

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Docker not running during live test | High | Blocks live mode | Hardcoded snapshot remains as default; live is opt-in |
| SEC whitelist misses financial phrases → false positives | Medium | Sprint aborts on legit data | Whitelist expandable; suspicious mode logs without blocking |
| DeBERTa 8.4% FP rate on financial text | High | Tainted sprints on legit data | Threshold 0.80 for suspicious (not blocked); T3 Haiku review for ambiguous; monitor in pilot |
| Item 1 extraction returns garbage for some companies | Medium | Low-quality builder input | Validator catches short/HTML-contaminated text |
| Framework card too long → dilutes sprint-specific focus | Low | Lower builder quality | Budget 800-1000 tokens; benchmark with/without |
| Prompt caching protocol change breaks mock LLMs | Medium | Test failures | Optional param with default None; existing mocks unaffected |
| JPM/SBUX edge cases (banking metrics, negative equity) | High | Sprint failures | Data validator warns; industry_notes guide agent; taint tracking surfaces issues |
| Cascade restart runs too many sprints → unexpected cost | Medium | Budget overrun | cascade respects budget guards; CostTracker resets for resume |
| Sonnet escalation fires on every sprint → cost spike | Low | Budget overrun | Escalation only on final attempt after all Haiku retries exhausted; budget guards still apply |
| Developer forgets Docker is down → confusing failure | High | Wasted time | run_aapl.py prints explicit actionable message with docker compose command and --snapshot escape |
