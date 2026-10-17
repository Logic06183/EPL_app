# GitHub Actions workflows (pending install)

These replace the outdated files in `.github/workflows/`. They are kept here
because the bot that prepared them is not allowed to write to
`.github/workflows/`. Install them with:

```bash
git rm .github/workflows/test-and-lint.yml
cp ci/github-workflows/*.yml .github/workflows/
git add .github/workflows && git commit -m "ci: install updated workflows"
```

| File | What it does |
|------|--------------|
| `ci.yml` | ruff + pytest on `app/`, static checks on the SPA, shellcheck, docker build + boot smoke test. Runs on every PR and push to `main`, and is reused by both deploy workflows. |
| `deploy-backend.yml` | After CI passes, `gcloud builds submit --config cloudbuild.yaml` → Cloud Run `epl-backend`, then curls `/health`. |
| `deploy-frontend.yml` | After CI passes, `firebase deploy --only hosting` from `frontend/` using the service account, then checks the site and the `/health` rewrite. |

Required repository settings:

- Secret `GCP_SA_KEY` — service-account JSON with roles: Cloud Build Editor,
  Cloud Run Admin, Service Account User, Artifact Registry Writer,
  Firebase Hosting Admin, Storage Admin (for Cloud Build source uploads).
- Optional variable `GCP_PROJECT_ID` (defaults to `epl-prediction-app`).
- An environment called `production` (add required reviewers there if you
  want a manual approval gate before deploys).
