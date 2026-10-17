# Deployability log

Running record of the push to make EPL_app a cleanly deployable product.
Newest first. Each entry: what changed, why, how it was checked.

## 2026-10-17 — Iteration 8: mobile + accessibility, planning-gameweek fixes

Audited every tab at 375–390 px and with axe-core (WCAG 2 A/AA) against the
demo stack.

**Found**
- 217 colour-contrast failures: `--text3` was 2.2:1 and `--text2` borderline;
  defender/forward/midfielder accents, Intel badges and trend ranks also
  under 4.5:1.
- Unlabelled selects and range sliders (critical); horizontally scrollable
  captain row and FDR table not keyboard-focusable.
- Intel → Trending forced two 240 px columns, widening the page to 516 px on
  phones.
- FPL calls goalkeepers `GKP`; the CSS only styled `.pos-GK`, so every
  goalkeeper badge was unstyled with live data.
- Captain picks showed fixtures as "TBC" and the FDR started from a finished
  gameweek: both used `is_current` (already played) instead of the next deadline.
- No `prefers-reduced-motion` support.

**Changed**
- Text/accents lifted to ≥4.5:1 on every card background; badges darkened.
- `aria-label`s on all selects/sliders; focusable labelled scroll regions.
- Responsive trend columns; `.pos-GKP`/`.pt-GKP` styles.
- `planning_gameweek()` helper (next deadline, falls back to current) used by
  captain picks and FDR.
- Reduced-motion media query.
- Mock FPL dates are relative to today (next deadline always ~3 days away).
- `e2e_fullstack.mjs` now also runs axe on every panel and checks no tab
  scrolls horizontally at 375 px (23 checks).

**Checked**: ruff clean; pytest 59 passed; full-stack 23/23 with zero axe
violations; unit browser tests 6/6.

## 2026-10-17 — Iteration 7: full-stack run against a mock FPL API

Built `scripts/mock_fpl.py` (deterministic 20-club league, 8 GWs played,
team id 1) and `scripts/demo.sh` / `make demo`, then drove every tab of the
real SPA against the real API in Chromium (`scripts/e2e_fullstack.mjs`).

**Found**
- **`/api/players/three-gw` took 42 s and `/value` 22 s**, synchronously,
  freezing the whole instance: captain, 3-GW, value and differentials called
  sklearn once per player (three-gw twice). Every other panel hung behind them.
- **Injuries tab never loaded** — `loadInjuries()` was never called; the
  Intel badge never updated.
- **Header gameweek bar never populated** — `loadGWBar()` was never called;
  it would also have counted down to the *current* (passed) deadline.
- **Briefing targeted the wrong gameweek** ("GW 8 · deadline passed") — it
  used the current GW, not the next deadline.
- Team import ignored `FPL_API_BASE` (hard-coded host), so it couldn't be
  pointed at a mock or proxy.
- On mock data (8 rounds) the next-GW model's backtest *didn't* beat
  PPG-to-date (MAE 1.63 vs 1.58) and the auto gate correctly kept the
  snapshot models.

**Changed**
- `_predict_map()` — one `predict_batch` per list endpoint: 42 s → 0.07 s.
- Injuries load with the Intel tab and sub-tab; GW bar loads at start and
  shows the next deadline; briefing label/deadline/meter/cache use next GW.
- Team import uses `settings.FPL_API_BASE`.
- `make demo` / `make demo-down` / `make e2e-full`; full-stack smoke added
  to the proposed CI.

**Checked**: ruff clean; pytest 59 passed (+5 batching tests — old code fails
4); `scripts/e2e.mjs` 6/6; `scripts/e2e_fullstack.mjs` 16/16 panels with no
console errors or failed API calls.

## 2026-10-17 — Iteration 6: launch-grace UI, error states, rate limiting

**Found**
- **The launch offer didn't work in the UI.** The SPA unlocked Pro features
  only for `plan === 'pro'`; founders (`founder`) and grace-period
  anonymous/free users — whom the API serves as Pro — saw lock screens.
- Pro-gated 403s never opened the upgrade modal (`detail` is an object,
  the SPA compared it to a string) — users saw "Access denied".
- Errors surfaced as "HTTP 500" / "Failed to fetch"; the SW returned its
  offline placeholder with status 200, so offline looked like empty data;
  the status pill stayed "Online" offline.
- No per-client rate limiting.

**Changed**
- `/api/users/me` returns `effective_plan` (also for anonymous users); the
  SPA gates on `hasPro()` from it and asks the API even when signed out.
- `apiFetch`: upgrade modal on `upgrade_required`, readable messages for
  429 / 5xx / network / offline; offline banner; SW offline response is 503.
- `app/utils/rate_limit.py`: sliding-window per-IP limits per instance —
  20/min briefing & optimiser, 30/min team import, 20/min payments, 240/min
  default; probes and PayFast webhook exempt; 429 with `Retry-After`.
- `scripts/e2e.mjs` (renamed from e2e-xss): XSS + error states + upgrade
  modal + grace-period UI. Old frontend fails 5 of its 6 checks.

**Checked**: ruff clean; pytest 54 passed; frontend static checks and all 6
browser checks pass.

## 2026-10-17 — Iteration 5: fixtures bug, honest model metrics, next-GW model

**Found**
- `get_fixtures()` truncated every result to 10 matches, so the FDR heatmap
  (up to 10 GWs), the 3-GW planner and captain fixture context only ever saw
  the first gameweek.
- Cache ignored per-key TTLs; `get_cache_manager()` could hand out
  different instances depending on call arguments.
- `/api/models/info` advertised invented accuracy figures ("80-86%").
- Models predicted season PPG from season totals (target leakage, no
  out-of-sample evaluation).
- HistGradientBoosting fits ran ~10× slower in worker threads (OpenMP sized
  to the host, not the container).

**Changed**
- Fixtures: `limit` param (UI keeps 10; internal callers get everything);
  raw fixtures cached 5 min. Cache rewritten with per-key expiry, one instance.
- `app/ml/next_gw.py`: per-fixture dataset (features strictly from earlier
  rounds), walk-forward backtest vs rolling-4 and PPG-to-date baselines,
  next-round prediction (doubles summed, blanks 0).
- `PredictionService.refresh_next_gw()`: fetches ~500 element-summaries
  (8 concurrent), backtests, activates only if it beats both baselines
  (`PREDICTION_MODEL=auto|next_gw|legacy`); runs at startup and on traffic
  every 6h (30 min retry after failure); OpenMP capped at 2 threads.
- `/api/models/info` and `/models/performance` report the measured backtest
  instead of made-up percentages. `python -m app.ml.report` prints it for live data.

**Checked**: ruff clean; pytest 51 passed (+10: fixture completeness, FDR
multi-GW, per-key TTL, leakage test — tampering with round ≥ r leaves round-r
features identical — backtest beats baselines on synthetic data with a
fixture effect, double/blank handling, service activation, legacy mode,
failure retry). Synthetic backtest: MAE 1.42 vs 1.78 (rolling-4) / 1.66 (PPG).
**Not checked on real FPL data** — the sandbox can't reach the FPL API.

**Action needed from Craig**: run `python -m app.ml.report` locally and paste
the numbers into this log; the auto gate already protects production if the
model underperforms.

## 2026-10-17 — Iteration 4: account deletion, transfer rules, non-blocking training

**Found**
- Privacy policy promises deletion, but there was no way to delete an account.
- Transfer suggestions could recommend a 4th player from one club (illegal
  in FPL) and suspended/unavailable players with no `chance_of_playing`.
- Nine endpoints called `prediction_service.train()` synchronously inside
  async handlers: on a cold instance the event loop froze for seconds, and
  concurrent cold requests each trained the models in parallel.

**Changed**
- `DELETE /api/users/me` + "Delete account" footer link (signed-in only):
  cancels a live PayFast subscription first, then removes the Firestore
  record and Firebase Auth user; nothing is deleted if PayFast cancel fails.
- Transfers: 3-per-club rule (selling a same-club player frees the slot),
  status filter; picks now carry `team_id`.
- `PredictionService.ensure_trained()` — trains once in a worker thread
  behind an asyncio lock; all call sites (and startup) use it.

**Checked**: ruff clean; pytest 41 passed (+6: account deletion paths,
transfer rules with a mocked FPL client — fails on the old code — and bank
units); frontend checks + XSS browser test pass.

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
- [x] Transfer endpoint tests + rule fixes (iteration 4).
- [x] FDR tests (iteration 5).
- [ ] `free_transfers` in team import is actually `event_transfers` (transfers made) — mislabelled.
- [ ] Briefing meter is read-then-write; make it a Firestore transaction.
- [x] Next-GW model with walk-forward backtest + auto gate (iteration 5).
- [ ] Record real-data backtest numbers; consider adding previous seasons for early-season rounds.
- [x] Gemini cost cap + per-client rate limiting (iterations 2, 6). Per-instance only — use Cloud Armor if abuse appears.
- [x] Security headers, SW updates, Firestore rules, privacy/terms (iteration 3).
- [ ] Enforce CSP after report-only period; move inline onclick handlers out so `unsafe-inline` can go.
- [x] Account deletion (iteration 4).
- [ ] Staging environment.
- [ ] 3-GW planner multiplies predictions by difficulty; when the next-GW model is active that double-counts fixture difficulty for the first GW.
