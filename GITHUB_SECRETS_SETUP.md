# 🔐 GitHub Secrets Setup Guide

## Overview
Add these secrets to your GitHub repository to enable CI/CD automation.

---

## 📍 Where to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add each secret below

---

## 🔑 Required Secrets

### 1. FIREBASE_TOKEN

**What it is:** Authentication token for Firebase CLI

**How to get it:**
```bash
firebase login:ci
```

**What to copy:** The entire token output (looks like `1//0gxxxxxxxxx...`)

**Add to GitHub:**
- Name: `FIREBASE_TOKEN`
- Value: Paste the entire token

---

### 2. GCP_SA_KEY

**What it is:** Service account key for Google Cloud deployments

**Value:** Copy the ENTIRE JSON content from `github-actions-key.json`:

```json
{
  "type": "service_account",
  "project_id": "epl-prediction-app",
  "private_key_id": "3b8b993cf5fac2e5045f0844108362dd967e4785",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9cVsaxuYvMNsU\nRj0lQbt8bmwy8b/xziRoH3jdpoI1M2YSgMgpKoMHW+PYKK0nKHTjsG45tfFQWDnh\nYIL5kMRT7M9MsSRmF5d0S0QPHa+w58rkAPSZWQSYJ/Wj8xSedlG41RDTYxjhJsrH\nZtqTIHdpWyfoeBoYnbDMnGfl64TC2usl0p0pE5DiLgwT7IMAo7FuiEqK9864vgIA\nqD8k9d1MkLjqcbzSfq0fxPyfpX4nQRf9QZbKj5idbJ4f8UBYdPsizthq29r60U+k\nk3UYq1blPmBjBzOdrolExaFz312BHzRfNdlLL5D6oMkIL0M+8faH/tr6ij03mC6K\nqHZ7BvgPAgMBAAECggEAUYgPQyN2HrpCl2OxXi7/j0qA054a02k6Xvuoi5BlepsP\n44e8XYc31Dt2gGnlN7SgNfwRPFIzNLZ71qUwSVNGQ65n+2RDu5KMstbPyEeo/RSN\nS/qjSro2kXulKvXrmlVmz4sXjjqYkxIcdJwuFuMCsXuzXcgOxyha1ny79Iab4TYS\nRJ3xq7FvfNLb2ITfNv/Bx6LCCaAx8eISG9voxzUm8rIAtznG/63E8Rvnm6aru7wk\nU6HSMy0PkANEcvIQk+UjLij9E0CyxssDmNANRC/A7Y1x2+x9SM8ivLioAN2Q1HKP\nn1K8bLfZu8fAcWxPZLgawZCsT1u7tkrdfWZusAqwZQKBgQD9zETdsJAj802d6qH1\n+EZMOHR3v0/HHxQR8ncWJON72PbEYSJYy1+sDUe27sO5H3KK6EZeXHhCX+lTcFJ+\nfnre4rhW0RunKlw1ytcBZFEiQHD13b1sPQI91C7aL17xgvOK0LXIOco+90QMXBtK\nS4CGFl6S4SDT6hTsLVkpi/qtHQKBgQC/FiR7zAqE7H7dGxpivRGNPjRyR6GW5lp4\ngiG+L3keKDppEG7Jt+yFYdzMN/FmZdxNEbsOtOIs1pzL3JoVL3SB4igFccf0B/OU\nVgU02EV7yP2Ueg7G3LNcMPl8K6jKjI4cmV2ltcOZrGX6qCQjkEtUDBq6+hyoTigM\nq+t5gxGuGwKBgQC8sCVy/FXtpHHMOij3igIZoM9WR/G0BLMTNMS8vegyp3evQNgc\nU/dpHuZ2ZsU02OB7zXyjovP1xQDfe96ZFMec9co/IXABtEih5ZA8BK0dXfOdl6HA\n2wrTlPDQXe+kdstCJTFBD1YBwivhVIklj0Saa/8cDCwv4RR1ErH7ZYqVMQKBgBtg\n4s1SCNfOwsaPUZKAIHmqRf1xwfdK/f9yNb94MdReUzAmiJkiXyMlSGuCQHY5df0c\n4z5SMG3YOhMDgpgyenD5pF5TVSDj2sSQJqLRsfLwc1TIwEFB8fjtk3F1F/Qde2ch\nmkdZ6bKk/t+RI8xsqj5alaHgoCaFPDvEjjKU0v2tAoGAK9lpNiFzEfnKbj+seExF\nybx8Qx+s3e9dFaKxxpKXb7nQQfO0RKRX4iPO587Lw28CkBb9siopvcGUyo8zoATt\nuvc2/7gRHbTWfCmbaiXPBKSEBRzj6860G7OmWls8DrPAUNHcYHYw5oFtECvv7Lz2\nF9xvIpmYdXvZatwPTvLzHNY=\n-----END PRIVATE KEY-----\n",
  "client_email": "github-actions@epl-prediction-app.iam.gserviceaccount.com",
  "client_id": "115522947574977500175",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/github-actions%40epl-prediction-app.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

**Add to GitHub:**
- Name: `GCP_SA_KEY`
- Value: Paste the ENTIRE JSON (all of it!)

---

### 3. GOOGLE_API_KEY

**What it is:** Your Gemini AI API key

**How to get it:**
- Check your `.env` file OR
- Get from Google Cloud Console → APIs & Services → Credentials

**Add to GitHub:**
- Name: `GOOGLE_API_KEY`
- Value: Your API key (starts with `AIza...`)

---

### 4. NEWS_API_KEY (Optional)

**What it is:** News API key for sentiment analysis

**How to get it:**
- Sign up at https://newsapi.org

**Add to GitHub:**
- Name: `NEWS_API_KEY`
- Value: Your News API key

---

### 5. SPORTMONKS_API_KEY (Optional)

**What it is:** SportMonks API key for match data

**How to get it:**
- Sign up at https://sportmonks.com

**Add to GitHub:**
- Name: `SPORTMONKS_API_KEY`
- Value: Your SportMonks API key

---

## ✅ Verification Checklist

After adding all secrets, you should have:

- [ ] `FIREBASE_TOKEN` - Required for frontend deployment
- [ ] `GCP_SA_KEY` - Required for backend deployment
- [ ] `GOOGLE_API_KEY` - Required for Gemini AI features
- [ ] `NEWS_API_KEY` - Optional for sentiment analysis
- [ ] `SPORTMONKS_API_KEY` - Optional for match data

---

## 🧪 Test Your Setup

### Step 1: Commit and Push

```bash
git add .
git commit -m "ci: add GitHub Actions workflows"
git push origin main
```

### Step 2: Watch the Magic

1. Go to GitHub → Actions tab
2. You should see workflows running:
   - "Deploy Frontend to Firebase"
   - "Deploy Backend to Cloud Run"
   - "Test and Lint"

### Step 3: Verify Deployment

After ~3-5 minutes:
- **Frontend**: https://epl-prediction-app.web.app
- **Backend**: https://epl-backend-77913915885.us-central1.run.app

---

## 🔒 Security Best Practices

### DO:
✅ Add secrets through GitHub UI only
✅ Use different secrets for staging/production
✅ Rotate service account keys every 90 days
✅ Review GitHub Actions logs for secret leaks

### DON'T:
❌ Commit `github-actions-key.json` to git
❌ Share secrets in Slack/Discord
❌ Use production keys for testing
❌ Log secrets in code

---

## 🆘 Troubleshooting

### Error: "Permission denied"
**Fix:** Verify `GCP_SA_KEY` is the full JSON, including `{` and `}`

### Error: "Unauthorized" (Firebase)
**Fix:** Run `firebase login:ci` again to get a fresh token

### Error: "Invalid credentials"
**Fix:** Check that secret names match exactly (case-sensitive!)

### Workflow doesn't trigger
**Fix:**
- Check workflow is in `.github/workflows/`
- Verify you pushed to `main` branch
- Check workflow `paths` filter matches changed files

---

## 📞 Quick Help

### View workflow logs:
1. GitHub → Actions tab
2. Click on workflow run
3. Click on job name
4. Expand steps to see detailed logs

### Test locally before pushing:
```bash
# Test frontend build
cd frontend && npm run build

# Test backend can start
python enhanced_api_production.py
```

---

## 🎯 Next Steps

Once secrets are added and workflows run successfully:

1. ✅ Every push to `main` auto-deploys
2. ✅ PRs show deployment preview (optional)
3. ✅ Failed deployments notify you
4. ✅ Rollback is one click away

---

## 🎉 You're Done!

Your CI/CD pipeline is now:
- ✅ Automated
- ✅ Tested
- ✅ Secure
- ✅ Production-ready

**Just push to main and let GitHub Actions handle the rest!** 🚀

---

*Generated for EPL AI Pro - November 23, 2025*
*Keep this file secure - it contains sensitive information!*
