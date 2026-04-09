# Lint Check

Run all code quality checks and report status.

## Instructions

1. **Run checks**:
   ```
   cd backend
   black --check app/ tests/ 2>&1 | tail -5
   isort --check-only app/ tests/ 2>&1 | tail -5
   flake8 app/ tests/ 2>&1 | tail -20
   mypy app/ --config-file pyproject.toml 2>&1 | tail -20
   ```

2. **Report**:
   - Which checks pass/fail
   - Count of violations per tool
   - Suggested fix for most common violation type

3. **Auto-fix option**: If the user says "fix", run:
   ```
   black app/ tests/
   isort app/ tests/
   ```
   Then re-run flake8 and mypy to report remaining issues.

## Arguments
- `$ARGUMENTS` — optional: "fix" to auto-format, or specific path to check
