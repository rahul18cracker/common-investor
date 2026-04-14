---
name: Alpine Docker Migration Gotchas
description: Lessons learned switching from Debian slim to Alpine base images — bash, UID conflicts, npm lock file Node version mismatch
type: feedback
---

When switching Docker base images to Alpine, these issues will recur:

1. **No bash on Alpine** — only `sh` (busybox ash). All scripts must use `#!/bin/sh` shebang. docker-compose commands must use `/bin/sh`, not `/bin/bash`. Bash-specific syntax (arrays, `[[ ]]`) won't work.

2. **node:alpine UID 1000 conflict** — `node:20-alpine` ships with a `node` user at UID 1000. Creating `appuser` at UID 1000 fails. Use the built-in `node` user instead: `USER node` + `chown -R node:node`.

3. **package-lock.json Node version mismatch** — Lock files generated with npm 11 (Node 24) produce different dependency trees than npm 10 (Node 20). CI uses Node 20. Always regenerate lock files inside a `node:20-alpine` container:
   ```
   docker run --rm --platform linux/amd64 -v $(pwd)/package.json:/app/package.json -v /tmp/out:/output node:20.20.2-alpine sh -c "cd /app && npm install >/dev/null 2>&1 && cp package-lock.json /output/"
   ```
   Use `--platform linux/amd64` to match CI runner architecture.

4. **C-extension packages** — All current deps have musllinux wheels (verified: numpy, pandas, lxml, psycopg2-binary, pydantic-core, cffi, curl-cffi, uvloop, httptools, watchfiles, markupsafe, frozendict). If adding new C-extension deps, verify musllinux wheel availability before merging.

5. **OS patching** — Alpine needs `apk upgrade --no-cache` (not `apt-get upgrade`) in Dockerfiles. Also `pip install --upgrade setuptools wheel` to patch vendored Python CVEs (jaraco.context, wheel).

**Why:** These cost hours of debugging during the security hardening PR. Recording them prevents repeating.

**How to apply:** Check these whenever modifying Dockerfiles, changing base images, or regenerating lock files.
