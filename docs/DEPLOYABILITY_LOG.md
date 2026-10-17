# Deployability log

Running record of the push to make EPL_app a cleanly deployable product.
Newest first. Each entry: what changed, why, how it was checked.

## 2026-10-17 — Iteration 1: foundations + payment security

**Found**
- Four parallel backends (`app/`, `backend/`, `src/`, `functions/`); only
  `app/` is deployed. The frontend that ships is `frontend/index.html`, but
  CI built an unused Next.js app. 6 of 7 Python test files tested dead code.
- `fastapi 0.109` + `httpx 0.28` → `TestClient` crashed; tests could not run.
- **Live PayFast merchant key + passphrase committed in `cloudbuild.yaml`.**
- **`POST /api/users/upgrade-manual` let any signed-in user grant themselves Pro.**
- PayFast ITN skipped signature checks when no passphrase was set, didn't
  check amount/merchant, never confirmed with PayFast.
- `python-multipart` missing from production deps → the ITN webhook 500'd
  on every call, so paid upgrades could never have applied automatically.
- CORS `*` with credentials; `LOG_FORMAT=json` accepted but not implemented.
- Deploy targets disagreed (`epl-api` vs `epl-backend`).

**Changed**
- Archived dead code to `archive/legacy/`; untracked generated artefacts.
- Upgraded FastAPI/uvicorn/pydantic; `requirements-dev.txt`; `pyproject.toml`
  with pytest + ruff config.
- Payments hardened (see commit `fix(security)…`), manual upgrade removed,
  checkout tied to the signed-in uid, return URL allow-list.
- `cloudbuild.yaml` uses Secret Manager; `scripts/setup-secrets.sh`.
- Dockerfile: non-root, no build toolchain, `/ping` healthcheck.
- New CI/CD workflows in `ci/github-workflows/` (bot can't write
  `.github/workflows/` — needs a manual copy).
- JSON structured logging for Cloud Logging; `SKIP_PREWARM`; honest `/health`.
- README, `.env.example`, `docs/DEPLOYMENT.md`, `Makefile` rewritten to match reality.

**Checked**: `ruff check .` clean; `pytest` 16 passed (10 new payment
security tests); `node scripts/check-frontend.mjs` passes; API boots with
`SKIP_PREWARM=true` and serves `/ping`, `/health`; webhook returns 503
unconfigured. Docker build not run locally (no daemon) — CI covers it.

**Action needed from Craig**
1. Rotate PayFast passphrase / merchant key (they are in git history).
2. Copy `ci/github-workflows/*.yml` into `.github/workflows/`.
3. Run `scripts/setup-secrets.sh` before the next deploy.

## Backlog (highest value first)

- [ ] Tests for core API logic: predictions, optimiser constraints (15
      players, ≤3 per club, budget), FDR, briefing meter, plan gating.
- [ ] Optimiser correctness: verify squad rules are enforced.
- [ ] Prediction model: target is `points_per_game` with `total_points`
      and minutes as features → in-sample reconstruction, not a forecast.
      Train on next-GW points from player histories and add a time-split backtest.
- [ ] Rate limiting on expensive endpoints (briefing → Gemini cost).
- [ ] Frontend: CSP/security headers in `firebase.json`; error states; SW cache versioning.
- [ ] Firestore security rules checked into repo.
- [ ] Privacy policy / terms pages (needed for app stores + PayFast).
- [ ] Staging environment.
