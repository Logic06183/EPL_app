# Deployability log

Running record of the push to make EPL_app a cleanly deployable product.
Newest first. Each entry: what changed, why, how it was checked.

## 2026-10-17 — Iteration 3: frontend security, PWA updates, legal pages

**Found**
- **Stored XSS**: FPL team/manager names (user-chosen) and Gemini reasons were
  interpolated into `innerHTML` unescaped. A team named
  `<img src=x onerror=…>` executed script on import — reproduced in Chromium —
  with access to the Firebase ID token.
- Service worker served the app shell cache-first under a fixed cache name,
  so users could stay on an old build indefinitely after a deploy.
- No security headers on Hosting; no Firestore rules in the repo.
- No privacy policy or terms — required by PayFast, Google sign-in
  verification and app stores.

**Changed**
- `esc()` on 64 interpolation sites; numeric-only team ID; static check fails
  on new unescaped interpolations; `scripts/e2e-xss.mjs` Playwright regression
  test (fails on old code, passes now).
- SW: network-first app shell with offline fallback; only same-origin GETs.
- `firebase.json`: nosniff, X-Frame-Options DENY, HSTS, Referrer-Policy,
  Permissions-Policy, COOP `same-origin-allow-popups` (keeps Google popup
  sign-in), CSP in **Report-Only**; `cleanUrls`.
- `frontend/firestore.rules`: deny all client access (API uses Admin SDK).
- `/privacy` and `/terms` describing what the code actually collects/sends
  (incl. Gemini prompt contents, PayFast, POPIA); linked from sign-in + footer.

**Checked**: ruff clean; pytest 35 passed; frontend static checks pass; XSS
browser test passes; screenshots of footer and privacy page at 390px.

**Action needed from Craig**
- Fill `[operator name]` and `[contact email]` in `frontend/privacy.html` and
  `frontend/terms.html` (highlighted in yellow on the pages).
- Deploy rules once: `cd frontend && npx firebase-tools deploy --only firestore:rules`.
- After a week of clean browser consoles, switch the CSP header from
  `Content-Security-Policy-Report-Only` to `Content-Security-Policy`.

## 2026-10-17 — Iteration 2: optimiser correctness, briefing reliability

**Found**
- `/api/teams/optimize` greedy picker broke FPL rules: no 3-per-club limit,
  injured/suspended players eligible, XI = insertion order, formation always
  reported as squad counts (5-5-3), budget often left unspent.
- Gemini call was synchronous inside an async handler → each briefing froze
  the whole instance for up to several seconds; the 8s timeout constant was
  never applied; no cost cap (anonymous users can request briefings for any
  team id during grace).
- Prediction limits used the *stored* plan, so anonymous users got the free
  cap of 10 during grace while every other feature treated them as Pro.

**Changed**
- `app/services/squad_optimizer.py`: exact MILP (scipy/HiGHS) choosing squad,
  XI and captain jointly under all FPL rules; runs in a worker thread
  (~0.8s / 760 players); 422 if the budget can't buy a legal squad. SPA shows (C).
- Gemini: `generate_briefing_reasons_async` — thread + hard timeout +
  `GEMINI_MAX_CALLS_PER_MINUTE` (default 30) per instance, falling back to
  data-only briefings.
- Prediction limits use the effective plan.

**Checked**: ruff clean; pytest 35 passed (+19: optimiser rules, club limit,
captain, beats old greedy, infeasible budget, endpoint contract, grace/paywall,
briefing meter, Gemini cap + timeout). FPL API unreachable from the sandbox,
so the optimiser is tested on a synthetic 20-club league.

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

- [x] Optimiser correctness + tests; plan gating / meter tests (iteration 2).
- [ ] Tests for predictions, FDR, transfers endpoints.
- [ ] Briefing meter is read-then-write; make it a Firestore transaction.
- [ ] Prediction model: target is `points_per_game` with `total_points`
      and minutes as features → in-sample reconstruction, not a forecast.
      Train on next-GW points from player histories and add a time-split backtest.
- [~] Gemini cost cap done; general per-client rate limiting still open.
- [x] Security headers, SW updates, Firestore rules, privacy/terms (iteration 3).
- [ ] Enforce CSP after report-only period; move inline onclick handlers out so `unsafe-inline` can go.
- [ ] Account deletion endpoint (privacy policy promises deletion on request).
- [ ] Staging environment.
