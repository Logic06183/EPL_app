# Proposed workflow updates

The Claude GitHub App can't push to `.github/workflows/` (no `workflows`
permission), so these are parked here. Copy them over the files in
`.github/workflows/` (and delete this folder) to apply:

- `test-and-lint.yml`: ruff + pytest on the live app only. The current one
  lints/tests deleted legacy code and installs tensorflow/torch; it can't pass.
- `deploy-backend.yml`: runs tests first, and uses `--update-env-vars`.
  **The current one uses `--set-env-vars`, which wipes PAYFAST_* and
  LAUNCH_FREE_UNTIL from the Cloud Run service on every deploy.**
- `deploy-frontend.yml`: deploys the static `frontend/` directly. The current
  one runs a Next.js build that no longer exists.
