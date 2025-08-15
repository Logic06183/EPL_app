FROM python:3.9-slim

WORKDIR /app

# Copy AI requirements
COPY requirements_ai_simple.txt .
RUN pip install --no-cache-dir -r requirements_ai_simple.txt

# Copy the enhanced API
COPY api_enhanced_final.py .

ENV PORT=8080

EXPOSE 8080

CMD exec uvicorn api_enhanced_final:app --host 0.0.0.0 --port $PORT