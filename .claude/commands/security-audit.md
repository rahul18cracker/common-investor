Run a comprehensive local security audit of the codebase. Execute each check and report findings.

## Steps

1. **Python dependency audit** — Run `cd backend && pip-audit --strict --desc` and report any CVEs found.

2. **Python security lint** — Run `cd backend && bandit -c pyproject.toml -r app/ -f json` and summarize findings by severity.

3. **npm dependency audit** — Run `cd ui && npm audit --audit-level=high` and report any high/critical CVEs.

4. **Secret scan** — Run `gitleaks detect --source . --verbose` and report any findings.

5. **Docker image check** — Verify all Dockerfiles and docker-compose.yml use pinned image tags (no `:latest`, no bare major versions).

6. **CORS/Headers review** — Check `backend/app/main.py` CORS config and `ui/next.config.js` security headers are correctly configured.

7. **Dependency freshness** — Compare `requirements.lock` timestamps against `requirements.txt` to see if lock files are stale.

## Report Format

For each check, report:
- **Status**: PASS / WARN / FAIL
- **Details**: What was found (if anything)
- **Action**: What to do about it (if anything)

Prioritize findings by severity: CRITICAL > HIGH > MEDIUM > LOW.
