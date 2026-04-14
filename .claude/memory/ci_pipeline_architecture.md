---
name: CI Pipeline Security Architecture
description: Design decisions behind CI security gates — which scans block merges, why some are advisory, Trivy ignore-unfixed rationale, npm audit threshold logic
type: feedback
---

## CI Security Gate Design

**Merge gate:** Only `all-tests-pass` job is in the branch protection path. It depends on `test` job only. Security scan jobs run in parallel and show as PR checks but don't block the merge button (unless branch protection is configured to require them).

**Blocking vs advisory scans:**

| Scan | Blocking? | Why |
|------|-----------|-----|
| `pip-audit -r requirements.lock` | Yes (in test job) | Lock file is our source of truth; 0 CVEs expected |
| `bandit --severity-level medium` | Yes (in test job) | Code we control; no excuse for security anti-patterns |
| `npm audit --audit-level=critical` | Yes (in frontend security-scan) | Only critical; high threshold deferred until Next.js 15+ |
| Trivy fs scan (ci.yml security-scan) | Advisory (exit-code 0) | SARIF upload to GitHub Security tab; duplicate of npm audit + pip-audit |
| Trivy fs scan (frontend-tests.yml) | Advisory (exit-code 0) | Same rationale as above |
| Trivy image scan — backend | Blocking (exit-code 1) | OS CVEs in built image; not caught by pip-audit |
| Trivy image scan — frontend | Blocking (exit-code 1, vuln-type=os) | OS CVEs only; npm CVEs handled by npm audit step |

**`ignore-unfixed: true` on all Trivy scans** — CVEs without upstream patches shouldn't block CI since we can't fix them. Only fail on CVEs with available fixes.

**Frontend image scan uses `vuln-type: os`** — npm CVEs in node_modules would duplicate the npm audit gate. Image scan focuses on Alpine OS packages only.

**Why:** These decisions were made iteratively during the security hardening PR after seeing real CI failures. The alternative (all scans blocking) caused persistent red checks from unfixable CVEs and duplicate npm findings.

**How to apply:** When adding new CI security steps, decide blocking vs advisory based on: (1) can we actually fix the findings? (2) is another gate already covering this? If both no, make it blocking. Otherwise advisory.
