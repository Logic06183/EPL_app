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
| Spearman rank correlation, predicted vs actual points | Is the ranking of players right? | **0.451 / 0.451** (was 0.40 / 0.36 on 2026-10-18 morning; season-average baseline 0.31 / 0.25) | **≥ 0.45 on both seasons** (met 2026-10-18), and ≥ the pre-deadline FPL `ep_next` on the live record over any rolling 8 GWs |
| Captain pick: actual points of the model's #1 | The headline feature. | 7.9 / 6.0; **not** better than the season-average pick (−1.2 / −0.2, CI ±1.3 to ±2.4). One pick per GW over 37 GWs is too noisy for a tight interval; top-3 is the measurable proxy (+0.1 / +0.8) | **Beats season-average captain, CI above zero, both seasons**; live: beats the most-owned captain in ≥ 55 % of GWs. Measure top-3 alongside |
| Top-11 points: mean actual of the model's top 11 | Is the XI it recommends good? | 5.63 / 4.87 (baseline 4.96 / 4.50): +0.67 significant / +0.37 not | **+0.5 over baseline, significant, both seasons** |
| MAE | Calibration for the optimiser and the −4 hit decision | 1.87 / 1.94 (was 2.03 / 2.12) | ≤ 1.85 |
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

- [x] Store FPL's pre-deadline `ep_next` in every `xp_snapshots` document, and score it alongside the model so the Track record page shows model vs FPL vs season-average per gameweek (2026-10-18; first comparable snapshot is GW8).
- [ ] Add the transfer-plan realised gain to scoring: the snapshot keeps the recommended transfers for a sample of imported teams (or at least the global top swaps); after the GW, realised points in minus out.
- [x] `ml/train.py` prints a one-screen GOAL.md scorecard after every run (2026-10-18). The historical FPL `xP` column stays reported but is not a target; the live `ep_next` is.
- [x] `data/` is git-ignored; `python -m ml.train --data data --download` fetches and trains in about a minute on the Mac.

## M1 — Make the model good  (Claude, iterate until the bar is met)

Ideas in rough order of expected gain; each is one experiment, one commit if it wins:

- [x] **Minutes model.** A P(60+ minutes) classifier scales the prediction by sqrt(P60): MAE 1.99 → 1.87, Spearman +0.02 to +0.03 (2026-10-18). Full product and bucketed decompositions were no better.
- [ ] **Use FPL's `ep_next` as a feature** (it is free, pre-deadline information). Cannot be backtested (the historical column is post-deadline); test it live once 8 GWs of snapshots exist.
- [ ] **Team strength from results and xG** with time decay (Dixon-Coles or Elo), home/away split, giving per-fixture expected goals for and against; from that, clean-sheet and goal-involvement probabilities.
- [ ] **Bookmaker odds**: tried 2026-10-18 with football-data.co.uk history; +0.005 Spearman on one season, nothing on the other, and it needs a live key (the-odds-api, free tier) plus a fallback. Parked.
- [ ] Set-piece and penalty takers; double/blank gameweek handling checked. (Per-position models tried 2026-10-18: worse.)
- [x] **Crowd features** (ownership and transfer ranks, price change) and **last-match features**: the biggest gain of the day, Spearman +0.05 to +0.09 (2026-10-18).
- [x] **Captain picker** (2026-10-18): the captain ranking is 0.6·xP + 0.4·season points-per-fixture. With the production bundle the captain pick went 7.9 → 9.8 and 6.0 → 7.0 pts per GW (+0.65, CI −0.11..1.60; +0.76, CI 0.03..1.62), top-3 +0.6 / +0.9. Applied to the captain endpoint, the briefing, the optimiser's captain term and the live snapshot, which now scores the recommended captain.
- [ ] Multi-GW horizon trained directly instead of repeating next-GW; calibrated uncertainty so the optimiser can be risk-aware.
- [ ] Retrain schedule: monthly in-season refit on the current season plus each summer with the finished season added.

## M2 — Runs itself  (Craig sets secrets, Claude wires and checks)

- [x] `CRON_SECRET` and `ADMIN_EMAILS` set on `epl-backend`; Cloud Scheduler enabled; hourly job `xp-refresh` at :07 UTC created (2026-10-18). A manual run refreshed GW8 and saved `xp_snapshots/2026-27-gw8` with the recommended captain and FPL's `ep_next` for 667 players. Unauthenticated refresh returns 403.
- [ ] **Claude:** after GW8 finishes (deadline 2026-10-23), confirm `xp_results/2026-27-gw8` exists and the Track record tab shows model vs season average vs FPL.
- [ ] **Claude:** failure alert: if the hourly refresh, a snapshot or scoring fails, Craig gets an email or push within the hour (Cloud Monitoring alert on the log line, or the refresh endpoint notifies).
- [ ] **Craig:** unlock GitHub Actions (account billing) and add repo secrets `GCP_SA_KEY`, `GOOGLE_API_KEY`, `FIREBASE_TOKEN` so a push to `main` deploys itself. Until then deploy from the Mac:
      `gcloud run deploy epl-backend --source . --region us-central1 --project epl-prediction-app --update-env-vars ENVIRONMENT=production`
      and `cd frontend && firebase deploy --only hosting --project epl-prediction-app`.

## M3 — Take money  (Craig: accounts; Claude: code)

- [ ] **Craig:** PayFast: make a free sandbox account (the shared test merchant 10000100 rejects every signed request, checked 2026-10-20), set a passphrase and turn on recurring billing. On `epl-backend` set `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`, with `PAYFAST_SANDBOX=true` first.
- [ ] **Claude:** sandbox purchase end to end: Go Pro → PayFast sandbox → return → `/api/users/me` shows `pro`. Then **Craig** sets `PAYFAST_SANDBOX=false`.
- [ ] **Craig:** Paddle or Lemon Squeezy account (merchant of record, handles UK/EU VAT); give Claude the API key and webhook secret.
- [ ] **Claude:** GBP/USD checkout alongside PayFast, webhook signature verified, upgrade by uid, tests like `tests/test_payments.py`.
- [x] Pricing decided 2026-10-20: free this season, founders free for life, paywall 1 Aug 2027, R449 season pass + R79/month (`docs/pricing.md`). Prices and copy applied; `LAUNCH_FREE_UNTIL=2027-08-01`.
- [ ] **Claude:** before 1 Aug 2027 add `require_pro` to the Pro endpoints listed in `docs/pricing.md`.

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
