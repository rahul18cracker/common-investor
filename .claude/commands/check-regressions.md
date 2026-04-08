# Check Regressions

Compare current DB state against saved baseline to detect data regressions.

## Instructions

1. **Run the regression check script**:
   ```
   cd backend && python -m scripts.workflows.regression_check --output /tmp/regression_check.json
   ```
   If the user says "save baseline" or "new baseline", run with `--save-baseline` instead.

2. **Read the output** from `/tmp/regression_check.json`

3. **Read memory files for context**:
   - `.claude/memory/tag_regressions.md` — past regression incidents and resolutions
   - `.claude/memory/known_patterns.md` — expected NULLs that aren't regressions

4. **Classify each anomaly**:
   - **True regression** — a field that was populated is now NULL. This is a bug.
   - **Expected change** — value changed because we improved the tag list or enrichment logic.
   - **New fill** — field was NULL and is now populated. This is a win — note it.
   - **Value drift** — >10% change. Check if it's a re-ingestion with updated SEC data vs a parsing change.

5. **Report**:
   - Count of regressions (bad), new fills (good), value changes (investigate)
   - For each true regression: which ticker, field, and what the baseline value was
   - Suggested fix if the regression matches a known pattern from memory

6. **Update `.claude/memory/tag_regressions.md`** if new regression patterns are found.

## Arguments
- `$ARGUMENTS` — optional: "save baseline", or comma-separated tickers
