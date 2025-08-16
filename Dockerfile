# Dockerfile for FPL AI Pro API deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_firebase.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY api_production.py .
COPY sportmonks_integration.py .
COPY paystack_integration.py .
COPY news_sentiment_analyzer.py .
COPY multi_model_predictor.py .

# Set environment variables for production
ENV NEWS_API_KEY=e36350769b6341bb81b832a84442e6ad
ENV PAYSTACK_PUBLIC_KEY=pk_test_0f6e3092te89f0f4ad18268d1f3884258afc37bc
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "uvicorn", "api_production:app", "--host", "0.0.0.0", "--port", "8080"]