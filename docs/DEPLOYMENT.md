# Deploying FPL AI Pro

Two pieces, one GCP/Firebase project (`epl-prediction-app` by default):

| Piece | Where | How |
|-------|-------|-----|
| API (`app/`) | Cloud Run service `epl-backend`, `us-central1` | `cloudbuild.yaml` → Artifact Registry image → `gcloud run deploy` |
| SPA (`frontend/`) | Firebase Hosting | `firebase deploy --only hosting`; `/api/**` and `/health` rewrite to `epl-backend` |

Because Hosting proxies the API, the browser only ever talks to one origin —
no CORS in production, and PayFast's ITN can target
`https://<site>/api/payments/webhook`.

## One-time setup

1. **Rotate the PayFast credentials.** Earlier versions of `cloudbuild.yaml`
   committed the live merchant key and passphrase to git. Generate a new
   passphrase (and ask PayFast to reissue the merchant key if possible) under
   PayFast → Settings → Developer settings. Treat the old values as public.
2. **Secrets + registry**:
   ```bash
   PROJECT_ID=epl-prediction-app ./scripts/setup-secrets.sh
   ```
   Creates the `epl` Artifact Registry repo and these Secret Manager secrets,
   readable by the Cloud Run runtime service account:
   `google-api-key`, `payfast-merchant-id`, `payfast-merchant-key`, `payfast-passphrase`.
3. **Firebase**: Authentication → enable Google provider; Firestore → create
   database (Native mode). Add your Hosting domain(s) to Auth → Settings →
   Authorised domains.
4. **IAM for the runtime service account**
   (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`): Firebase Admin SDK
   Administrator Service Agent (Auth token verification + Firestore).
5. **PayFast merchant settings**: set the passphrase to the one stored in
   Secret Manager. If you enable "Require signature", also set
   `PAYFAST_REQUIRE_SIGNATURE=true` on the service.

## Deploy

```bash
make deploy-backend    # gcloud builds submit --config cloudbuild.yaml
make deploy-frontend   # firebase deploy --only hosting (from frontend/)
curl -fsS https://epl-prediction-app.web.app/health
```

Override defaults with substitutions, e.g. a staging service:

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_SERVICE=epl-backend-staging,_PUBLIC_BASE_URL=https://staging.example.com
```

## CI/CD

Copy `ci/github-workflows/*.yml` into `.github/workflows/` (see the README in
that folder for the required `GCP_SA_KEY` secret and roles). Pushes to `main`
then run CI and, if green, deploy whichever half changed.

## Runtime configuration

All variables are documented in [`.env.example`](../.env.example). The ones
that matter in production:

| Variable | Set by | Notes |
|----------|--------|-------|
| `ENVIRONMENT=production` | cloudbuild | |
| `PUBLIC_BASE_URL` | cloudbuild | builds the PayFast notify URL and allowed return URLs |
| `GOOGLE_API_KEY` | Secret Manager | optional; briefings degrade gracefully |
| `PAYFAST_*` | Secret Manager | the webhook returns 503 until merchant id + passphrase are set |
| `LAUNCH_FREE_UNTIL` | set manually | ISO date; paywall switches on after it |
| `FREE_BRIEFINGS_PER_GW` | optional | default 1 |

To flip the paywall on:

```bash
gcloud run services update epl-backend --region us-central1 \
  --update-env-vars LAUNCH_FREE_UNTIL=2026-11-01
```

## Rollback

```bash
gcloud run revisions list --service epl-backend --region us-central1
gcloud run services update-traffic epl-backend --region us-central1 --to-revisions=<REVISION>=100
firebase hosting:rollback   # from frontend/
```

## Mobile

`mobile/` is a Capacitor shell around `frontend/`. See `mobile/BUILD.md`.
The native app calls `https://epl-prediction-app.web.app/api`.
