# Use Python slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_local.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_local.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.local_main:app", "--host", "0.0.0.0", "--port", "8000"]