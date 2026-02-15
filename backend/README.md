# FPL AI Pro - Backend

Production-ready FastAPI backend for Fantasy Premier League predictions with multi-model AI and advanced analytics.

## Features

- **Multi-Model Predictions**: RandomForest + CNN + Gemini AI ensemble
- **Advanced Analytics**: xG (Expected Goals), xA (Expected Assists), ICT Index
- **Team Optimization**: Linear programming-based squad selection
- **Transfer Suggestions**: AI-powered transfer recommendations
- **Real-time Data**: Official FPL API integration
- **High Performance**: Async processing, intelligent caching
- **Production Ready**: Comprehensive error handling, logging, monitoring

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Installation

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -e .

# Or install with all extras
pip install -e ".[all]"

# Copy environment template
cp ../.env.example .env

# Edit .env with your configuration
nano .env
```

### Configuration

Required environment variables:

```env
# Google AI (for Gemini predictions)
GOOGLE_API_KEY=your_google_ai_key_here

# Optional
NEWS_API_KEY=your_news_api_key
SPORTMONKS_API_KEY=your_sportmonks_key
PAYSTACK_SECRET_KEY=your_paystack_key
REDIS_URL=redis://localhost:6379
```

### Running Locally

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access the API:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Docker

### Build and Run

```bash
# Build image
docker build -t fpl-ai-pro-backend .

# Run container
docker run -p 8000:8000 --env-file .env fpl-ai-pro-backend

# Or use docker-compose
docker-compose up backend
```

## API Endpoints

### Health & Info

- `GET /` - API information
- `GET /health` - Health check
- `GET /ping` - Lightweight ping

### Players

- `GET /api/players` - Get all players (with filters)
- `GET /api/players/{id}` - Get player details
- `GET /api/players/search/{query}` - Search players
- `GET /api/players/{id}/history` - Player history

### Predictions

- `GET /api/predictions` - Get predictions (top N players)
- `GET /api/predictions/enhanced` - Enhanced with Gemini AI
- `GET /api/predictions/{player_id}` - Single player prediction
- `GET /api/predictions/models/info` - Model information
- `POST /api/predictions/models/retrain` - Trigger retraining

### Teams

- `POST /api/teams/optimize` - Optimize fantasy team
- `POST /api/teams/transfers` - Get transfer suggestions
- `GET /api/teams/formations` - Valid formations

### Payments

- `GET /api/payments/plans` - Subscription plans
- `POST /api/payments/initialize` - Initialize payment
- `POST /api/payments/verify/{ref}` - Verify payment

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── api/                 # API routes
│   │   ├── players.py
│   │   ├── predictions.py
│   │   ├── teams.py
│   │   └── payments.py
│   ├── services/            # Business logic
│   │   ├── data_service.py
│   │   ├── prediction_service.py
│   │   └── team_service.py
│   ├── models/              # ML models
│   ├── schemas/             # Pydantic models
│   │   ├── common.py
│   │   ├── player.py
│   │   └── team.py
│   └── utils/               # Utilities
│       ├── logging.py
│       └── cache.py
├── tests/                   # Tests
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Code Quality

```bash
# Format code
black app/

# Lint code
ruff check app/

# Type check
mypy app/

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## ML Models

### Random Forest
- **Trees**: 200
- **Features**: 24 (including xG, xA, ICT)
- **Accuracy**: 75-80%
- **Training**: Auto-trains on first request

### Features Used
```python
[
    "price", "total_points", "form", "ownership", "minutes",
    "goals", "assists", "clean_sheets", "goals_conceded",
    "influence", "creativity", "threat", "ict_index",
    "position", "transfers_balance",
    "expected_goals", "expected_assists", "expected_goal_involvements",
    "expected_goals_conceded", "expected_goals_per_90",
    "expected_assists_per_90", "bps", "saves", "bonus"
]
```

### Gemini AI Integration
- Context-aware analysis
- xG/xA overperformance detection
- Hidden gem identification
- Transfer reasoning

## Deployment

### Google Cloud Run

```bash
# Deploy to Cloud Run
gcloud run deploy fpl-ai-pro-backend \
    --source . \
    --region us-central1 \
    --platform managed \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --allow-unauthenticated
```

### Firebase Cloud Functions

```bash
# Deploy to Firebase
firebase deploy --only functions
```

### Environment Variables

Set in Cloud Run / Cloud Functions:
- `GOOGLE_API_KEY`
- `NEWS_API_KEY` (optional)
- `SPORTMONKS_API_KEY` (optional)
- `PAYSTACK_SECRET_KEY` (optional)
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`

## Monitoring

### Logging

Structured JSON logging for production:

```json
{
    "timestamp": "2024-02-15T12:00:00Z",
    "level": "INFO",
    "logger": "app.services.prediction",
    "message": "Model trained successfully",
    "module": "prediction_service",
    "function": "train_model"
}
```

### Health Check

```bash
# Check health
curl http://localhost:8000/health

# Response
{
    "status": "healthy",
    "version": "3.0.0",
    "timestamp": "2024-02-15T12:00:00Z",
    "models_loaded": true,
    "cache_available": true
}
```

## Performance

- **Response Time**: < 200ms (p95)
- **Concurrent Requests**: 100+
- **Cache Hit Rate**: > 80%
- **Memory Usage**: ~500MB (baseline)

## Troubleshooting

### Common Issues

**Models not loading:**
```bash
# Check if models directory exists
ls -la models/

# Retrain models
curl -X POST http://localhost:8000/api/predictions/models/retrain
```

**Slow responses:**
```bash
# Check cache
curl http://localhost:8000/debug/cache

# Clear cache
curl -X POST http://localhost:8000/debug/clear-cache
```

**Import errors:**
```bash
# Reinstall dependencies
pip install -e ".[all]" --force-reinstall
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: https://github.com/Logic06183/EPL_app/issues
- Documentation: https://github.com/Logic06183/EPL_app#readme

---

Built with ❤️ using FastAPI, scikit-learn, and Google Gemini AI
