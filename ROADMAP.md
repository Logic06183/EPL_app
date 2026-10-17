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
- [ ] Hourly refresh independent of traffic (Cloud Scheduler → endpoint) so snapshots are close to each deadline
- [x] Optimiser: integer programme for squad + XI + captain over 3 GWs; transfer planner with -4 hits vs hold (`app/services/optimizer.py`, `/api/fpl-team/{id}/plan`)
- [x] Escape user/LLM-controlled text in the frontend (FPL team names, Gemini briefing text)
- [x] Estimate free transfers from the manager's history (user can override)
- [ ] Briefing: use the new model; chip advice (bench boost / triple captain timing)
- [ ] Analytics: privacy-friendly event tracking for the funnel (visit → import team → sign in → briefing → upgrade)
- [ ] Retention: email capture + deadline reminder carrying the briefing
- [ ] Pricing review (R199/month is high vs competitors; consider a cheaper season pass)

## Needs Craig

- Rotate PayFast credentials (were committed in the old `cloudbuild.yaml`) and set them on `epl-backend`; set the same passphrase in the PayFast dashboard
- Copy `docs/proposed-workflows/*.yml` into `.github/workflows/` (the Claude GitHub App can't push workflow files). **Do this before merging**: the current backend deploy wipes PAYFAST_* env vars
- Merge `claude/loving-allen-fd1rpb` → `main` to deploy
- Delete the retired Cloud Run services `epl-api` and `epl-backend-sa` if they still exist
- Archive the old `EPL_Fantasy_Optimizer` repo

## Log

- 2026-10-17 — security + PayFast fixes (`eac827f`); repo clean-up and CI (`d518a29`)
- 2026-10-17 — expected-points model + walk-forward backtest (`cfe03e1`): rank corr 0.40/0.36 vs 0.31/0.25 for season average
- 2026-10-17 — live track record (snapshot before deadline, score after) + Track record page; frontend plan-gating fix (`49800af`)
- 2026-10-17 — optimiser + transfer planner; XSS escaping
