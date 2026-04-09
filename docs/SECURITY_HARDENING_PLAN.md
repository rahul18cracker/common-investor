# Security Hardening Plan

**Date:** 2026-04-09
**Branch:** `rahul/security-hardening`
**Goal:** Establish automated vulnerability detection across dependencies, containers, code, and secrets — integrated into CI and local dev workflow.

---

## Current State

### What exists
- Trivy filesystem scan in CI (non-blocking: `continue-on-error: true`)
- `.gitignore` excludes `.env` files
- Pre-commit hooks for formatting/linting (black, isort, flake8, mypy) — no security hooks
- Parameterized SQL via `execute()` + SQLAlchemy `text()` — safe pattern, no injection risk
- Phase D narrowed bare `except Exception` handlers in alerts/pricefeed

### What's missing
- No dependency vulnerability scanning (Python or Node.js)
- No automated dependency update PRs (Dependabot)
- No Python security linter (bandit)
- No secret scanning (gitleaks or similar)
- Docker images unpinned (`ankane/pgvector:latest`)
- Container image scanning only does filesystem, not built images
- Node.js 18 is past EOL (April 2025)
- Next.js 13.5.6 has known CVEs
- Python packages unpinned (no version specifiers in requirements.txt)

### Stack inventory

**Python production deps (16):** fastapi, uvicorn[standard], pydantic, pydantic-settings, sqlalchemy, psycopg2-binary, alembic, celery, redis, httpx, python-dotenv, loguru, beautifulsoup4, lxml, yfinance, pandas

**Python dev deps (13):** pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-celery, pytest-httpx, faker, freezegun, black, isort, flake8, mypy, pre-commit

**Node.js deps (4 prod + 9 dev):** next@13.5.6, react@18.2.0, react-dom@18.2.0, recharts@^2.12.6, plus testing/build tooling

**Docker images:**
| Service | Image | Tag | Risk |
|---------|-------|-----|------|
| Backend API | python | 3.11-slim | OK — slim variant, Python 3.11 EOL Oct 2027 |
| Frontend | node | 18-alpine | HIGH — Node 18 EOL April 2025 |
| PostgreSQL | ankane/pgvector | latest | CRITICAL — unpinned |
| Redis | redis | 7-alpine | LOW — major version pinned, alpine |

---

## Stage 1: CI Vulnerability Gates (Free, ~1 hour)

**Goal:** Block vulnerable code from merging. Zero cost, all open-source tools.

### 1.1: Add Dependabot configuration

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels: ["dependencies", "security"]
    # Group minor/patch updates to reduce PR noise
    groups:
      python-minor:
        update-types: ["minor", "patch"]

  - package-ecosystem: "npm"
    directory: "/ui"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels: ["dependencies", "security"]
    groups:
      npm-minor:
        update-types: ["minor", "patch"]

  - package-ecosystem: "docker"
    directory: "/backend"
    schedule:
      interval: "weekly"
    labels: ["dependencies", "security"]

  - package-ecosystem: "docker"
    directory: "/ui"
    schedule:
      interval: "weekly"
    labels: ["dependencies", "security"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels: ["dependencies", "security"]
```

**What this does:** GitHub automatically opens PRs when dependencies have known CVEs or new versions. Covers Python, npm, Docker base images, and GitHub Actions versions.

### 1.2: Add pip-audit to CI

Add step to `.github/workflows/ci.yml` in the test job, after pip install:

```yaml
- name: Audit Python dependencies
  run: |
    pip install pip-audit
    pip-audit --strict --desc
```

**What this does:** Checks all installed Python packages against the OSV (Open Source Vulnerabilities) database. `--strict` makes it fail on any known vulnerability. `--desc` shows CVE descriptions.

### 1.3: Add npm audit to CI

Add a new step or job for frontend security:

```yaml
- name: Audit Node.js dependencies
  working-directory: ui
  run: |
    npm ci
    npm audit --audit-level=high
```

**What this does:** Checks all npm packages (including transitive) against the npm advisory database. `--audit-level=high` fails only on high/critical severity (avoids noise from low-severity advisories).

**Note:** `npm audit` may flag issues in dev dependencies. If too noisy initially, use `npm audit --omit=dev --audit-level=high` to scan only production deps.

### 1.4: Make Trivy scan blocking

In `.github/workflows/ci.yml`, the current Trivy step has:

```yaml
continue-on-error: true  # Don't fail CI on vulnerabilities yet
```

Change to:

```yaml
continue-on-error: false
```

Also consider adding `--exit-code 1` explicitly to the Trivy args if not already set. The current config scans CRITICAL and HIGH severity — this is a good threshold.

### 1.5: Pin Docker image tags

**`docker-compose.yml`:**
```yaml
# Before:
postgres:
  image: ankane/pgvector:latest

# After (look up current digest and pin):
postgres:
  image: pgvector/pgvector:pg16
```

Note: `ankane/pgvector` is the legacy image name. The official image is now `pgvector/pgvector`. Pin to a PostgreSQL major version (pg16).

```yaml
# Before:
redis:
  image: redis:7-alpine

# After:
redis:
  image: redis:7.2-alpine
```

**`.github/workflows/ci.yml` services section** — apply the same pins for CI service containers.

**`backend/Dockerfile`:**
```dockerfile
# Before:
FROM python:3.11-slim

# After (pin to specific patch):
FROM python:3.11.9-slim
```

**`ui/Dockerfile`:**
```dockerfile
# Before:
FROM node:18-alpine

# After (use current LTS, pin to specific version):
FROM node:20.18-alpine
```

Note: Node 18 is EOL. Node 20 LTS is supported until April 2026, Node 22 LTS until April 2027. Upgrading to Node 20 is low risk for Next.js 13. Node 22 may require testing.

### Stage 1 — Verification

```bash
# Dependabot: Will auto-create PRs after config is pushed to main
# Check: Settings > Code security > Dependabot should show "Enabled"

# pip-audit: Test locally
cd backend
pip install pip-audit
pip-audit --strict --desc

# npm audit: Test locally
cd ui
npm audit --audit-level=high

# Trivy: CI will enforce on next PR

# Docker pins: Rebuild and verify
docker compose down
docker compose up -d --build
docker compose ps  # All services healthy
```

---

## Stage 2: Pre-commit Security Hooks (~30 minutes)

**Goal:** Catch security issues before code leaves the developer's machine.

### 2.1: Add bandit to pre-commit

Add to `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: ["-c", "backend/pyproject.toml", "-r"]
        files: ^backend/app/
        exclude: ^backend/app/nlp/research_agent/
```

Add bandit config to `backend/pyproject.toml`:

```toml
[tool.bandit]
exclude_dirs = ["tests", "alembic", "app/nlp/research_agent"]
# Skip rules that conflict with our patterns:
# B101: assert used (fine in non-prod code)
# B608: SQL injection (we use parameterized queries via SQLAlchemy text())
skips = ["B101", "B608"]
```

Also add bandit as a CI step:

```yaml
- name: Security scan (bandit)
  working-directory: backend
  run: |
    pip install bandit[toml]
    bandit -c pyproject.toml -r app/
```

**What bandit catches:** Hardcoded passwords, use of `eval()`, weak crypto, unsafe YAML loading, subprocess shell injection, binding to all interfaces, etc.

### 2.2: Add gitleaks to pre-commit

Add to `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
```

Optionally create `.gitleaks.toml` for custom rules:

```toml
[allowlist]
description = "Global allowlist"
paths = [
    '''\.env\.example$''',
    '''tests/''',
    '''conftest\.py$''',
]
```

**What gitleaks catches:** API keys, passwords, tokens, private keys accidentally committed. Scans the diff (pre-commit) or full history (CI).

### 2.3: Add bandit to requirements-dev.txt

```
bandit[toml]
pip-audit
```

### Stage 2 — Verification

```bash
# Test pre-commit hooks
cd /path/to/common-investor
pre-commit run bandit --all-files
pre-commit run gitleaks --all-files

# Run bandit standalone to see current findings
cd backend
bandit -c pyproject.toml -r app/ -f json | python -m json.tool | head -50
```

---

## Stage 3: Container Image Scanning (~30 minutes)

**Goal:** Scan built Docker images (not just filesystem) for OS-level vulnerabilities.

### 3.1: Add Trivy image scan to CI

Add after the Docker build step (or as a separate job):

```yaml
  scan-images:
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4

      - name: Build backend image
        run: docker build -t ci-backend:scan ./backend

      - name: Scan backend image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: "ci-backend:scan"
          format: "table"
          exit-code: "1"
          severity: "CRITICAL,HIGH"

      - name: Build frontend image
        run: docker build -t ci-frontend:scan ./ui

      - name: Scan frontend image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: "ci-frontend:scan"
          format: "table"
          exit-code: "1"
          severity: "CRITICAL,HIGH"
```

**What this adds beyond Stage 1:** The existing Trivy scan checks source files. This scans the built image including OS packages (openssl, glibc, etc.) from the base image. Common findings: outdated openssl in python:3.11-slim, vulnerable zlib in alpine.

### 3.2: Generate SBOM (Software Bill of Materials)

Add to CI:

```yaml
      - name: Generate SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: "ci-backend:scan"
          format: "cyclonedx"
          output: "sbom-backend.json"

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom-backend.json
```

**Why:** SBOMs track every component in your image. Useful for incident response ("are we affected by CVE-XXXX?") and eventually required for compliance.

### Stage 3 — Verification

```bash
# Test locally with Trivy CLI
brew install trivy  # or: docker run aquasec/trivy

# Scan built image
docker build -t ci-backend:test ./backend
trivy image ci-backend:test --severity CRITICAL,HIGH

docker build -t ci-frontend:test ./ui
trivy image ci-frontend:test --severity CRITICAL,HIGH
```

---

## Stage 4: Pin Python Dependencies (~30 minutes)

**Goal:** Reproducible builds and protection against supply chain attacks.

### 4.1: Generate pinned requirements files

```bash
cd backend

# Pin production deps
pip-compile requirements.txt -o requirements.lock --strip-extras

# Pin dev deps
pip-compile requirements-dev.txt -o requirements-dev.lock --strip-extras
```

**Why:** Without version pins, `pip install -r requirements.txt` installs whatever the latest version is. A compromised or buggy release of any package (or its transitive deps) would be pulled automatically. Pinned files lock the exact versions.

### 4.2: Use lock files in Dockerfile and CI

```dockerfile
# backend/Dockerfile
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
```

```yaml
# CI
- name: Install dependencies
  run: pip install -r requirements-dev.lock
```

### 4.3: Add pip-compile to dev workflow

Add to `requirements-dev.txt`:
```
pip-tools
```

Document in CLAUDE.md:
```markdown
### Updating dependencies
To update a dependency: edit requirements.txt, then run:
pip-compile requirements.txt -o requirements.lock --strip-extras
pip-compile requirements-dev.txt -o requirements-dev.lock --strip-extras
```

### Stage 4 — Verification

```bash
# Verify lock files install cleanly
pip install -r requirements-dev.lock
pytest tests/ --tb=short -q
```

---

## Stage 5: Frontend Upgrades (Deferred — separate effort)

**Goal:** Reduce frontend attack surface by upgrading EOL runtimes.

### 5.1: Upgrade Node.js 18 -> 22 LTS

- Update `ui/Dockerfile`: `FROM node:22-alpine`
- Update CI: `node-version: "22"`
- Run `npm install` to regenerate lock file
- Run all frontend tests
- Test UI manually

### 5.2: Upgrade Next.js 13 -> 14 (or 15)

- Next.js 14 is mostly backward-compatible with 13 App Router
- Key changes: `next/image` import path, metadata API tweaks
- Run `npm install next@14` and fix any build errors
- Test all pages manually

**Why deferred:** These upgrades have UI testing implications and should be a focused effort, not bundled with security tooling.

---

## Implementation Order

| Stage | What | Blocks CI? | Effort | Dependencies |
|-------|------|-----------|--------|-------------|
| **1** | Dependabot + pip-audit + npm audit + Trivy blocking + pin images | Yes (new gates) | ~1 hour | None |
| **2** | bandit + gitleaks pre-commit hooks | No (local only) + CI step | ~30 min | Stage 1 |
| **3** | Container image scanning + SBOM | Yes (new gate) | ~30 min | Stage 1 |
| **4** | Pin Python deps (lock files) | No (swap file refs) | ~30 min | Stage 1 |
| **5** | Node/Next.js upgrades | No | ~2-3 hours | Separate effort |

**Recommended approach:** Implement Stages 1-4 as a single PR. Stage 5 is a separate PR.

---

## Files Changed (Stages 1-4)

| File | Stage | Change |
|------|-------|--------|
| `.github/dependabot.yml` | 1.1 | NEW — Dependabot config for pip, npm, docker, actions |
| `.github/workflows/ci.yml` | 1.2-1.4, 2.1, 3.1-3.2 | Add pip-audit, npm audit, bandit steps; make Trivy blocking; add image scan job |
| `docker-compose.yml` | 1.5 | Pin postgres and redis image tags |
| `backend/Dockerfile` | 1.5 | Pin python base image tag |
| `ui/Dockerfile` | 1.5 | Upgrade node 18 -> 20 (or 22), pin tag |
| `.pre-commit-config.yaml` | 2.1-2.2 | Add bandit and gitleaks hooks |
| `backend/pyproject.toml` | 2.1 | Add [tool.bandit] config |
| `backend/requirements-dev.txt` | 2.3 | Add bandit[toml], pip-audit, pip-tools |
| `backend/requirements.lock` | 4.1 | NEW — pinned production deps |
| `backend/requirements-dev.lock` | 4.1 | NEW — pinned dev deps |
| `.gitleaks.toml` | 2.2 | NEW — gitleaks allowlist config |

---

## Success Criteria

After all stages:

1. **Dependabot** creates PRs automatically for vulnerable deps
2. **pip-audit** blocks CI if any Python CVE is found
3. **npm audit** blocks CI if any high/critical npm CVE is found
4. **bandit** blocks CI if Python security anti-patterns are found
5. **Trivy** blocks CI on critical/high filesystem vulnerabilities
6. **Trivy image scan** blocks CI on critical/high OS-level vulnerabilities in built containers
7. **gitleaks** prevents accidental secret commits locally
8. **All Docker images** pinned to specific versions
9. **All Python deps** pinned via lock files
10. **SBOM** generated per build as artifact
