FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_gemini.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_gemini.txt

# Copy application code
COPY enhanced_api_production.py .
COPY gemini_integration.py .
COPY sportmonks_integration.py .
COPY paystack_integration.py .
COPY news_sentiment_analyzer.py .

# Copy trained models
COPY models/ ./models/

# No non-root user for now to avoid permission issues

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "enhanced_api_production.py"]