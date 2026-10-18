# FPL AI Pro

A Fantasy Premier League assistant: import your FPL team and get a short
"what to do this gameweek" briefing (captain, transfer, flagged players),
plus predictions, fixture difficulty, price movers and value picks.

Live at https://epl-prediction-app.web.app

## How it fits together

| Part | Where | Notes |
|------|-------|-------|
| Frontend | `frontend/` → Firebase Hosting | Plain static `index.html`, Google sign-in via Firebase Auth |
| Backend | `app/` → Cloud Run `epl-backend` (us-central1) | FastAPI. Firebase Hosting rewrites `/api/**` and `/health` to it |
| Data | FPL public API | Cached in memory per instance |
| Users | Firestore `users` collection | Plan, PayFast token, briefing meter |
| Briefing wording | Gemini (`GOOGLE_API_KEY`) | Optional; falls back to template text |
| Payments | PayFast recurring subscription | R199/month; see below |
| Mobile | `mobile/` | Capacitor wrapper around `frontend/` |

## Local development

```sh
pip install -r requirements-dev.txt
cp .env.example .env          # fill in what you need
uvicorn app.main:app --port 8001
# open frontend/index.html via any static server; on localhost it calls :8001
ruff check . && pytest
```

## Deploying

- Backend: push to `main` touching `app/`, `requirements_production.txt` or
  `Dockerfile` → `.github/workflows/deploy-backend.yml` runs tests, then
  `gcloud run deploy epl-backend --source .`. It uses `--update-env-vars`, so
  settings made on the service in the Cloud Run console survive deploys.
- Frontend: push to `main` touching `frontend/` → `deploy-frontend.yml`
  (needs the `FIREBASE_TOKEN` secret), or `cd frontend && firebase deploy --only hosting`.

After any deploy, check the live site end to end (model built from live FPL
data, sane predictions, optimiser, calendar, track record):

```sh
pip install httpx && python scripts/smoke_test.py https://epl-prediction-app.web.app
```

## Paywall and PayFast

- `LAUNCH_FREE_UNTIL` (UTC date). Before it, everyone gets Pro and signed-in
  users are made lifetime "founders". Unset = 2099 = paywall off.
- After it, free users get one team briefing per gameweek; Pro is unlimited.
- To take payments, set on the `epl-backend` service: `PAYFAST_MERCHANT_ID`,
  `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` (the same passphrase must be set
  in the PayFast dashboard; subscriptions require it). Use
  `PAYFAST_SANDBOX=true` to test with sandbox credentials first.
- PayFast notifies `https://epl-prediction-app.web.app/api/payments/webhook`.

## Analytics

The frontend posts anonymous event names (visit, team import, briefing view,
sign-in, paywall view, upgrade click, checkout start/return, …) to
`/api/events`; the backend keeps daily counts in Firestore `analytics_daily`.
No ids, cookies or IPs are stored. Set `ADMIN_EMAILS` on the service and
call `/api/admin/funnel?days=30` signed in as that account to see the funnel.

## Prediction track record

`/api/models/track-record` (and the Track record tab) shows the walk-forward
backtest from `ml/train.py` plus this season's gameweeks: predictions are
saved to `xp_snapshots` before each deadline and scored into `xp_results`
after. Retrain each summer: `python -m ml.train --data <dir> --download`
after adding the finished season to `SEASONS`.

So snapshots are taken close to each deadline even with no traffic, set
`CRON_SECRET` on the service and add an hourly Cloud Scheduler job:

```sh
gcloud scheduler jobs create http xp-refresh --location us-central1 \
  --schedule "7 * * * *" --http-method POST \
  --uri https://epl-prediction-app.web.app/api/predictions/refresh \
  --headers X-Cron-Secret=$CRON_SECRET
```

## Roadmap

See `ROADMAP.md`.
