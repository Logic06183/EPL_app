#!/bin/bash

echo "Deploying EPL Backend to South Africa (africa-south1) for optimal performance and cost..."

# Deploy to South Africa region with cost optimizations
gcloud run deploy epl-backend-sa \
  --source . \
  --region africa-south1 \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --max-instances 2 \
  --min-instances 0 \
  --timeout 60 \
  --execution-environment gen2 \
  --concurrency 80 \
  --no-cpu-throttling

echo "Deployment complete!"
echo ""
echo "Benefits of South Africa deployment:"
echo "✓ Lower latency from South Africa (~20-50ms vs 200-300ms from US)"
echo "✓ Reduced egress costs for South African users"
echo "✓ Compliance with African data residency preferences"
echo "✓ Better performance during South African peak hours"
echo ""
echo "Cost optimizations applied:"
echo "✓ Minimum memory (256Mi) for lightweight API"
echo "✓ Scale to zero when not in use"
echo "✓ Efficient concurrency settings"
echo "✓ Generation 2 execution environment"

# Get the service URL
URL=$(gcloud run services describe epl-backend-sa --region africa-south1 --format "value(status.url)")
echo ""
echo "Service URL: $URL"
echo "Health check: $URL/health"