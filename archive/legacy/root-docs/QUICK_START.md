# Quick Start Guide

Get EPL AI Pro running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- npm or yarn

## Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Install dependencies
pip install -e .

# 3. Set environment variables
export GOOGLE_API_KEY=your_google_ai_key_here

# 4. Run backend
uvicorn app.main:app --reload

# Backend running at http://localhost:8000
```

## Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Run frontend
npm run dev

# Frontend running at http://localhost:3000
```

## Verify Setup

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "models_loaded": false,
  "cache_available": true
}
```

### 2. Get Predictions

```bash
curl "http://localhost:8000/api/predictions?top_n=10"
```

### 3. View API Documentation

Open http://localhost:8000/docs in your browser.

### 4. Test Frontend

Open http://localhost:3000 in your browser.

## Next Steps

- [Local Development Guide](DEVELOPMENT.md) - Detailed development setup
- [API Documentation](API.md) - Complete API reference
- [Deployment Guide](DEPLOYMENT.md) - Deploy to production

## Common Issues

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -e ".[dev]"
```

### Frontend won't start

```bash
# Clear node_modules
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

### API connection fails

Check `NEXT_PUBLIC_API_URL` in frontend:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Support

- Issues: https://github.com/Logic06183/EPL_app/issues
- Docs: https://github.com/Logic06183/EPL_app/docs

---

*For detailed setup, see [INSTALLATION.md](INSTALLATION.md)*
