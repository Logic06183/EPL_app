# 🚀 CI/CD Setup Guide - GitHub Actions

## Overview
Automated deployment pipeline for the EPL Prediction App using GitHub Actions. Deploys frontend to Firebase Hosting and backend to Google Cloud Run on every push to main.

---

## 📋 Prerequisites

### 1. GitHub Repository
- Repository must be connected to your project
- Admin access to configure secrets

### 2. Firebase Setup
```bash
# Get Firebase token
firebase login:ci

# This will output a token like:
# 1//0xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Google Cloud Service Account

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployment"

# Grant necessary roles
gcloud projects add-iam-policy-binding epl-prediction-app \
  --member="serviceAccount:github-actions@epl-prediction-app.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding epl-prediction-app \
  --member="serviceAccount:github-actions@epl-prediction-app.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding epl-prediction-app \
  --member="serviceAccount:github-actions@epl-prediction-app.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@epl-prediction-app.iam.gserviceaccount.com

# This creates github-actions-key.json - keep it safe!
```

---

## 🔐 GitHub Secrets Configuration

Go to: **Repository → Settings → Secrets and variables → Actions**

### Required Secrets:

| Secret Name | Description | How to Get |
|------------|-------------|-----------|
| `FIREBASE_TOKEN` | Firebase CI token | Run `firebase login:ci` |
| `GCP_SA_KEY` | Service account JSON | Contents of `github-actions-key.json` |
| `GOOGLE_API_KEY` | Gemini AI API key | From Google Cloud Console |
| `NEWS_API_KEY` | News API key | From newsapi.org |
| `SPORTMONKS_API_KEY` | SportMonks API key | From sportmonks.com |
| `API_URL` | Backend URL (optional) | `https://epl-backend-77913915885.us-central1.run.app` |

### Adding Secrets:

1. Click **"New repository secret"**
2. Enter **Name** (e.g., `FIREBASE_TOKEN`)
3. Paste the **Value**
4. Click **"Add secret"**

---

## 📁 Workflow Files

The CI/CD pipeline consists of 3 workflows:

### 1. **deploy-frontend.yml**
- Triggers: Push to `main` (frontend files changed)
- Actions:
  - Checkout code
  - Install Node.js dependencies
  - Build Next.js app
  - Deploy to Firebase Hosting
  - Test deployment

### 2. **deploy-backend.yml**
- Triggers: Push to `main` (Python files changed)
- Actions:
  - Checkout code
  - Authenticate to Google Cloud
  - Deploy to Cloud Run
  - Test API health
  - Verify endpoints

### 3. **test-and-lint.yml**
- Triggers: Push/PR to `main` or `develop`
- Actions:
  - Lint frontend (ESLint)
  - Lint backend (flake8, black)
  - Run tests
  - Security scan (Trivy)

---

## 🔄 Deployment Flow

### Automatic Deployment (Recommended)

```bash
# Make changes
git add .
git commit -m "feat: add new prediction model"
git push origin main

# GitHub Actions automatically:
# 1. Runs tests and linting
# 2. Builds frontend/backend
# 3. Deploys to production
# 4. Runs post-deployment tests
```

### Manual Deployment

1. Go to **Actions** tab in GitHub
2. Select workflow (e.g., "Deploy Frontend")
3. Click **"Run workflow"**
4. Select branch (e.g., `main`)
5. Click **"Run workflow"**

---

## 🧪 Testing Workflow

### Run Tests Locally

**Frontend:**
```bash
cd frontend
npm run lint
npm run build
```

**Backend:**
```bash
pip install flake8 black pytest
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
black --check .
pytest tests/ -v
```

### What Gets Tested in CI

✅ **Code Quality:**
- ESLint for JavaScript/React
- flake8 for Python syntax
- black for Python formatting

✅ **Build:**
- Frontend builds successfully
- No TypeScript errors

✅ **Security:**
- Trivy scans for vulnerabilities
- Dependency audits

✅ **Functionality:**
- API health checks
- Endpoint response validation

---

## 📊 Monitoring Deployments

### GitHub Actions UI

1. Go to **Actions** tab
2. Click on workflow run
3. View logs for each step
4. Check for errors (red X) or success (green checkmark)

### Deployment URLs

After successful deployment:
- **Frontend**: Check workflow logs for `https://epl-prediction-app.web.app`
- **Backend**: Check logs for Cloud Run URL

### Notifications

GitHub Actions will:
- ✅ Comment on PRs with deployment URLs
- ❌ Fail workflow if tests fail
- 📧 Email on workflow failure (if configured)

---

## 🛠️ Troubleshooting

### Issue: Firebase deployment fails

**Error:** `Error: HTTP Error: 401, Unauthorized`

**Solution:**
```bash
# Regenerate Firebase token
firebase login:ci

# Update FIREBASE_TOKEN secret in GitHub
```

### Issue: Cloud Run deployment fails

**Error:** `Permission denied`

**Solution:**
- Verify service account has required roles
- Check `GCP_SA_KEY` secret is correct JSON
- Ensure Cloud Run API is enabled:
  ```bash
  gcloud services enable run.googleapis.com --project epl-prediction-app
  ```

### Issue: Build fails

**Error:** `npm ERR! 404 Not Found`

**Solution:**
- Check `package-lock.json` is committed
- Run `npm install` locally to regenerate
- Commit and push

### Issue: Environment variables not working

**Solution:**
- Verify secrets are added in GitHub
- Check secret names match workflow file
- Secrets are case-sensitive!

---

## 🔒 Security Best Practices

### 1. Never Commit Secrets

```bash
# Add to .gitignore
echo "github-actions-key.json" >> .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

### 2. Use Minimal Permissions

- Service accounts should have only necessary roles
- Review IAM permissions regularly
- Rotate keys every 90 days

### 3. Enable Branch Protection

Repository Settings → Branches → Add rule:
- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Require branches to be up to date

### 4. Audit Logs

- Review GitHub Actions logs regularly
- Monitor Google Cloud audit logs
- Set up alerts for unauthorized deployments

---

## 📈 Advanced Configuration

### Deploy to Staging First

Create `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy to Staging

on:
  push:
    branches:
      - develop

# ... similar to production but different project
```

### Rollback on Failure

Add to backend workflow:

```yaml
      - name: Rollback on failure
        if: failure()
        run: |
          gcloud run services update-traffic ${{ env.SERVICE_NAME }} \
            --to-revisions=PREVIOUS_REVISION=100 \
            --region ${{ env.REGION }}
```

### Slack Notifications

Add Slack webhook secret and:

```yaml
      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 📝 Workflow Customization

### Change Deployment Trigger

Only deploy on tags:

```yaml
on:
  push:
    tags:
      - 'v*'  # Trigger on version tags like v1.0.0
```

### Add Manual Approval

```yaml
jobs:
  approval:
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - name: Wait for approval
        run: echo "Deployment approved"

  deploy:
    needs: approval
    # ... deployment steps
```

### Deploy Specific Services

```yaml
on:
  push:
    paths:
      - 'frontend/**'  # Only trigger if frontend changes
```

---

## ✅ Verification Checklist

Before pushing to production:

- [ ] All secrets configured in GitHub
- [ ] Service account has correct permissions
- [ ] Workflows tested on feature branch
- [ ] Environment variables set correctly
- [ ] Firebase project ID is correct
- [ ] Cloud Run region is correct
- [ ] Tests passing locally
- [ ] Branch protection enabled

---

## 🚀 Quick Start

### 1. Add Secrets to GitHub

```bash
# Get Firebase token
firebase login:ci
# Copy output and add as FIREBASE_TOKEN secret

# Create GCP service account key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@epl-prediction-app.iam.gserviceaccount.com
# Copy contents of key.json and add as GCP_SA_KEY secret

# Add API keys
# Add GOOGLE_API_KEY, NEWS_API_KEY, SPORTMONKS_API_KEY
```

### 2. Commit Workflow Files

```bash
git add .github/workflows/
git commit -m "ci: add GitHub Actions workflows"
git push origin main
```

### 3. Monitor First Deployment

1. Go to GitHub → Actions
2. Watch workflows execute
3. Verify deployment success
4. Test live URLs

---

## 🎯 Cost Optimization

### GitHub Actions

- **Free tier**: 2,000 minutes/month
- **Private repos**: Uses minutes
- **Public repos**: Unlimited minutes

### Strategies:

1. **Cache dependencies**:
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.npm
       key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
   ```

2. **Run only on changes**:
   ```yaml
   paths:
     - 'frontend/**'  # Only frontend files
   ```

3. **Use matrix builds** for testing multiple versions

---

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Firebase CI/CD](https://firebase.google.com/docs/hosting/github-integration)
- [Cloud Run CI/CD](https://cloud.google.com/run/docs/continuous-deployment-with-github-actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## 🎉 Success!

Your CI/CD pipeline is now configured! Every push to `main` will automatically:

1. ✅ Run tests and linting
2. ✅ Build frontend and backend
3. ✅ Deploy to production
4. ✅ Verify deployments
5. ✅ Notify on failures

**Happy deploying!** 🚀

---

*Generated for EPL AI Pro - November 23, 2025*
