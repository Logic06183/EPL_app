# Roadmap

The improvement loop works top to bottom: take the first unchecked item,
ship it in small tested commits, tick it off and add a log line.
Anything that touches money or production (deploys, prices, flipping the
paywall, keys) waits for Craig.

## Thesis

Free FPL tools are good, so people only pay for something they can trust.
The edge is **predictions with a public, honest track record**, delivered as a
personal weekly briefing for *your* team.

## Backlog

- [x] Security: remove self-upgrade endpoint, harden PayFast checkout + ITN, fix briefing meter, lock CORS
- [x] Fix PayFast bugs that stopped payments working (field order, ITN signature, python-multipart, notify URL)
- [x] Clean-up: delete dead code/artefacts/docs, one Dockerfile, accurate README/CLAUDE.md, CI green on live code
- [x] Deploy hygiene: tests gate deploys, `--update-env-vars` so console settings survive
- [x] Real model: next-GW expected points from rolling form, minutes, xG/xA, team/opponent strength, home/away, last season; trained on 2022-23..2025-26
- [x] Backtest harness: walk-forward over past seasons vs a "season average" baseline (`ml/train.py`, `app/ml/backtest.json`)
- [x] Replace hand-typed accuracy claims with measured numbers
- [x] Prediction log: snapshot each GW's predictions before the deadline; score after (`app/services/track_record.py`)
- [x] Public track-record page in the frontend
- [x] Frontend: Pro UI gated on server's effective plan (founders/grace were locked out); app survives Firebase SDK failing to load
- [ ] Retrain each summer: add the new season to `SEASONS` in `ml/train.py`, rerun, commit `app/ml/*`
- [x] Hourly refresh endpoint for Cloud Scheduler (`POST /api/predictions/refresh`, `CRON_SECRET`)
- [x] Optimiser: integer programme for squad + XI + captain over 3 GWs; transfer planner with -4 hits vs hold (`app/services/optimizer.py`, `/api/fpl-team/{id}/plan`)
- [x] Escape user/LLM-controlled text in the frontend (FPL team names, Gemini briefing text)
- [x] Estimate free transfers from the manager's history (user can override)
- [x] Briefing uses the new model (via PredictionService)
- [x] Chip advice in `/plan`: TC on captain doubles, BB on 3+ squad doubles, FH on 4+ blank starters, WC when a rebuild adds 15+ xP; only chips left this half-season
- [x] Analytics: anonymous daily event counts for the funnel; `/api/admin/funnel` (needs `ADMIN_EMAILS`)
- [x] Retention (no provider needed): subscribable deadline calendar with 24h/2h reminders linking to `?team=ID`; last team remembered on device
- [ ] Retention: email reminders carrying the briefing — needs an email provider account (Resend/Postmark) from Craig
- [x] Pricing review → `docs/pricing.md` (recommendation only; Craig decides)
- [ ] International checkout (GBP/USD) via a merchant-of-record provider — needs Craig's account

- [x] Mini-league view: league effective ownership, threats / under-covered / differentials by next-GW swing
- [x] Shareable GW plan card

## Needs Craig

- Rotate PayFast credentials (were committed in the old `cloudbuild.yaml`) and set them on `epl-backend`; set the same passphrase in the PayFast dashboard
- Copy `docs/proposed-workflows/*.yml` into `.github/workflows/` (the Claude GitHub App can't push workflow files). **Do this before merging**: the current backend deploy wipes PAYFAST_* env vars
- Merge `claude/loving-allen-fd1rpb` → `main` to deploy
- Delete the retired Cloud Run services `epl-api` and `epl-backend-sa` if they still exist
- Archive the old `EPL_Fantasy_Optimizer` repo
- Set `ADMIN_EMAILS` on `epl-backend` to read the funnel
- Set `CRON_SECRET` and create the hourly Cloud Scheduler job (command in README)

## Log

- 2026-10-17 — security + PayFast fixes (`eac827f`); repo clean-up and CI (`d518a29`)
- 2026-10-17 — expected-points model + walk-forward backtest (`cfe03e1`): rank corr 0.40/0.36 vs 0.31/0.25 for season average
- 2026-10-17 — live track record (snapshot before deadline, score after) + Track record page; frontend plan-gating fix (`49800af`)
- 2026-10-17 — optimiser + transfer planner; XSS escaping
- 2026-10-17 — chip advice (`/plan` + Transfer plan card)
- 2026-10-17 — deadline calendar feed + `?team=` deep link
- 2026-10-17 — bootstrap CIs on pick metrics: captaincy gap vs season average is noise in both seasons; top-11 +0.65 significant in 2024-25
- 2026-10-17 — code review of the branch: 10 findings fixed (departed players in /plan, deep-link auth race, analytics cap, season-end refresh loop, parallel live fetches, calendar escape, cancelled checkout, funnel reads, 422 on impossible budget, shared track-record loader)
- 2026-10-17 — link previews (Open Graph/Twitter image + tags), better title/description, robots.txt
- 2026-10-18 — shareable GW plan card (canvas PNG via share sheet / download) + ?ref=share attribution
- 2026-10-18 — mini-league view (`/api/fpl-team/{id}/league/{league_id}`)
- 2026-10-18 — fix: 403 upgrade_required from require_pro now opens the upgrade modal (was 'Access denied'); gating switches documented in docs/pricing.md
- 2026-10-18 — first-visit hero (team import from Predictions tab), team ID field accepts pasted FPL links
