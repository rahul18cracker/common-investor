# Test Audit

Audit test marker coverage and report gaps.

## Instructions

1. **Collect marker stats**:
   ```
   cd backend
   pytest --collect-only -q -m "unit" 2>&1 | tail -3
   pytest --collect-only -q -m "integration" 2>&1 | tail -3
   pytest --collect-only -q -m "e2e" 2>&1 | tail -3
   pytest --collect-only -q 2>&1 | tail -3
   ```

2. **Calculate unmarked**: Total - (unit + integration + e2e)

3. **If unmarked > 0**: Find which files have unmarked tests:
   ```
   for f in tests/test_*.py; do
     grep -L "pytestmark\|pytest.mark.unit\|pytest.mark.integration\|pytest.mark.e2e" "$f"
   done
   ```

4. **Report**: Marker distribution table + list of files needing markers

## Arguments
- `$ARGUMENTS` — optional: specific test file to audit
