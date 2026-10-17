# FPL AI Pro

Fantasy Premier League assistant: player point predictions, captain picks,
fixture difficulty, transfer suggestions and a Gemini-written weekly briefing
for your own FPL squad. Free during launch; Pro via PayFast (ZAR) afterwards.

Live: <https://epl-prediction-app.web.app>

## How it fits together

```
Browser / Capacitor app
        │  same-origin /api/**, /health
        ▼
Firebase Hosting  ── frontend/index.html (single-file SPA, PWA)
        │  rewrite
        ▼
Cloud Run "epl-backend"  ── app/ (FastAPI)
        ├── FPL public API (bootstrap, fixtures, entries) — cached in memory
        ├── scikit-learn ensemble (RF + GB + MLP), trained at startup
        ├── Gemini 2.5 Flash (optional) — briefing reasons
        ├── Firebase Auth + Firestore — users, plans, briefing meter
        └── PayFast — subscriptions + ITN webhook
```

| Path | What |
|------|------|
| `app/` | FastAPI service (the only backend that ships) |
| `frontend/` | Static SPA + `firebase.json` hosting config |
| `mobile/` | Capacitor shell that wraps `frontend/` for Android/iOS |
| `tests/` | pytest suite (`test_*.py`) and a Playwright smoke test against production |
| `scripts/` | GCP secret setup, frontend static checks |
| `ci/github-workflows/` | CI/CD workflows to install into `.github/workflows/` |
| `archive/legacy/` | Earlier prototypes kept for reference — not built, tested or deployed |

## Run locally

Needs Python 3.11 and Node 18+ (Node only for the frontend check script).

```bash
cp .env.example .env      # fill in what you need; everything is optional for browsing
make install              # .venv + dev dependencies
make dev                  # API on http://localhost:8001 (docs at /docs)
make frontend             # SPA on http://localhost:3000 (talks to :8001)
```

Sign-in and paid features need Firebase credentials
(`gcloud auth application-default login`). Without them the app runs
anonymously, which during the launch grace period still unlocks everything.

## Checks

```bash
make check                # ruff + frontend static checks + pytest
```

CI runs the same plus a Docker build-and-boot smoke test
(see `ci/github-workflows/ci.yml`).

## Deploy

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Short version:

```bash
./scripts/setup-secrets.sh   # once: Artifact Registry + Secret Manager
make deploy-backend          # Cloud Build → Cloud Run
make deploy-frontend         # Firebase Hosting
```

## API

Interactive docs at `/docs` on any running instance. Main routes:

| Route | Notes |
|-------|-------|
| `GET /health`, `GET /ping` | readiness / liveness |
| `GET /api/players/predictions?top_n=&model_type=&position=` | `basic` (default), `random_forest`, `deep_learning`, `ensemble` |
| `GET /api/players/captain`, `/differentials`, `/value`, `/price-movers`, `/three-gw` | Pro-gated after launch |
| `GET /api/players/search?q=` | |
| `GET /api/teams/fdr?gameweeks=` | fixture difficulty |
| `POST /api/teams/optimize` `{"budget": 100}` | 15-player squad |
| `GET /api/fpl-team/{id}`, `/transfers`, `/briefing` | import an FPL entry |
| `GET /api/gameweek/current`, `GET /api/fixtures?filter=` | |
| `GET /api/users/me` | plan, limits, subscription (bearer token) |
| `POST /api/payments/initialize`, `/cancel`, `/webhook` | PayFast |

## A note on the predictions

The models are trained on the current season's FPL bootstrap data at startup
and predict a points-per-game style score. There is no held-out backtest in
this repo yet, so treat outputs as a ranking aid, not a forecast with known
accuracy.
