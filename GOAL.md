# The goal

**A live FPL assistant that people pay for because its predictions are
provably good, used every gameweek on web, Mac and phone.**

"Done" means every box below is ticked and checked, not just coded.
Work top to bottom. Each milestone says who does it: **Craig** (needs his
accounts, money or judgement) or **Claude** (Claude Code can do it alone).
Tick boxes in this file as they're verified, and add a line to the log in
`ROADMAP.md`.

Branch with all the work so far: `claude/loving-allen-fd1rpb`.

---

## Definition of done

- [x] The site is live from `main`, and `python scripts/smoke_test.py` passes against it (2026-10-18)
- [ ] Predictions are snapshotted before every deadline and scored after (Track record tab fills up each gameweek)
- [ ] Someone can pay, by PayFast in ZAR and by card in GBP/USD, and gets Pro automatically
- [ ] A Mac app is installed from a signed download and sign-in works in it
- [ ] Deadline reminders reach people (calendar feed today, email once a provider exists)
- [ ] The funnel can be read in `/api/admin/funnel` and gets checked weekly
- [ ] Pricing is decided and the paywall is switched on for 2027-28 pre-season

---

## M1 — Ship what's built  (Craig, ~30 min, then Claude verifies)

The Claude GitHub App couldn't push workflow files, so these steps are manual.

- [x] copy `docs/proposed-workflows/*.yml` over `.github/workflows/`, delete `docs/proposed-workflows/`, commit.
      Done 2026-10-18 from the Mac (`9ec7fe5`); the `gh` token there has the `workflow` scope.
- [x] merge `claude/loving-allen-fd1rpb` → `main`. Merged as PR #1 on 2026-10-18.
      GitHub Actions is locked on the account (billing) and the repo has no Actions secrets, so deploys run from the Mac:
      `gcloud run deploy epl-backend --source . --region us-central1 --project epl-prediction-app --update-env-vars ENVIRONMENT=production`
      and `cd frontend && firebase deploy --only hosting --project epl-prediction-app`.
- [ ] **Craig:** unlock GitHub Actions (github.com → Settings → Billing) and add repo secrets `GCP_SA_KEY`, `GOOGLE_API_KEY`,
      `FIREBASE_TOKEN` so a push to `main` deploys itself. Until then, deploy from the Mac as above.
- [x] **Claude:** `python scripts/smoke_test.py https://epl-prediction-app.web.app` → all PASS (2026-10-18).
      The xP model built from live data: GW8, 667 players, 6 GWs of history. One fix was needed:
      the predictions endpoint gated on the stored plan instead of the effective plan (`d12c874`).
- [x] **Claude:** open the site, import a real team ID, then check the briefing, Transfer plan, chips, mini-league and share card.
      Checked with team 1 on 2026-10-18: all render. Fixed the blank GW header bar (loader never called) and a
      `null` points gap in the mini-league rivals row (`c40769a`).

## M2 — Make the track record run itself  (Craig sets secrets, Claude checks)

- [ ] **Craig:** on Cloud Run `epl-backend`, set `CRON_SECRET` (any long random string) and `ADMIN_EMAILS` (your Google email).
- [ ] **Craig:** create the hourly Cloud Scheduler job (command in README, "Prediction track record").
- [ ] **Claude:** after the next deadline, check Firestore has `xp_snapshots/<season>-gw<N>`.
      After that gameweek finishes, check `xp_results/...` exists and the Track record tab shows it.

## M3 — Take money  (Craig: accounts; Claude: code)

- [ ] **Craig:** PayFast: set a passphrase in the dashboard. On `epl-backend` set `PAYFAST_MERCHANT_ID`,
      `PAYFAST_MERCHANT_KEY` and `PAYFAST_PASSPHRASE`, with `PAYFAST_SANDBOX=true` first.
- [ ] **Claude:** run a sandbox purchase end to end: Go Pro → PayFast sandbox → return → `/api/users/me` shows `pro`.
      The notification must reach `/api/payments/webhook` and pass all checks; Cloud Run logs show why if it doesn't.
      Then **Craig** sets `PAYFAST_SANDBOX=false`.
- [ ] **Craig:** create a Paddle or Lemon Squeezy account (merchant of record, handles UK/EU VAT) and give Claude the API key + webhook secret.
- [ ] **Claude:** add a GBP/USD checkout alongside PayFast (pick by the user's choice or locale), verify its webhook signature,
      upgrade by uid, with tests in the same style as `tests/test_payments.py`.

## M4 — Mac app  (Claude builds on the Mac; Craig signs)

Two stages. Stage A works today with zero code.

- [ ] **Stage A, today (Craig, 1 min):** in Safari on macOS 14+, open the site → File → **Add to Dock**.
      That gives a real app window with its own Dock icon, and Google sign-in works because it's Safari.
      Good enough for Craig, and worth telling users about.
- [x] **Stage B, a downloadable app:** Claude scaffolds `desktop/` with **Tauri v2**
      (small, native WebKit, about a 10 MB download) loading `https://epl-prediction-app.web.app`.
      - **Sign-in gotcha:** Google blocks OAuth inside embedded webviews (`disallowed_useragent`),
        so `signInWithPopup` will fail in the app. Fix: open sign-in in the system browser and hand the
        Firebase ID token back via a deep link (`fplai://auth?token=...`), or add a backend endpoint that
        mints a Firebase custom token after a browser sign-in. **Test sign-in first, before polishing anything else.**
      - PayFast/Paddle checkout should also open in the system browser.
      - Window remembers its size; menu bar has Reload; app icon made from `frontend/icon.svg`.
      - Acceptance: `npm run tauri build` produces a `.app` and `.dmg`; on a clean Mac the app opens,
        signs in, imports a team and shows the plan.
      - **Built 2026-10-18** (`desktop/`, see `desktop/README.md`): 4.4 MB `.app`, 1.9 MB `.dmg` at
        `desktop/src-tauri/target/release/bundle/`. Sign-in goes through the system browser and comes back via
        `fplai://auth` → `POST /api/users/desktop-token` → `signInWithCustomToken`. Verified on this Mac: the
        bundle registers the scheme, a test `open "fplai://auth?ct=..."` reaches the page, malformed links are
        rejected, the browser hand-off page opens the sign-in modal, backend endpoint has tests.
      - [x] **Craig:** open the built app, click Sign in → Continue with Google in the browser → confirm the app
        shows you signed in. Done 2026-10-18: signed in inside the app on Craig's Mac. Google sign-in works in the app.
- [ ] **Craig:** Apple Developer account (£79/yr) to sign and notarise, so the download opens without Gatekeeper warnings.
      Claude wires the signing settings into `tauri.conf.json` and a `scripts/release-mac.sh`.
- [ ] **Later:** iOS/Android via the existing `mobile/` Capacitor wrapper. It has the same sign-in gotcha and needs
      `@capacitor-firebase/authentication` for native Google sign-in.

## M5 — Reminders and retention  (Craig: provider; Claude: code)

- [x] Calendar feed with 24h/2h reminders (`/api/calendar/deadlines.ics?team=ID`), already built
- [ ] **Craig:** a Resend or Postmark account and a verified sending domain
- [ ] **Claude:** opt-in email reminders 24h before each deadline, carrying captain + transfer from `/plan`,
      sent from the hourly refresh, with one-click unsubscribe; stored on the Firestore user doc

## M6 — Decide and launch paid  (Craig decides, Claude implements)

- [ ] Run this season free. Every week, read `/api/admin/funnel?days=7` and the Track record tab, and note the drop-offs in `ROADMAP.md`.
- [ ] **Craig:** choose pricing from `docs/pricing.md` (recommended: season pass + monthly) and what goes behind the paywall.
- [ ] **Claude:** apply the gating switches (`docs/pricing.md`), update prices in `app/api/payments.py` and the
      upgrade copy, remove "Free this season" from `frontend/og.png` (`docs/README-og.md`), and set `LAUNCH_FREE_UNTIL`
      for the 2027-28 pre-season.
- [ ] **Claude (each summer):** retrain: add the finished season to `SEASONS` in `ml/train.py`, run
      `python -m ml.train --data <dir> --download`, check `app/ml/backtest.json`, commit `app/ml/*`.

---

## Kick-off prompt for Claude Code on the Mac

> Read `GOAL.md`, `ROADMAP.md` and `CLAUDE.md`. Check out `claude/loving-allen-fd1rpb`.
> Work through GOAL.md top to bottom: do every step marked Claude, stop and ask me at each step marked
> Craig, and verify each box before ticking it. Start with M1, then build M4 Stage B (Tauri Mac app),
> proving Google sign-in works in the app before anything else.
