# Security Patterns — What to Watch For

## SQL Injection
- All DB access MUST use `execute(sql, **params)` with parameterized queries
- SQLAlchemy `text()` bindings are safe; string formatting/f-strings in SQL are NOT
- bandit B608 is globally skipped because we use parameterized queries — if raw SQL formatting is ever introduced, remove the B608 skip and fix the code

## Secret Management
- NEVER commit `.env` files — `.gitignore` excludes them
- `.env.example` should use placeholder values only (no real credentials)
- API keys (SEC_USER_AGENT, Anthropic, Tavily) come from environment variables
- gitleaks pre-commit hook catches accidental secret commits
- CI credentials (ci/ci_pass) are intentionally non-secret test defaults

## Dependency Security
- Python deps pinned in `requirements.lock` / `requirements-dev.lock`
- After editing `requirements.txt`, regenerate lock files:
  `pip-compile requirements.txt -o requirements.lock --strip-extras`
  `pip-compile requirements-dev.txt -o requirements-dev.lock --strip-extras`
- npm deps: `next` pinned exactly (no caret); devDeps use caret ranges
- Dependabot auto-creates PRs for vulnerable deps

## Docker Security
- All images pinned to specific versions (no `:latest`)
- Containers run as non-root `appuser`
- Multi-stage build for backend (build deps not in production image)
- `.dockerignore` prevents `.env`, `.git`, test files from entering images
- postgres/redis on internal `backend` network only (not exposed to host)

## CORS / Headers
- FastAPI CORS: only `localhost:3000` and `127.0.0.1:3000` allowed
- Methods restricted to GET/POST (what the frontend actually uses)
- Headers restricted to Content-Type/Authorization
- Next.js security headers: X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy

## CI Security
- All GitHub Actions SHA-pinned (not version tags)
- Trivy scans both filesystem and built Docker images
- pip-audit blocks on any known Python CVE
- bandit blocks on security anti-patterns
- npm audit blocks on critical CVEs (high threshold deferred until Next.js 15+)
- SBOM generated per build as CI artifact

## Known Accepted Risks
- Next.js 14.2.35 has DoS-only high CVEs (not RCE) — acceptable for localhost Phase 1
- esbuild/vitest chain has moderate dev-only CVEs — no production impact
- bandit B101 (assert) skipped — assert used in non-production code paths
- research_agent excluded from bandit/mypy — experimental, isolated deps
