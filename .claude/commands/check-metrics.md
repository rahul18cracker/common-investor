# Check Metrics

Run a full metrics snapshot for a ticker and triage anomalies with domain context.

## Instructions

1. **Run the metrics snapshot script**:
   ```
   cd backend && python -m scripts.workflows.metrics_snapshot $ARGUMENTS --output /tmp/metrics_snapshot.json
   ```
   If the user includes "ingest" or "fresh", add the `--ingest` flag.

2. **Read the output** from `/tmp/metrics_snapshot.json`

3. **Read memory files for context**:
   - `.claude/memory/known_patterns.md` — expected anomalies (e.g., SBUX negative equity is real)
   - `.claude/memory/industry_expectations.md` — what's normal for this company's industry

4. **Triage anomalies**:
   - For each anomaly flagged by the script, check if memory explains it as expected
   - Flag anything truly unexpected with a suggested investigation path
   - Check if metric values are plausible for the industry (e.g., banks shouldn't have high ROIC, utilities have low growth)

5. **Report**:
   - Key metrics summary (growth, ROIC, valuation, Four Ms scores)
   - Anomalies classified as expected vs needs-investigation
   - If valuation failed, explain why and whether it's a data gap or domain limitation

6. **Update memory** if you discover a new pattern worth remembering.

## Arguments
- `$ARGUMENTS` — required: ticker symbol (e.g., MSFT). Optionally append "fresh" to ingest first.
