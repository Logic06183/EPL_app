# Google Cloud Run Deployment Skill

## Description
Deploy Python/FastAPI applications to Google Cloud Run with automatic scaling, containerization, and environment variable management.

## Use Cases
- Deploy FastAPI/Flask backends to Cloud Run
- Set up serverless Python ML applications
- Configure auto-scaling and resource limits
- Manage environment variables and secrets

## Prerequisites
- Google Cloud SDK installed (`gcloud` CLI)
- Google Cloud project created
- Cloud Run API enabled
- Docker installed (optional - Cloud Run can build from source)
- Service account with proper permissions

## Steps

### 1. Project Setup

```bash
# Login to Google Cloud
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Prepare Application

Ensure you have a `requirements.txt` or `Dockerfile`:

**Option A: Using Buildpacks (Automatic)**
```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
httpx==0.25.1
# ... other dependencies
```

**Option B: Custom Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec uvicorn enhanced_api_production:app --host 0.0.0.0 --port $PORT
```

### 3. Deploy to Cloud Run

**Deploy from Source (Recommended):**
```bash
gcloud run deploy SERVICE_NAME \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout=300 \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --set-env-vars="GOOGLE_API_KEY=${GOOGLE_API_KEY},NEWS_API_KEY=${NEWS_API_KEY}"
```

**Deploy from Docker Image:**
```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/SERVICE_NAME

# Deploy
gcloud run deploy SERVICE_NAME \
  --image gcr.io/PROJECT_ID/SERVICE_NAME \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### 4. Configure Environment Variables

**Set environment variables:**
```bash
gcloud run services update SERVICE_NAME \
  --region us-central1 \
  --set-env-vars="GOOGLE_API_KEY=your_key,API_ENV=production"
```

**Use Secret Manager (Recommended for sensitive data):**
```bash
# Create secret
echo -n "your_api_key" | gcloud secrets create API_KEY --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding API_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with secret
gcloud run deploy SERVICE_NAME \
  --set-secrets="GOOGLE_API_KEY=API_KEY:latest"
```

### 5. Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=SERVICE_NAME \
  --domain=api.yourdomain.com \
  --region=us-central1

# Note: Update DNS records as instructed
```

## Resource Configuration

### Memory and CPU

```bash
# Standard (1 vCPU, 512Mi RAM)
--memory=512Mi --cpu=1

# Medium (2 vCPU, 2Gi RAM) - Good for ML apps
--memory=2Gi --cpu=2

# Large (4 vCPU, 8Gi RAM)
--memory=8Gi --cpu=4
```

### Auto-scaling

```bash
# Set min/max instances
gcloud run services update SERVICE_NAME \
  --min-instances=1 \
  --max-instances=10 \
  --region=us-central1

# Set concurrency (requests per container)
--concurrency=80  # Default is 80
```

### Timeout

```bash
# Set timeout (max 3600 seconds / 1 hour)
--timeout=300  # 5 minutes
```

## Verification

After deployment:

```bash
# Get service URL
gcloud run services describe SERVICE_NAME \
  --region=us-central1 \
  --format='value(status.url)'

# Test the endpoint
curl https://SERVICE_NAME-PROJECT_ID.run.app

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" \
  --limit 50 \
  --format="table(timestamp,textPayload)"
```

## Common Issues

### Issue: Container fails to start
**Solution**:
- Check logs: `gcloud logging read ...`
- Ensure app listens on `$PORT` environment variable
- Verify all dependencies in requirements.txt

### Issue: Timeout errors
**Solution**:
- Increase timeout: `--timeout=600`
- Optimize cold start (reduce dependencies, lazy load ML models)
- Increase memory/CPU

### Issue: Out of memory
**Solution**:
- Increase memory: `--memory=4Gi`
- Optimize code (release unused objects)
- Use streaming for large responses

### Issue: Permission denied
**Solution**:
```bash
# Grant invoker role for public access
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=us-central1
```

## Environment Variables Reference

Common environment variables for ML apps:

```bash
--set-env-vars="
  GOOGLE_API_KEY=${GOOGLE_API_KEY},
  NEWS_API_KEY=${NEWS_API_KEY},
  SPORTMONKS_API_KEY=${SPORTMONKS_API_KEY},
  PAYSTACK_SECRET_KEY=${PAYSTACK_SECRET_KEY},
  API_ENV=production,
  LOG_LEVEL=INFO
"
```

## Performance Optimization

### 1. Cold Start Optimization

```python
# Lazy load heavy dependencies
@app.on_event("startup")
async def startup_event():
    # Load ML models here
    global model
    model = load_model()

# Use lighter dependencies
# Minimize import time
```

### 2. Container Optimization

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 3. Caching

- Use min-instances=1 for always-warm containers
- Implement in-memory caching (TTLCache)
- Use Cloud Memorystore for distributed caching

## Monitoring and Logging

### View Logs

```bash
# Real-time logs
gcloud logging tail "resource.type=cloud_run_revision"

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 100
```

### Set up Monitoring

1. Cloud Monitoring Console: https://console.cloud.google.com/monitoring
2. Create alerts for:
   - Error rates > 5%
   - Latency > 1 second
   - Instance count > 8

### Metrics to Track

- Request count
- Request latency (p50, p95, p99)
- Error rate
- Container instance count
- CPU utilization
- Memory utilization

## Cost Optimization

### Pricing Model

Cloud Run charges for:
- CPU and memory while handling requests
- Number of requests
- Network egress

### Optimization Strategies

1. **Use minimum resources needed:**
   ```bash
   --memory=512Mi --cpu=1  # Start small, scale up if needed
   ```

2. **Set appropriate max-instances:**
   ```bash
   --max-instances=5  # Prevent runaway costs
   ```

3. **Use Free Tier:**
   - 2 million requests/month free
   - 360,000 GB-seconds memory free
   - 180,000 vCPU-seconds free

4. **Optimize cold starts:**
   - Reduce dependencies
   - Use min-instances sparingly (costs $$$)

## Rollback Procedure

```bash
# List revisions
gcloud run revisions list --service=SERVICE_NAME --region=us-central1

# Route traffic to previous revision
gcloud run services update-traffic SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1
```

## CI/CD Integration

Cloud Run works seamlessly with:
- GitHub Actions
- Cloud Build
- GitLab CI
- CircleCI

See GitHub Actions workflow for automated deployments.

## Quick Commands

```bash
# Deploy
gcloud run deploy SERVICE_NAME --source . --region us-central1

# Update env vars
gcloud run services update SERVICE_NAME --set-env-vars="KEY=value"

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Get service URL
gcloud run services describe SERVICE_NAME --format='value(status.url)'

# Delete service
gcloud run services delete SERVICE_NAME --region=us-central1

# List all services
gcloud run services list
```

## Security Best Practices

1. **Use Secret Manager** for sensitive data
2. **Enable VPC connector** for private resources
3. **Implement authentication** (Cloud IAM, JWT)
4. **Set up CORS** properly
5. **Use HTTPS only** (automatic with Cloud Run)
6. **Limit max-instances** to prevent abuse
7. **Enable Cloud Armor** for DDoS protection

## Service Account Permissions

Required IAM roles:
- `roles/run.admin` - Deploy services
- `roles/iam.serviceAccountUser` - Act as service account
- `roles/cloudbuild.builds.builder` - Build containers
- `roles/secretmanager.secretAccessor` - Access secrets

## Support Resources

- Cloud Run Documentation: https://cloud.google.com/run/docs
- Pricing Calculator: https://cloud.google.com/products/calculator
- Quickstarts: https://cloud.google.com/run/docs/quickstarts
- Best Practices: https://cloud.google.com/run/docs/best-practices

## Advanced Features

### VPC Connector
```bash
# For private database access
gcloud run services update SERVICE_NAME \
  --vpc-connector=CONNECTOR_NAME \
  --region=us-central1
```

### Cloud SQL Connection
```bash
gcloud run services update SERVICE_NAME \
  --add-cloudsql-instances=PROJECT:REGION:INSTANCE \
  --region=us-central1
```

### Custom Service Account
```bash
gcloud run services update SERVICE_NAME \
  --service-account=SA_NAME@PROJECT.iam.gserviceaccount.com \
  --region=us-central1
```
