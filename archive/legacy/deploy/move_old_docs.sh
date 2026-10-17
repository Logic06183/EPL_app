#!/bin/bash
# Consolidate old documentation files
echo "📚 Consolidating documentation..."

mkdir -p ../archive/old_docs

# Move deployment guides (consolidated into docs/DEPLOYMENT.md)
mv ../DEPLOYMENT_*.md ../archive/old_docs/ 2>/dev/null
mv ../FIREBASE_DEPLOYMENT_GUIDE.md ../archive/old_docs/ 2>/dev/null

# Move setup guides (consolidated into docs/INSTALLATION.md)
mv ../LOCAL_SETUP.md ../archive/old_docs/ 2>/dev/null
mv ../PAYSTACK_SETUP_GUIDE.md ../archive/old_docs/ 2>/dev/null
mv ../SPORTMONKS_SETUP.md ../archive/old_docs/ 2>/dev/null

# Move CI/CD guides (consolidated into docs/CICD.md)
mv ../CICD_SETUP_GUIDE.md ../archive/old_docs/ 2>/dev/null
mv ../GITHUB_SECRETS_SETUP.md ../archive/old_docs/ 2>/dev/null

# Move testing docs
mv ../TESTING_*.md ../archive/old_docs/ 2>/dev/null

# Move project summaries (keep for reference but move to archive)
mv ../PROJECT_SUMMARY.md ../archive/old_docs/ 2>/dev/null
mv ../QUICK_START_GUIDE.md ../archive/old_docs/ 2>/dev/null

echo "✅ Documentation consolidated!"
echo "Old docs archived in: archive/old_docs/"
echo "New docs in: docs/"
