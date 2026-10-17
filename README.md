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

## Paywall and PayFast

- `LAUNCH_FREE_UNTIL` (UTC date). Before it, everyone gets Pro and signed-in
  users are made lifetime "founders". Unset = 2099 = paywall off.
- After it, free users get one team briefing per gameweek; Pro is unlimited.
- To take payments, set on the `epl-backend` service: `PAYFAST_MERCHANT_ID`,
  `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` (the same passphrase must be set
  in the PayFast dashboard; subscriptions require it). Use
  `PAYFAST_SANDBOX=true` to test with sandbox credentials first.
- PayFast notifies `https://epl-prediction-app.web.app/api/payments/webhook`.

## Roadmap

See `ROADMAP.md`.
