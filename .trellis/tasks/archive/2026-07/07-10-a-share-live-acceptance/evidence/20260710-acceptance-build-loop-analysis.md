# Bug Analysis: Acceptance images failed before a clean install

## 1. Root Cause Category

- **Category**: E - Implicit Assumption, with D - Test Coverage Gap.
- **Specific cause**: root Docker ignore patterns were assumed to match nested
  workspace output, and the Node base image was assumed to use the same npm
  lock semantics as the host. Neither assumption was encoded or tested.

## 2. Why earlier attempts failed

1. The first build appeared stalled because BuildKit was still receiving the
   nested 4 GB `.next` directory; no Dockerfile step had started.
2. After the context fix, npm 10 in `node:22-slim` rejected an optional SWC peer
   dependency layout that npm 11.17.0 accepted.
3. Regenerating the lock file inside Linux caused unrelated platform-metadata
   churn. It was reverted instead of being committed as a surface fix.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific action | Status |
|---|---|---|---|
| P0 | Test coverage | Assert recursive generated-directory ignore patterns | DONE |
| P0 | Reproducible tooling | Declare npm 11.17.0 and install it in the Web image before `npm ci` | DONE |
| P0 | Integration check | Clean-build both acceptance images without starting services | DONE |
| P1 | Documentation | Add clean-install image rules to the frontend quality spec | DONE |

## 4. Systematic Expansion

- **Similar issues**: any workspace-local generated directory can silently
  inflate a root Docker context; any container using an unpinned package manager
  can interpret the same lock file differently from the host.
- **Design improvement**: treat the package manager and lock file as one
  versioned build contract.
- **Process improvement**: verify image construction separately from guarded
  runtime startup so build defects can be fixed without crossing write gates.

## 5. Knowledge Capture

- [x] Updated `.trellis/spec/frontend/quality-guidelines.md`.
- [x] Added focused configuration regressions.
- [x] Recorded successful API and Web image builds in the acceptance report.
- [x] Template sync checked; this application repository has no
  `src/templates/markdown/spec/` template tree.
