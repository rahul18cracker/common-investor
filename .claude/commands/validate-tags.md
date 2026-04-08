# Validate XBRL Tags

Run the coverage matrix workflow and triage anomalies using domain knowledge from memory.

## Instructions

1. **Run the coverage matrix script** against the requested tickers (or full cohort if none specified):
   ```
   cd backend && python -m scripts.workflows.coverage_matrix --skip-ingest --output /tmp/coverage_matrix.json
   ```
   If the user says "with ingest" or "fresh", drop the `--skip-ingest` flag.

2. **Read the output** from `/tmp/coverage_matrix.json`

3. **Read memory files for context** before triaging:
   - `.claude/memory/known_patterns.md` — expected NULLs per industry (e.g., banks don't have inventory)
   - `.claude/memory/tag_regressions.md` — past incidents and what fixed them
   - `.claude/memory/industry_expectations.md` — what fields should/shouldn't be NULL

4. **Triage the NULLs** — for each NULL field, classify as:
   - **Expected** — this industry doesn't use this field (e.g., bank with no inventory). Cite the memory pattern.
   - **Known issue** — we've seen this before and know the fix. Cite the memory entry.
   - **Needs investigation** — unexpected NULL that may indicate a missing XBRL tag or parsing bug.

5. **Report concisely**:
   - Overall coverage % and trend vs last run
   - Table of unexpected NULLs with suggested next steps
   - Skip expected NULLs unless the user asks for full detail

6. **If you discover a new pattern** (e.g., all utilities are missing a field), save it to the appropriate memory file so future runs benefit.

## Arguments
- `$ARGUMENTS` — optional: comma-separated tickers, or "fresh" to re-ingest
