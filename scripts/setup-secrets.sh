#!/usr/bin/env bash
# One-time GCP setup for the API: Artifact Registry repo + Secret Manager secrets,
# and grant the Cloud Run runtime service account access to them.
#
# Usage: PROJECT_ID=epl-prediction-app ./scripts/setup-secrets.sh
# Values are read interactively (never pass secrets as CLI arguments).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-epl-prediction-app}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-epl}"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com

if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for name in google-api-key payfast-merchant-id payfast-merchant-key payfast-passphrase; do
  read -r -s -p "Value for ${name} (leave blank to skip): " value
  echo
  if [[ -z "$value" ]]; then
    continue
  fi
  if ! gcloud secrets describe "$name" >/dev/null 2>&1; then
    gcloud secrets create "$name" --replication-policy=automatic
  fi
  printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
  gcloud secrets add-iam-policy-binding "$name" \
    --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor >/dev/null
done

echo "Done. Deploy with: gcloud builds submit --config cloudbuild.yaml"
