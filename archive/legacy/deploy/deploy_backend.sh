#!/bin/bash

# Deploy backend to Cloud Run using Firebase

echo "Deploying EPL Backend to Cloud Run..."

# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

echo "Backend deployment complete!"
echo "Get the Cloud Run URL with: gcloud run services describe epl-backend --region us-central1 --format 'value(status.url)'"