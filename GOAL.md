# The goal

**A self-running subscription app that FPL managers pay for because its
predictions are measurably better than what they can get for free, and the
proof is public.**

Side hustle, not a startup: it has to earn without Craig's weekly attention.
People in the FPL community pay for FPL Review, Fantasy Football Fix and
Fantasy Football Hub today. They will only pay for this if it is at least as
good at the one thing that matters, predicting points, and makes that visible.

"Done" means every box below is ticked and *measured*, not just coded. Work top
to bottom. Each step says who does it: **Craig** (accounts, money, judgement)
or **Claude** (Claude Code does it alone). Tick boxes as they are verified and
add a line to the log in `ROADMAP.md`.

---

## The bar: is it good at predictions?

Measured by `python -m ml.train --data data --download` (walk-forward backtest
on held-out seasons, written to `app/ml/backtest.json`) and by the live track
record (`xp_snapshots` saved before each deadline, scored after).

Pool for every metric: players with at least 30 minutes over the last 6
gameweeks (the decision-relevant set). Per gameweek, then averaged.

| Metric | Why it matters to a paying user | Today (2024-25 / 2025-26 backtest) | Target |
|---|---|---|---|
| Spearman rank correlation, predicted vs actual points | Is the ranking of players right? | 0.40 / 0.36 (season-average baseline 0.31 / 0.25) | **≥ 0.45 on both seasons**, and ≥ the pre-deadline FPL `ep_next` on the live record over any rolling 8 GWs |
| Captain pick: actual points of the model's #1 | The headline feature. | 7.5 / 7.3; **not** significantly better than the season-average pick (CI spans zero; −1.6 in 2024-25) | **Beats season-average captain, CI above zero, both seasons**; live: beats the most-owned captain in ≥ 55 % of GWs |
| Top-11 points: mean actual of the model's top 11 | Is the XI it recommends good? | 5.6 / 4.7 (baseline 5.0 / 4.5), significant in one season only | **+0.5 over baseline, significant, both seasons** |
| MAE | Calibration for the optimiser and the −4 hit decision | 2.03 / ≈2.0 | ≤ 1.85 |
| Transfer plan realised gain | Does following the plan gain points vs holding? | not measured | measured live every GW; ≥ 0 on average over the season |

The FPL column `xP` in the historical data scores 0.65, but it was scraped
during or after each gameweek, so it is probably contaminated by lineup news.
The fair comparison is FPL's own `ep_next` captured *before* the deadline,
which the live snapshot must store from now on (M0).

**Stop rule for the model loop:** keep iterating until every Target column
is met on the backtest, then hold for the live record. Every iteration is one
commit with the new `backtest.json`; a change is kept only if the primary
metric (Spearman) improves on both test seasons without the captain or top-11
metrics getting worse.

---

## Definition of done

- [ ] **Good:** every row in the table above meets its Target on the backtest, and the live Track record page shows the same metrics against FPL's `ep_next`, updated automatically every gameweek
- [x] **Live:** the site runs from `main`; `python scripts/smoke_test.py` passes (2026-10-18)
- [ ] **Runs itself:** snapshots before every deadline and scoring after, retraining, payments, reminders and failure alerts all happen with no manual step per gameweek
- [ ] **Paid:** someone can pay by PayFast (ZAR) or by card (GBP/USD) and gets Pro automatically; pricing decided; paywall on for the 2027-28 pre-season
- [x] **Everywhere:** web, Mac app (signed download, Google sign-in works), phone web; verified 2026-10-18 except signing
- [ ] **Valued:** Craig sets the number. Placeholder: 100 paying subscribers, ≥ 60 % of them back every gameweek, < 8 % monthly churn, by GW19 of 2027-28

---

## M0 — Measure fairly  (Claude)

- [ ] Store FPL's pre-deadline `ep_next` (and `chance_of_playing_next_round`) in every `xp_snapshots` document, and score it alongside the model so the Track record page shows model vs FPL vs season-average per gameweek.
- [ ] Add the transfer-plan realised gain to scoring: the snapshot keeps the recommended transfers for a sample of imported teams (or at least the global top swaps); after the GW, realised points in minus out.
- [ ] `ml/train.py`: add MAE/Spearman/captain/top-11 for FPL `xP` only where it can be shown pre-deadline (or drop it and rely on the live `ep_next`); print a one-screen scorecard against the Targets above and exit non-zero if any Target regresses.
- [ ] Keep `data/` out of git; document the two commands in README.

## M1 — Make the model good  (Claude, iterate until the bar is met)

Ideas in rough order of expected gain; each is one experiment, one commit if it wins:

- [ ] **Minutes model × points-per-90.** Predict P(start), P(60+ min) from recent starts, `chance_of_playing_next_round`, news text, rotation patterns; multiply by a per-90 points model. This is where captaincy and the −4 decision go wrong today.
- [ ] **Use FPL's `ep_next` as a feature** (it is free, pre-deadline information). The product's value is the plan built on top, not the raw number.
- [ ] **Team strength from results and xG** with time decay (Dixon-Coles or Elo), home/away split, giving per-fixture expected goals for and against; from that, clean-sheet and goal-involvement probabilities.
- [ ] **Bookmaker odds** for match result and total goals (football-data.co.uk historic for training; a free live odds source each GW). Odds are the strongest public signal for clean sheets.
- [ ] Per-position models or position interactions; set-piece and penalty takers; double/blank gameweek handling checked.
- [ ] Multi-GW horizon trained directly instead of repeating next-GW; calibrated uncertainty so the optimiser can be risk-aware.
- [ ] Retrain schedule: monthly in-season refit on the current season plus each summer with the finished season added.

## M2 — Runs itself  (Craig sets secrets, Claude wires and checks)

- [ ] **Craig:** on Cloud Run `epl-backend`, set `CRON_SECRET` (any long random string) and `ADMIN_EMAILS` (your Google email). Create the hourly Cloud Scheduler job (command in README). Or say "do M2" and Claude does it with gcloud.
- [ ] **Claude:** after the next deadline, confirm `xp_snapshots/<season>-gw<N>` exists; after the GW, `xp_results/...` exists and the Track record tab shows it.
- [ ] **Claude:** failure alert: if the hourly refresh, a snapshot or scoring fails, Craig gets an email or push within the hour (Cloud Monitoring alert on the log line, or the refresh endpoint notifies).
- [ ] **Craig:** unlock GitHub Actions (account billing) and add repo secrets `GCP_SA_KEY`, `GOOGLE_API_KEY`, `FIREBASE_TOKEN` so a push to `main` deploys itself. Until then deploy from the Mac:
      `gcloud run deploy epl-backend --source . --region us-central1 --project epl-prediction-app --update-env-vars ENVIRONMENT=production`
      and `cd frontend && firebase deploy --only hosting --project epl-prediction-app`.

## M3 — Take money  (Craig: accounts; Claude: code)

- [ ] **Craig:** PayFast: set a passphrase in the dashboard. On `epl-backend` set `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`, with `PAYFAST_SANDBOX=true` first.
- [ ] **Claude:** sandbox purchase end to end: Go Pro → PayFast sandbox → return → `/api/users/me` shows `pro`. Then **Craig** sets `PAYFAST_SANDBOX=false`.
- [ ] **Craig:** Paddle or Lemon Squeezy account (merchant of record, handles UK/EU VAT); give Claude the API key and webhook secret.
- [ ] **Claude:** GBP/USD checkout alongside PayFast, webhook signature verified, upgrade by uid, tests like `tests/test_payments.py`.
- [ ] **Craig:** pricing from `docs/pricing.md` (recommended: season pass + monthly) and what sits behind the paywall. **Claude** applies the gating switches, prices and copy, and sets `LAUNCH_FREE_UNTIL`.

## M4 — Everywhere  (mostly done)

- [x] Web, first-visit flow, mobile layout (design review 2026-10-18).
- [x] Mac app (`desktop/`, Tauri v2) with browser hand-off sign-in; verified end to end 2026-10-18.
- [ ] **Craig:** Apple Developer account (£79/yr) to sign and notarise, so the `.dmg` opens without Gatekeeper warnings; `scripts/release-mac.sh` handles it once the `APPLE_*` variables are set.
- [ ] **Craig:** Stage A for your own Mac today: Safari → File → Add to Dock.
- [ ] **Later:** iOS/Android via `mobile/` (Capacitor). Same sign-in gotcha; needs `@capacitor-firebase/authentication`.

## M5 — Keep people coming back  (Craig: provider; Claude: code)

- [x] Calendar feed with 24h/2h reminders (`/api/calendar/deadlines.ics?team=ID`).
- [ ] **Craig:** a Resend or Postmark account and a verified sending domain.
- [ ] **Claude:** opt-in email 24h before each deadline carrying captain, transfer and chip from `/plan`, sent from the hourly refresh, one-click unsubscribe.
- [ ] **Claude:** weekly "how did last week's advice do" line in the email and on the Track record page (this is the marketing: honest, public, every week).

## M6 — Grow and decide  (Craig decides, Claude measures)

- [ ] Run this season free. Every week read `/api/admin/funnel?days=7` and the Track record tab; log drop-offs in `ROADMAP.md`.
- [ ] **Craig:** where the FPL community lives for you (r/FantasyPL, FPL Twitter, a WhatsApp league): post the public track record when it is good, not before.
- [ ] **Craig:** set the "Valued" numbers above and the launch date for the paywall.

---

## Kick-off prompt for Claude Code on the Mac

> Read `GOAL.md`, `ROADMAP.md` and `CLAUDE.md`. Work through GOAL.md top to bottom: do every step
> marked Claude, stop and ask me at each step marked Craig, and verify each box before ticking it.
> Start with M0 (measure fairly), then run the M1 model loop until the bar in "Is it good at
> predictions?" is met. Every experiment is one commit with the new `backtest.json`.
