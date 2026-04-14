Update all dependency lock files and run security audits.

## Steps

### 1. Python lock files
```bash
cd backend
pip-compile requirements.txt -o requirements.lock --strip-extras --index-url https://pypi.org/simple/
pip-compile requirements-dev.txt -o requirements-dev.lock --strip-extras --index-url https://pypi.org/simple/
```

IMPORTANT: Always use `--index-url https://pypi.org/simple/` to avoid embedding corporate registry tokens in lock files (GitHub Push Protection will block the push).

### 2. Python audit
```bash
pip-audit -r requirements.lock --strict --desc
pip-audit -r requirements-dev.lock --strict --desc
```

Report any CVEs found. If a CVE has no fix available, note it as accepted risk.

### 3. npm lock file (MUST use Node 20 container to match CI)
```bash
cd ui
docker run --rm --platform linux/amd64 \
  -v "$(pwd)/package.json":/app/package.json \
  -v "$(pwd)/package-lock.json":/app/package-lock.json \
  -v /tmp/lock-output:/output \
  node:20.20.2-alpine sh -c "cd /app && npm ci >/dev/null 2>&1 && npm audit fix >/dev/null 2>&1; cp package-lock.json /output/package-lock.json"
cp /tmp/lock-output/package-lock.json ./package-lock.json
rm -rf /tmp/lock-output
```

IMPORTANT: Do NOT regenerate the lock file with local Node (may be v24) — CI uses Node 20 and the lock files are incompatible across major npm versions.

### 4. npm audit
```bash
cd ui
npm audit --audit-level=critical
```

Report any critical CVEs. High-severity CVEs are accepted if they are Next.js DoS-only (see dependency_policy.md).

### 5. Verify tests still pass
```bash
cd backend && pytest tests/ -v --tb=short -q
cd ui && npx vitest --run
```

### 6. Summary
Report what changed: upgraded versions, new CVEs found, CVEs resolved, and whether CI will pass.
