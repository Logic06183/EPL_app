#!/bin/bash

# FPL AI Pro - Firebase Deployment Script
echo "🔥 Deploying FPL AI Pro to Firebase..."

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo -e "${RED}❌ Firebase CLI not found. Installing...${NC}"
    npm install -g firebase-tools
fi

# Login to Firebase (if not already logged in)
echo -e "${BLUE}🔐 Checking Firebase authentication...${NC}"
if ! firebase projects:list &> /dev/null; then
    echo -e "${YELLOW}⚠️  Please login to Firebase${NC}"
    firebase login
fi

# List projects to confirm access
echo -e "${BLUE}📋 Available Firebase projects:${NC}"
firebase projects:list

# Check if project exists
echo -e "${BLUE}🔍 Checking project configuration...${NC}"
if firebase use --help &> /dev/null; then
    echo -e "${GREEN}✅ Firebase CLI ready${NC}"
else
    echo -e "${RED}❌ Firebase CLI setup failed${NC}"
    exit 1
fi

# Build frontend
echo -e "${BLUE}🏗️  Building frontend...${NC}"
cd frontend
npm run build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend build successful${NC}"
else
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi
cd ..

# Prepare API files for functions
echo -e "${BLUE}📦 Preparing functions...${NC}"
cp api_production.py functions/
cp sportmonks_integration.py functions/ 2>/dev/null || echo "⚠️  SportMonks integration not found"
cp paystack_integration.py functions/ 2>/dev/null || echo "⚠️  PayStack integration not found"
cp news_sentiment_analyzer.py functions/ 2>/dev/null || echo "⚠️  News sentiment analyzer not found"

# Initialize Firebase (if not done)
if [ ! -f ".firebaserc" ]; then
    echo -e "${YELLOW}🚀 Initializing Firebase project...${NC}"
    firebase init
else
    echo -e "${GREEN}✅ Firebase already initialized${NC}"
fi

# Deploy to Firebase
echo -e "${BLUE}🚀 Deploying to Firebase...${NC}"

# Deploy hosting first
echo -e "${BLUE}🌐 Deploying frontend...${NC}"
firebase deploy --only hosting

# Deploy functions
echo -e "${BLUE}⚡ Deploying functions...${NC}"
firebase deploy --only functions

# Get deployment URLs
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}🌍 Your app is now live at:${NC}"
firebase hosting:channel:open live

echo ""
echo -e "${BLUE}📱 Access your app:${NC}"
echo "Frontend: https://fpl-ai-pro.web.app"
echo "API: https://fpl-ai-pro.web.app/api"
echo "Docs: https://fpl-ai-pro.web.app/api/docs"

echo ""
echo -e "${BLUE}🔧 Next steps:${NC}"
echo "1. Test all features on the live site"
echo "2. Configure custom domain (optional)"
echo "3. Set up monitoring and analytics"
echo "4. Add production PayStack keys when compliance is approved"

echo ""
echo -e "${GREEN}🎉 FPL AI Pro is now deployed to Firebase!${NC}"