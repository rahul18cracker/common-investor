# Tech Debt: Parallelization of Qualitative Agent Harness Sprint Execution

**Status**: Design complete, implementation deferred  
**Author**: Engineering team  
**Date**: 2026-05-06  
**Phase**: Post-Phase 1B (future work, not in Phase 1B pilot)

---

## Summary

The qualitative agent harness currently executes 8 sequential sprints per company, each running an LLM API call and evaluation loop. By restructuring sprints into waves based on dependency analysis, we can parallelize up to 3 concurrent sprints, reducing per-company wall-clock time from ~10–15 minutes to ~5–8 minutes (50–55% improvement). This document captures the complete design for future implementation after baseline quality data is established.

---

## Motivation

**Current pain points:**
- A 25-company pilot run takes 4–6 hours wall-clock time due to sequential execution.
- Most sprints are I/O-bound (network calls to Anthropic API), making thread-level parallelism viable.
- The dependency graph is richer than the current sequential logic exploits—multiple sprints in later waves have no dependencies on each other.
- Observability becomes easier with structured logging, but concurrent execution will require careful state management to preserve correctness.

**Business impact:**
- Faster iteration cycle for the qualitative agent development roadmap.
- Reduced pilot validation time, enabling faster feedback loops to refine agent contracts.
- Foundation for eventual scaling: if we move to a 100-company dataset or higher-frequency re-runs, wall-clock latency becomes a bottleneck.

---

## Current State

### Sequential Orchestrator

The `run_all_sprints()` function in `orchestrator.py` executes sprints in order:

```
for sprint_name in sprints_to_run:  # ["01_business_profile", "02_unit_economics", ...]
    run_sprint(sprint_name, ...)    # Blocks until complete
```

Each `run_sprint()` call encapsulates:
1. **Build**: LLM generates structured JSON output (1–3 min, includes retries)
2. **Evaluate**: LLM checks output quality (10–30 sec)
3. **Retry loop**: Up to 2 retries if evaluation fails (best case: 1 attempt, worst case: 3 attempts)

Output for each sprint is written to disk, and subsequent sprints read prior outputs via `read_prior_outputs()` to provide LLM context.

### Pre-existing Dependency Graph Inconsistency

**Critical bug**: `SPRINT_DEPENDENCIES` is defined in **both** files with **different graphs**:

#### orchestrator.py (lines 41–50)

```python
SPRINT_DEPENDENCIES: dict[str, list[str]] = {
    "01_business_profile": [],
    "02_unit_economics": ["01_business_profile"],
    "03_industry": ["01_business_profile"],
    "04_moat": ["01_business_profile", "02_unit_economics"],  # Missing 03_industry
    "05_management": ["01_business_profile"],
    "06_peers": ["03_industry"],
    "07_risks": ["04_moat", "05_management"],  # Missing other deps
    "08_thesis": ["04_moat", "05_management", "06_peers", "07_risks"],  # Missing 01-03
}
```

#### state_manager.py (lines 188–212)

```python
SPRINT_DEPENDENCIES: dict[str, list[str]] = {
    "01_business_profile": [],
    "02_unit_economics": ["01_business_profile"],
    "03_industry": ["01_business_profile"],
    "04_moat": ["01_business_profile", "02_unit_economics", "03_industry"],  # Authoritative
    "05_management": ["01_business_profile"],
    "06_peers": ["03_industry"],
    "07_risks": [
        "01_business_profile",  # Authoritative: all prior deps
        "02_unit_economics",
        "03_industry",
        "04_moat",
        "05_management",
        "06_peers",
    ],
    "08_thesis": [
        "01_business_profile",  # Authoritative: all 7 prior sprints
        "02_unit_economics",
        "03_industry",
        "04_moat",
        "05_management",
        "06_peers",
        "07_risks",
    ],
}
```

**Why the discrepancy?**
- `orchestrator.py`: Used only for restart validation in `resume_from_sprint()` (lines 356–360). A narrower graph was initially thought to be sufficient for restarts.
- `state_manager.py`: Used by `read_prior_outputs()` (lines 159–172) to determine what prior builder outputs a sprint sees. **This is the authoritative graph** because it directly controls what context the LLM receives, thus determining output quality.

**Impact**: Currently, the narrower orchestrator graph is only used for restart validation and does not affect sequential execution. However, with parallelization, the narrower graph would incorrectly allow downstream sprints to start before all their true dependencies finish, resulting in silent data loss (missing prior outputs for the LLM context).

---

## Proposed Wave Structure

Derived from the authoritative `state_manager.py` dependency graph, we restructure sprints into 5 waves. All sprints within a wave can run in parallel; a wave cannot start until the previous wave is fully complete.

| Wave | Sprints | Max Parallelism | Rationale |
|------|---------|-----------------|-----------|
| 1 | `01_business_profile` | 1 | No dependencies; must complete before any other sprint |
| 2 | `02_unit_economics`, `03_industry`, `05_management` | 3 | All depend only on 01; no cross-dependencies |
| 3 | `04_moat`, `06_peers` | 2 | 04 needs 01+02+03 (all complete after wave 2); 06 needs 03 (complete after wave 2) |
| 4 | `07_risks` | 1 | Needs all of waves 1–3 (01–06 complete) |
| 5 | `08_thesis` | 1 | Needs all of waves 1–4 (01–07 complete) |

**Max practical parallelism**: 3 concurrent sprints (wave 2), not 6 as initially estimated.

### Timing Estimate

Assuming:
- Wave 1: ~3 min (01_business_profile, no retries expected)
- Wave 2: ~4 min (max(02, 03, 05) ≈ 3–4 min each, run in parallel)
- Wave 3: ~3 min (max(04, 06) ≈ 2–3 min each; 04 typically longer)
- Wave 4: ~3 min (07_risks is usually quick)
- Wave 5: ~2 min (08_thesis is short)

**Parallel total**: ~15 min (waves run sequentially, but within-wave sprints overlap).  
**Current sequential**: ~25 min (all sprints run back-to-back).  
**Wall-clock improvement**: ~40% reduction; 25-company pilot goes from ~10 hours to ~6 hours.

---

## Pre-conditions (MUST be completed before implementation)

### Pre-condition 1: Consolidate SPRINT_DEPENDENCIES

**Scope**: Single source of truth for the dependency graph.

**Action**:
1. In `state_manager.py`, the current graph (lines 188–212) is already authoritative and correct.
2. In `orchestrator.py`, replace the narrow SPRINT_DEPENDENCIES (lines 41–50) with:

```python
from app.nlp.research_agent.harness.state_manager import SPRINT_DEPENDENCIES
```

This ensures all restart validation and wave-gating logic uses the same graph.

**Verification**: Run the test suite; no behavioral change (orchestrator.py only used it for restarts, and the narrower graph was still "correct" for restarts in sequential mode—but for correctness with parallelization, must use the broader graph).

**Code snippet** (orchestrator.py, lines 40–50):

```python
# OLD: local SPRINT_DEPENDENCIES definition
# NEW: import from state_manager
from app.nlp.research_agent.harness.state_manager import SPRINT_DEPENDENCIES
```

Then remove the old definition.

### Pre-condition 2: Thread-safe manifest writes

**Scope**: `StateManager.update_sprint_in_manifest()` uses read→modify→write without locks.

**Current code** (state_manager.py, lines 75–81):

```python
def update_sprint_in_manifest(self, sprint_name: str, sprint_data: dict[str, Any]) -> dict[str, Any]:
    """Set or update a single sprint entry in the manifest."""
    manifest = self.read_manifest()               # (1) Read
    manifest["sprints"][sprint_name] = sprint_data # (2) Modify
    manifest["total_cost_usd"] = sum(...)         # (3) Recalculate
    self.write_json(self.root / "manifest.json", manifest)  # (4) Write
```

**Race condition**: If two threads call this simultaneously (e.g., sprints 02 and 03 complete at the same time in wave 2):
- Thread A reads manifest (has neither 02 nor 03 entries)
- Thread B reads manifest (same state)
- Thread A updates 02 and writes
- Thread B updates 03 and writes (overwrites A's 02 entry, last-write-wins)

**Fix**: Add a threading.Lock per StateManager instance.

**Implementation**:

```python
import threading

class StateManager:
    def __init__(self, ticker: str, state_root: Path | None = None):
        self.ticker = ticker.upper()
        self.root = (state_root or DEFAULT_STATE_ROOT) / self.ticker
        self._manifest_lock = threading.Lock()

    def update_sprint_in_manifest(self, sprint_name: str, sprint_data: dict[str, Any]) -> dict[str, Any]:
        """Set or update a single sprint entry in the manifest (thread-safe)."""
        with self._manifest_lock:
            manifest = self.read_manifest()
            manifest["sprints"][sprint_name] = sprint_data
            manifest["total_cost_usd"] = sum(s.get("cost_usd", 0.0) for s in manifest["sprints"].values())
            self.write_json(self.root / "manifest.json", manifest)
            return manifest
```

**Verification**: Unit test with thread pool calling `update_sprint_in_manifest()` on the same StateManager instance; all entries must be preserved (manifest["sprints"] size = number of calls after all threads complete).

### Pre-condition 3: CostTracker atomicity audit

**Scope**: `CostTracker.record_builder_usage()` and `record_eval_usage()` must be thread-safe.

**Current code** (cost_tracker.py, lines 121–156):

```python
def record_builder_usage(
    self,
    sprint_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> None:
    sprint = self.get_or_create_sprint(sprint_name)  # (A) Get or create
    sprint.builder_usages.append(                     # (B) Append
        LLMUsage(...)
    )
```

**Analysis**:
- `get_or_create_sprint()` modifies `self._sprints` dict if the sprint is missing. If two threads call this simultaneously for different sprints (02 and 03), the dict will be resized—Python's GIL protects this from corruption.
- `.append()` on a list is atomic (GIL protects).
- `total_cost` is computed fresh on each call (property, not cached), so no stale totals.

**Verdict**: The GIL provides sufficient protection for CostTracker as-is. No lock needed. Verify this in tests by spawning threads and recording costs simultaneously; final `.to_dict()` must be consistent.

**Test**: Add `test_cost_tracker_concurrent_writes()` in `test_cost_tracker.py`:

```python
from concurrent.futures import ThreadPoolExecutor

def test_cost_tracker_concurrent_writes():
    tracker = CostTracker()
    def record_usage(sprint_idx):
        tracker.record_builder_usage(f"sprint_{sprint_idx}", "haiku", 1000, 200, 0)
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(record_usage, range(5))
    
    # Verify all 5 sprints exist and have exactly 1 usage each
    assert len(tracker._sprints) == 5
    for sprint in tracker._sprints.values():
        assert len(sprint.builder_usages) == 1
```

### Pre-condition 4: Wave gate on `passed` status only

**Scope**: Configurable behavior for degraded dependencies.

**Problem**: With sequential execution, a sprint in `degraded` status still has a builder output on disk (it just failed evaluation). The next sequential sprint reads this degraded output as context, and the caller accepts this (no explicit warning). With waves, if sprint 04 (04_moat) depends on 02 (unit_economics) and 02 is degraded, should 04 start or wait?

**Options**:

| Option | Behavior | Pros | Cons |
|--------|----------|------|------|
| A. Block | Wave N+1 doesn't start if any wave N dep is degraded | Conservative; easy to reason about | Pilot may be slow if early sprints degrade frequently |
| B. Proceed with flag | Wave N+1 starts; manifest notes degraded deps used | Faster; matches current behavior | Risk of quality cascade; harder to debug |
| C. Configurable | Add `allow_degraded_deps` boolean to orchestrator params | Flexible; lets pilot choose | More code; coordination burden |

**Recommendation for Phase 1B pilot**: **Option C (configurable)**, defaulting to **Option B (proceed with flag)** to match current behavior, with the flag exposed as a runtime parameter:

```python
def run_all_sprints(
    ticker: str,
    ...,
    allow_degraded_deps: bool = True,  # Phase 1B default: proceed
) -> dict[str, Any]:
```

If `allow_degraded_deps=False`, `run_wave()` checks:

```python
def _wave_gate_check(state: StateManager, sprints: list[str], allow_degraded: bool) -> None:
    """Raise ValueError if any sprint's dependencies are not 'passed' and allow_degraded=False."""
    manifest = state.read_manifest()
    for sprint in sprints:
        deps = SPRINT_DEPENDENCIES.get(sprint, [])
        for dep in deps:
            dep_status = manifest.get("sprints", {}).get(dep, {}).get("status")
            if dep_status != "passed" and not allow_degraded:
                raise ValueError(
                    f"Sprint {sprint} depends on {dep} which is {dep_status}. "
                    f"Set allow_degraded_deps=True to proceed."
                )
```

Record which dependencies were degraded in the manifest for traceability:

```python
sprint_data = {
    "status": "passed",
    ...,
    "degraded_deps_used": [dep for dep in deps if manifest["sprints"][dep]["status"] == "degraded"]
}
```

**Verification**: Tests for both modes (allow=True and allow=False); test restartability from degraded state.

### Pre-condition 5: Exception propagation from thread pools

**Scope**: ThreadPoolExecutor must propagate exceptions cleanly.

**Problem**: `executor.map()` returns an iterator that lazily evaluates results. If a thread raises an exception, it's not seen until `.result()` is called. Using `as_completed()` with explicit `.result()` calls ensures we catch and handle exceptions properly.

**Implementation** (preview, detailed in Implementation Plan section):

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_wave(wave_sprints: list[str], ...):
    """Run all sprints in a wave in parallel."""
    futures = {}
    with ThreadPoolExecutor(max_workers=len(wave_sprints)) as executor:
        for sprint in wave_sprints:
            future = executor.submit(run_sprint, sprint_name=sprint, ...)
            futures[future] = sprint

    # Collect results and exceptions
    results = {}
    exceptions = []
    for future in as_completed(futures):
        sprint_name = futures[future]
        try:
            result = future.result()
            results[sprint_name] = result
        except Exception as exc:
            exceptions.append((sprint_name, exc))
            logger.exception("Sprint %s failed with exception: %s", sprint_name, exc)

    if exceptions:
        raise RuntimeError(
            f"Wave execution failed for sprints: {[e[0] for e in exceptions]}. "
            f"Details: {exceptions}"
        )

    return results
```

**Verification**: Unit test that intentionally raises an exception in a thread and verifies it propagates to the caller.

---

## Implementation Plan

### Phase 1: Skeleton and Wave Executor

**File**: `orchestrator.py`, lines ~212–337 (replace `run_all_sprints()`)

**Changes**:

1. **Import ThreadPoolExecutor and as_completed**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

2. **Add wave definitions** (after pre-condition 1, use state_manager's SPRINT_DEPENDENCIES):
```python
def _build_wave_structure() -> dict[str, list[str]]:
    """Map sprints to waves based on dependency graph."""
    # Derive waves from SPRINT_DEPENDENCIES (state_manager)
    # Return { 1: [...], 2: [...], 3: [...], 4: [...], 5: [...] }
    ...
```

3. **Add run_wave() function**:
```python
def run_wave(
    wave_num: int,
    wave_sprints: list[str],
    state: StateManager,
    cost_tracker: CostTracker,
    builder_llm: Callable,
    evaluator_llm: Callable,
    skip_retries: bool,
    allow_degraded_deps: bool,
) -> dict[str, dict[str, Any]]:
    """Execute a wave of sprints in parallel using ThreadPoolExecutor."""
    # Check wave gate (pre-condition 4)
    if not allow_degraded_deps:
        _wave_gate_check(state, wave_sprints, allow_degraded_deps)
    
    futures = {}
    with ThreadPoolExecutor(max_workers=len(wave_sprints)) as executor:
        for sprint in wave_sprints:
            future = executor.submit(
                run_sprint,
                sprint_name=sprint,
                state=state,
                cost_tracker=cost_tracker,
                builder_llm=builder_llm,
                evaluator_llm=evaluator_llm,
                skip_retries=skip_retries,
            )
            futures[future] = sprint
    
    # Collect results
    results = {}
    exceptions = []
    for future in as_completed(futures):
        sprint_name = futures[future]
        try:
            result = future.result()
            results[sprint_name] = result
        except Exception as exc:
            exceptions.append((sprint_name, exc))
            logger.exception("Sprint %s failed in wave %d", sprint_name, wave_num)
    
    if exceptions:
        raise RuntimeError(
            f"Wave {wave_num} failed for sprints: {[e[0] for e in exceptions]}"
        )
    
    return results
```

4. **Modify run_all_sprints()** to call `run_wave()` for each wave instead of the inner `for sprint_name in sprints_to_run` loop.

### Phase 2: StateManager locks (pre-condition 2)

**File**: `state_manager.py`, lines ~34–81

**Changes**:

1. Add `import threading` at top.
2. In `__init__()`, add `self._manifest_lock = threading.Lock()`.
3. Wrap `update_sprint_in_manifest()` and `update_manifest()` with the lock (both modify manifest.json).

**Verification**: Run existing tests; all should pass (lock doesn't change behavior, only adds safety).

### Phase 3: Observability enhancements (optional for Phase 1B, recommended)

**Scope**: Logging becomes harder to read when sprints interleave. Add structured logging support.

**Options**:
- **Option A (minimal)**: Each log line includes `sprint_name`, already done in current code. Log readers can grep/filter by sprint.
- **Option B (recommended)**: Add a structured log format (JSON lines) for programmatic parsing.

For Phase 1B, **Option A is sufficient**. Existing log statements like `logger.info("Sprint %s ...", sprint_name)` are already sprint-aware.

---

## Threading vs Async Analysis

### Why Threading (not Async)

| Aspect | Threading | Async |
|--------|-----------|-------|
| **GIL behavior** | Releases during I/O; genuine parallelism | Still releases during I/O, but more overhead |
| **Code changes required** | Minimal: only orchestrator.py run_all_sprints() | Massive: run_sprint, build, evaluate, llm_client all become async def |
| **Exception model** | `future.result()` re-raises in calling thread; clear | `asyncio.gather(return_exceptions=True)` less intuitive |
| **Max concurrency** | 3 threads (wave 2); no scaling cliff | Same max concurrency; marginal benefit |
| **Dependency integration** | All existing deps (anthropic, etc.) are sync | Would need httpx async wrapper |

**Decision**: **Use threading**. Scope is limited (~50 lines of new code), benefits are clear, and the codebase is fully synchronous.

### False economies of async

- "Async is always faster": Only if you have 50+ concurrent tasks. At 3 tasks max, thread overhead is negligible, and thread setup is 10x simpler.
- "Async exception handling is better": No—`future.result()` is more explicit than `gather(return_exceptions=True)`.
- "Async scales to 1000 tasks": Out of scope; Phase 1B pilot is 25 companies * 8 sprints = 200 tasks total, mostly sequential (waves).

---

## Observability & Reliability Impact

### Restartability

**Current behavior** (sequential): `resume_from_sprint(sprint_name, cascade=False)` re-runs a single sprint; all dependencies are already passed (checked on entry). Sequential execution guarantees output is read correctly.

**New behavior** (parallel): Same logic applies. The difference:
- A wave cannot start until the previous wave is complete (hard gate in orchestrator).
- Within a wave, concurrent sprints may finish in any order, but each sprint writes its results independently to `sprints/{sprint_name}/` directories.
- The manifest update is now protected by a lock (pre-condition 2).

**Restartability impact**: No change in functionality. The state_manager lock ensures the manifest is always consistent. Restarting from mid-wave respects dependency gates.

**Test**: Add `test_resume_from_wave2_sprint()` that runs waves 1–2, fails wave 2 sprint 03, resumes from 03. Verify 02 is not re-run, and final manifest is correct.

### Log readability

**Current** (sequential):
```
2026-05-06 10:00:00 - Sprint 01_business_profile: build starting
2026-05-06 10:00:05 - Sprint 01_business_profile: evaluate pass
2026-05-06 10:00:05 - Sprint 02_unit_economics: build starting
...
```

**With parallelism** (wave 2: 02, 03, 05 concurrent):
```
2026-05-06 10:00:00 - Sprint 01_business_profile: build starting
2026-05-06 10:00:05 - Sprint 01_business_profile: evaluate pass
2026-05-06 10:00:05 - Sprint 02_unit_economics: build starting
2026-05-06 10:00:05 - Sprint 03_industry: build starting
2026-05-06 10:00:05 - Sprint 05_management: build starting
2026-05-06 10:00:08 - Sprint 03_industry: evaluate pass
2026-05-06 10:00:09 - Sprint 05_management: evaluate pass
2026-05-06 10:00:10 - Sprint 02_unit_economics: evaluate fail, retry
...
```

**Readability**: Still parseable. Grep by sprint name to follow a single sprint's timeline. No change to log line format needed.

**Structured logs** (JSON): Optional enhancement post-Phase 1B:
```json
{"timestamp": "2026-05-06T10:00:08.123Z", "sprint": "03_industry", "event": "evaluate", "status": "pass"}
```

### Retry loop integrity

**Current** (sequential): `run_sprint()` has an inner loop:
```python
for attempt in range(1, max_attempts + 1):
    ...
    eval_result = evaluate(...)
    if eval_result["pass"]:
        state.update_sprint_in_manifest(sprint_name, {"status": "passed"})
        return sprint_data
```

**Impact**: Retry logic is entirely local to a single `run_sprint()` call. Parallel execution of *different* sprints does not interfere with retry state. Each thread has its own `eval_failures` list, `last_eval_result`, etc.

**No changes needed**: Retry loop is unaffected.

### Error propagation and wave gating

**Current** (sequential): If sprint 03 fails to build (e.g., API error), it's marked `degraded`. Sprint 04 still starts and reads the degraded output of 03 if it exists. The caller sees the full run with mixed passed/degraded status.

**New** (parallel waves): If sprint 02 fails in wave 2 before sprint 04's wave 3 starts:
- Manifest shows `02: {status: "degraded"}`.
- Wave gate (pre-condition 4) checks this. If `allow_degraded_deps=True` (default for pilot), wave 3 proceeds.
- Otherwise, raises an error.

**Implementation detail**: The wave gate runs *before* submitting sprint tasks to ThreadPoolExecutor. Once a wave starts, all sprints in the wave run to completion (no mid-wave cancellation).

### Data consistency

**Concern**: If thread A is reading the manifest while thread B is writing it, does A get partial data?

**Current code** (no lock): Yes, possible. `read_manifest()` reads the entire file into memory before parsing JSON. On modern filesystems, this is usually atomic at the file level, but JSON parsing of a partially-written file fails.

**With lock** (pre-condition 2): `read_manifest()` outside the lock, `write_manifest()` inside the lock. So:
- Reader sees consistent snapshots (either old or new manifest, never partial).
- Writers are serialized (no concurrent writes).

**Caveat**: Long readers don't block writers. If `read_manifest()` takes 100ms, a writer will wait until the reader completes and the old manifest is fully read. This is fine for our use case (manifest is <1KB).

---

## Expected Gains

### Timing Analysis

**Assumptions**:
- Each sprint: 2–4 min build + 0.5 min evaluate (including retries).
- API latency is the dominant cost, not CPU.
- Network delays are independent (parallel I/O is real win).

| Scenario | Sequential | Parallel (waves) | Speedup |
|----------|-----------|------------------|---------|
| Baseline (all pass on 1st try) | ~25 min | ~10 min | 2.5x |
| 1 retry in wave 2 sprint | ~27 min | ~12 min | 2.25x |
| 1 retry in wave 4 sprint | ~28 min | ~10 min | 2.8x (waves 1–3 hidden) |

**Realistic pilot scenario** (25-company run):
- Sequential: 25 * 12 min = 300 min = 5 hours (using conservative 12 min/company average).
- Parallel: 25 * 5 min = 125 min = 2 hours.
- **Gain**: 3 hours wall-clock saved, 60% reduction.

### Cost impact

No cost change. API call counts are identical (same 8 sprints per company). Threading does not increase calls. Parallelism is purely a scheduling optimization.

### Pilot validation timeline

- **Phase 1B pilot (current, sequential)**: ~5–6 hours to run 25 companies.
- **Phase 1B+parallelization**: ~2–3 hours, enabling faster feedback on agent contract refinements.

---

## Acceptance Criteria

### Functional Requirements

1. **Wave gating**: No sprint in wave N starts before all sprints in wave N-1 are complete.
   - Test: Run 25-company pilot, inspect logs for timestamp ordering. Wave 2 sprints start after wave 1 completes.

2. **Concurrency within wave**: All sprints in a wave start within 1 second of each other (no artificial sequencing).
   - Test: Parse logs, verify 02, 03, 05 have start timestamps within 1s in wave 2.

3. **Manifest correctness**: After 25-company run, manifest for each company has all 8 sprints (or skipped/degraded if applicable). No missing entries.
   - Test: `for c in COMPANIES: assert len(manifest[c]["sprints"]) == 8`.

4. **Exception safety**: If one sprint throws an exception mid-wave, the wave fails (not just that sprint).
   - Test: Mock llm_client to raise ValueError in sprint 03. Verify entire wave 2 fails, wave 3 does not start.

5. **Restartability**: `resume_from_sprint("04_moat", cascade=False)` works after wave 2 completion.
   - Test: Run waves 1–2, then resume 04_moat. Verify 04 is re-run, 02/03/05 are not touched.

### Non-functional Requirements

1. **Cost parity**: Total API cost for 25-company run is identical in parallel vs. sequential.
   - Verify in cost_tracker totals.

2. **Log integrity**: All log lines include sprint name; interleaved logs are still parseable.
   - Test: Run pilot, grep logs by sprint, verify complete timeline for each sprint.

3. **Performance**: 25-company run completes in <3 hours wall-clock.
   - Benchmark pilot execution time.

4. **Thread safety**: No data corruption when running 100+ parallel operations (stress test).
   - Test: Spawn 20 threads, each updating manifest independently for different sprints. Verify all 20 entries exist after completion.

### Regression Prevention

1. **Existing tests pass**: All unit and integration tests pass with parallelization code in place (even though tests themselves are sequential).
2. **State idempotency**: Running the same company twice (parallel then sequential) produces identical output manifests.
3. **Sequential compatibility**: Setting `max_workers=1` in ThreadPoolExecutor should produce identical behavior to original sequential code.
   - Add test: `test_parallelization_with_single_worker_matches_sequential()`.

---

## Scope Boundaries

### In Scope

- Wave structure design and dependency analysis
- ThreadPoolExecutor integration in `run_all_sprints()`
- StateManager manifest lock (threading.Lock)
- Exception propagation and wave gating logic
- Acceptance tests for concurrency and restartability
- Log parsing validation

### Out of Scope (Post-Phase 1B)

- Async/await refactoring (rejected as unnecessary at current scale)
- Structured logging (JSON lines) — defer to Phase 2 observability work
- Dynamic wave calculation from runtime DAG (waves are hardcoded; sufficient for Phase 1B)
- Distributed execution (K8s/Celery tasks) — Phase 2+ infrastructure work
- Sprint-level timeout/cancellation (if one sprint hangs, current wave hangs; Phase 2 timeout infrastructure)
- Per-sprint resource limits (CPU, memory) — Phase 2+ resource management

---

## Implementation Timeline

| Milestone | Duration | Description |
|-----------|----------|-------------|
| Pre-condition 1 (consolidate deps) | 15 min | Import SPRINT_DEPENDENCIES from state_manager; remove orchestrator copy |
| Pre-condition 2 (manifest lock) | 30 min | Add threading.Lock to StateManager; update test_state_manager.py |
| Pre-condition 3 (CostTracker audit) | 15 min | Verify GIL sufficiency; add concurrent write test |
| Pre-condition 4 (wave gate) | 45 min | Implement _wave_gate_check(); add allow_degraded_deps parameter |
| Pre-condition 5 (exception handling) | 20 min | Add as_completed() pattern; test exception propagation |
| Core implementation (run_wave) | 1 hour | ThreadPoolExecutor skeleton; integrate into run_all_sprints() |
| Testing (acceptance criteria) | 2 hours | 25-company pilot; thread safety tests; restartability tests; stress tests |
| Documentation | 30 min | Add parallel execution notes to CLAUDE.md; update orchestrator docstrings |
| **Total** | **~5.5 hours** | Ready for merging and Phase 1B pilot (parallel edition) |

---

## Not in Scope for Phase 1B Pilot

**This feature is deferred.** The Phase 1B pilot (currently underway) uses sequential execution to establish baseline quality metrics and refine agent contracts. Once the qualitative agent is stabilized (expected end of Phase 1B), parallelization will be implemented to accelerate future iterations.

**Rationale**:
1. **Debugging complexity**: Parallel execution introduces thread-ordering variability, making output quality harder to reproduce. Sequential execution provides deterministic behavior.
2. **Quality stability**: Before optimizing latency, we must establish that outputs are consistent and correct. Parallelization is an optimization, not a feature.
3. **Pilot scope**: Phase 1B pilot is resource-bounded; adding parallelization implementation is out of scope. Use sequential execution for the baseline 25-company run.

**Expected timeline for implementation**: End of Phase 1B (late 2026-05).

---

## Related Documents

- `docs/spec-ideas/qualitative-analysis-v2.md` — Agent playbook and contract design
- `backend/app/nlp/research_agent/harness/orchestrator.py` — Current sequential orchestrator
- `backend/app/nlp/research_agent/harness/state_manager.py` — Manifest and dependency logic
- `CLAUDE.md` — Project architecture and patterns
- `.claude/memory/project_qualitative_harness.md` — Harness development history and design decisions

---

## Appendix: Code Sketch (Full run_wave Implementation)

```python
# orchestrator.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Pre-condition 1: Import consolidated dependency graph
from app.nlp.research_agent.harness.state_manager import SPRINT_DEPENDENCIES, SPRINT_NAMES

def _build_wave_structure() -> dict[int, list[str]]:
    """Derive waves from dependency graph.
    
    Returns: {1: [01], 2: [02, 03, 05], 3: [04, 06], 4: [07], 5: [08]}
    """
    waves = {
        1: ["01_business_profile"],
        2: ["02_unit_economics", "03_industry", "05_management"],
        3: ["04_moat", "06_peers"],
        4: ["07_risks"],
        5: ["08_thesis"],
    }
    return waves

def _wave_gate_check(state: StateManager, wave_sprints: list[str], allow_degraded: bool) -> None:
    """Verify all sprint dependencies are 'passed' (or skip if allow_degraded)."""
    if allow_degraded:
        return  # Proceed regardless of dependency status
    
    manifest = state.read_manifest()
    for sprint in wave_sprints:
        deps = SPRINT_DEPENDENCIES.get(sprint, [])
        for dep in deps:
            dep_status = manifest.get("sprints", {}).get(dep, {}).get("status", "unknown")
            if dep_status != "passed":
                raise ValueError(
                    f"Cannot start sprint {sprint}: dependency {dep} has status '{dep_status}'. "
                    f"Set allow_degraded_deps=True to override."
                )

def run_wave(
    wave_num: int,
    wave_sprints: list[str],
    state: StateManager,
    cost_tracker: CostTracker,
    builder_llm: Callable[[str, str], str],
    evaluator_llm: Callable[[str, str], str],
    skip_retries: bool,
    allow_degraded_deps: bool,
) -> dict[str, dict[str, Any]]:
    """Execute a wave of sprints in parallel using ThreadPoolExecutor.
    
    Args:
        wave_num: Wave identifier (1–5)
        wave_sprints: List of sprint names in this wave (e.g., ["02_unit_economics", ...])
        state: StateManager instance
        cost_tracker: CostTracker instance
        builder_llm: LLM callable for building
        evaluator_llm: LLM callable for evaluation
        skip_retries: Skip retries if budget is soft-exceeded
        allow_degraded_deps: If False, raise error if any dependency is degraded
    
    Returns:
        Dict mapping sprint name to result dict
    
    Raises:
        ValueError: If wave gate check fails
        RuntimeError: If any sprint in the wave raises an exception
    """
    logger.info("Wave %d: starting %d sprints: %s", wave_num, len(wave_sprints), wave_sprints)
    
    # Wave gate check (pre-condition 4)
    _wave_gate_check(state, wave_sprints, allow_degraded_deps)
    
    futures = {}
    with ThreadPoolExecutor(max_workers=len(wave_sprints)) as executor:
        for sprint in wave_sprints:
            future = executor.submit(
                run_sprint,
                sprint_name=sprint,
                state=state,
                cost_tracker=cost_tracker,
                builder_llm=builder_llm,
                evaluator_llm=evaluator_llm,
                skip_retries=skip_retries,
            )
            futures[future] = sprint
    
    # Collect results and exceptions
    results = {}
    exceptions = []
    for future in as_completed(futures):
        sprint_name = futures[future]
        try:
            result = future.result()  # Re-raises exception if thread raised
            results[sprint_name] = result
        except Exception as exc:
            exceptions.append((sprint_name, exc))
            logger.exception("Sprint %s failed in wave %d: %s", sprint_name, wave_num, exc)
    
    if exceptions:
        raise RuntimeError(
            f"Wave {wave_num} failed. Sprints with errors: {[e[0] for e in exceptions]}. "
            f"Exceptions: {exceptions}"
        )
    
    logger.info("Wave %d: completed all %d sprints", wave_num, len(wave_sprints))
    return results

def run_all_sprints(
    ticker: str,
    agent_bundle: dict[str, Any] | None = None,
    item1_text: str | None = None,
    builder_llm: Callable[[str, str], str] | None = None,
    evaluator_llm: Callable[[str, str], str] | None = None,
    state_root: Path | None = None,
    sprint_names: list[str] | None = None,
    base_url: str = "http://localhost:8080/api/v1",
    allow_degraded_deps: bool = True,  # Phase 1B pilot default
) -> dict[str, Any]:
    """Run the full pipeline for a ticker using wave-based parallelization.
    
    Sprints are organized into waves; all sprints within a wave run in parallel,
    and waves execute sequentially.
    """
    # ... existing setup code (fetch, validate, sanitize) ...
    
    state = StateManager(ticker, state_root=state_root)
    state.init_run()
    state.write_agent_bundle(sanitized_bundle)
    state.write_item1_text(sanitized_item1)
    
    cost_tracker = CostTracker()
    run_start = time.time()
    
    # Build wave structure
    waves = _build_wave_structure()
    
    for wave_num in sorted(waves.keys()):
        wave_sprints = waves[wave_num]
        
        # Filter to only sprints we're running
        sprints_to_run = sprint_names or SPRINT_NAMES
        wave_sprints = [s for s in wave_sprints if s in sprints_to_run]
        
        if not wave_sprints:
            continue
        
        # Data readiness and contract checks
        for sprint_name in wave_sprints:
            # ... same readiness/contract checks as before ...
            pass
        
        # Budget and timeout checks
        skip_retries = cost_tracker.is_soft_exceeded()
        try:
            cost_tracker.check_budget()
        except BudgetExceeded:
            logger.error("Hard budget exceeded before wave %d, aborting", wave_num)
            _mark_remaining_skipped(state, wave_sprints[0], sprints_to_run)
            return state.complete_run(status="budget_exceeded")
        
        elapsed = time.time() - run_start
        if elapsed > RUN_TIMEOUT_SECONDS:
            logger.error("Run timeout before wave %d (%.0fs)", wave_num, elapsed)
            _mark_remaining_skipped(state, wave_sprints[0], sprints_to_run)
            return state.complete_run(status="timeout")
        
        # Run the wave in parallel
        try:
            run_wave(
                wave_num=wave_num,
                wave_sprints=wave_sprints,
                state=state,
                cost_tracker=cost_tracker,
                builder_llm=builder_llm,
                evaluator_llm=evaluator_llm,
                skip_retries=skip_retries,
                allow_degraded_deps=allow_degraded_deps,
            )
        except RuntimeError as exc:
            logger.error("Wave %d failed: %s", wave_num, exc)
            return state.complete_run(status="wave_failed")
    
    manifest = state.complete_run(status="completed")
    manifest["total_cost_usd"] = cost_tracker.total_cost
    state.update_manifest({"total_cost_usd": cost_tracker.total_cost})
    return state.read_manifest()
```

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-06 | Engineering | Initial design document; deferred to post-Phase 1B |

