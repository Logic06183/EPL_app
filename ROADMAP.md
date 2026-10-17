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
- [ ] Real model: next-GW expected points from rolling form, minutes, fixture difficulty, home/away; trained on past seasons
- [ ] Backtest harness: walk-forward over past seasons, report MAE / rank correlation vs a "season average" baseline
- [ ] Replace hand-typed accuracy claims with measured numbers
- [ ] Prediction log: store each GW's predictions; score against actuals once the GW finishes
- [ ] Public track-record page in the frontend
- [ ] Optimiser: proper ILP squad selection + multi-GW transfer planner (with hits)
- [ ] Briefing: use the new model; chip advice (bench boost / triple captain timing)
- [ ] Analytics: privacy-friendly event tracking for the funnel (visit → import team → sign in → briefing → upgrade)
- [ ] Retention: email capture + deadline reminder carrying the briefing
- [ ] Pricing review (R199/month is high vs competitors; consider a cheaper season pass)

## Needs Craig

- Rotate PayFast credentials (were committed in the old `cloudbuild.yaml`) and set them on `epl-backend`; set the same passphrase in the PayFast dashboard
- Merge `claude/loving-allen-fd1rpb` → `main` to deploy
- Delete the retired Cloud Run services `epl-api` and `epl-backend-sa` if they still exist
- Archive the old `EPL_Fantasy_Optimizer` repo

## Log

- 2026-10-17 — security + PayFast fixes (`eac827f`); repo clean-up and CI
