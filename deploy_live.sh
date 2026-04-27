#!/bin/bash

# FPL Prediction App - Complete Deployment Script
# Deploys backend to Cloud Run and frontend to Firebase Hosting

set -e

echo "🚀 FPL Prediction App - Live Deployment"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ID="epl-prediction-app"
REGION="us-central1"
SERVICE_NAME="epl-api"

# Step 1: Check prerequisites
echo -e "${BLUE}📋 Step 1: Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}⚠️  Firebase CLI not found. Installing...${NC}"
    npm install -g firebase-tools
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

# Step 2: Authenticate
echo -e "${BLUE}📋 Step 2: Authenticating with Google Cloud...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"
echo ""

# Step 3: Build and Deploy Backend to Cloud Run
echo -e "${BLUE}📋 Step 3: Building and deploying backend API...${NC}"
echo "This may take 5-10 minutes..."

# Build Docker image
echo "Building Docker image..."
gcloud builds submit \
    --config cloudbuild.yaml \
    --project $PROJECT_ID

echo -e "${GREEN}✅ Backend deployed to Cloud Run${NC}"
echo ""

# Get the Cloud Run service URL
echo "Getting Cloud Run service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format 'value(status.url)' \
    --project $PROJECT_ID)

echo -e "${GREEN}✅ Backend API URL: $SERVICE_URL${NC}"
echo ""

# Step 4: Test the backend
echo -e "${BLUE}📋 Step 4: Testing backend API...${NC}"
sleep 5  # Wait for service to be ready

if curl -s "${SERVICE_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "Check Cloud Run logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
    exit 1
fi
echo ""

# Step 5: Deploy Frontend to Firebase Hosting
echo -e "${BLUE}📋 Step 5: Deploying frontend to Firebase Hosting...${NC}"

# Login to Firebase if needed
firebase login --reauth

# Deploy to Firebase Hosting
firebase deploy --only hosting --project $PROJECT_ID

echo -e "${GREEN}✅ Frontend deployed to Firebase Hosting${NC}"
echo ""

# Step 6: Show deployment info
echo ""
echo "================================================"
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo "================================================"
echo ""
echo -e "${BLUE}📱 Your Live URLs:${NC}"
echo ""
echo "Frontend:"
echo "  https://epl-prediction-app.web.app"
echo "  https://epl-prediction-app.firebaseapp.com"
echo ""
echo "Backend API:"
echo "  $SERVICE_URL"
echo ""
echo -e "${BLUE}🔍 Test Your App:${NC}"
echo "1. Visit https://epl-prediction-app.web.app"
echo "2. Click 'Get Predictions' - should show real FPL players"
echo "3. Try 'Optimize Squad' - should build a 15-player team"
echo "4. Check Gameweek Info - should show current gameweek"
echo ""
echo -e "${BLUE}📊 Monitoring:${NC}"
echo "Cloud Run Logs:"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION --project $PROJECT_ID"
echo ""
echo "Firebase Hosting:"
echo "  https://console.firebase.google.com/project/$PROJECT_ID/hosting"
echo ""
echo -e "${BLUE}🔄 To Redeploy:${NC}"
echo "Backend only: gcloud builds submit --config cloudbuild.yaml"
echo "Frontend only: firebase deploy --only hosting"
echo "Both: ./deploy_live.sh"
echo ""
echo -e "${GREEN}✨ Your FPL Prediction App is now LIVE!${NC}"
