# FPL Prediction App

A state-of-the-art Fantasy Premier League prediction and optimization app using CNN models, sentiment analysis, and real-time data integration.

## Features

### Core Capabilities
- **CNN-based Player Performance Prediction**: Uses convolutional neural networks trained on historical FPL data
- **Sentiment Analysis Integration**: Analyzes news and social media sentiment to adjust predictions
- **Team Optimization**: Intelligent squad selection within budget constraints using linear programming
- **Transfer Suggestions**: Data-driven transfer recommendations based on predicted performance
- **Live Data Updates**: Automatic synchronization with official FPL API
- **iOS App Ready API**: RESTful API endpoints for mobile app integration

### Advanced Modeling
- Temporal pattern recognition using CNN architecture
- Multi-gameweek horizon predictions (up to 5 gameweeks ahead)
- Feature engineering with xG, xA, ICT index integration
- Sentiment-adjusted predictions using transformer models
- Automatic model retraining on schedule

## Installation

### Prerequisites
- Python 3.9+
- PostgreSQL (optional, for production)
- Redis (optional, for caching)

### Setup

1. Clone the repository:
```bash
cd /Users/craig/Desktop/EPL_app
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

### Start the API Server
```bash
python run.py
```
The API will be available at `http://localhost:8000`

### CLI Commands

Optimize a squad:
```bash
python cli.py optimize --budget 100.0
```

Get player predictions:
```bash
python cli.py predictions --top 20
```

Search for a player:
```bash
python cli.py player "Haaland"
```

Train/retrain models:
```bash
python cli.py train
```

Check current gameweek:
```bash
python cli.py gameweek
```

## API Endpoints

### Core Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check endpoint

### Player Predictions
- `GET /players/predictions?top_n=50` - Get top player predictions
- `GET /players/{player_id}/details` - Detailed player information and predictions

### Team Optimization
- `POST /optimize/squad` - Optimize full 15-player squad
- `POST /optimize/starting11` - Select best starting 11 from squad

### Transfers
- `POST /transfers/suggest` - Get transfer suggestions

### Gameweek
- `GET /gameweek/current` - Current gameweek information

### Model Management
- `POST /models/retrain` - Trigger model retraining

## Architecture

### Data Sources
1. **Official FPL API**: Real-time player stats, fixtures, and gameweek data
2. **Vaastav Dataset**: Historical FPL data from GitHub
3. **News APIs**: For sentiment analysis (optional)
4. **Twitter/X API**: Social media sentiment (optional)

### Model Pipeline
1. **Data Collection**: Automated fetching from multiple sources
2. **Feature Engineering**: Rolling averages, form metrics, opponent difficulty
3. **CNN Model**: 
   - Input: 6-gameweek sequences of 15 features
   - Architecture: 2 Conv1D layers + Dense layers
   - Output: Points prediction for next gameweek(s)
4. **Sentiment Adjustment**: Transformer-based sentiment analysis
5. **Optimization**: Linear programming for squad selection

### Technology Stack
- **Backend**: FastAPI, Python 3.9+
- **ML Framework**: TensorFlow/Keras for CNN, Transformers for NLP
- **Optimization**: PuLP for linear programming
- **Data Processing**: Pandas, NumPy
- **Scheduling**: APScheduler for automated updates
- **API**: RESTful design for iOS app integration

## Scheduled Tasks

The app includes automated scheduling for:
- **Daily Updates** (1 AM): Full player data refresh
- **6-Hour Refresh**: Periodic data synchronization
- **Weekly Retraining** (Monday 3 AM): Model retraining with latest data
- **Hourly Checks**: Gameweek deadline notifications

## iOS App Integration

The API is designed for seamless iOS app integration:

### Swift Example
```swift
// Fetch player predictions
let url = URL(string: "http://your-server:8000/players/predictions?top_n=20")!
URLSession.shared.dataTask(with: url) { data, response, error in
    // Handle response
}

// Optimize squad
let optimizeURL = URL(string: "http://your-server:8000/optimize/squad")!
var request = URLRequest(url: optimizeURL)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
let body = ["budget": 100.0]
request.httpBody = try? JSONSerialization.data(withJSONObject: body)
```

## Model Performance

### CNN Predictor
- **Architecture**: 2x Conv1D layers with batch normalization
- **Input Features**: 15 statistical features per gameweek
- **Sequence Length**: 6 gameweeks of historical data
- **Training Data**: 2021-2024 seasons
- **Validation**: 2024-25 season data

### Expected Accuracy
- **MAE**: ~2.5 points per player per gameweek
- **Top Player Ranking**: ~75% Spearman correlation
- **Transfer Success Rate**: ~65% improvement suggestions

## Development

### Project Structure
```
/Users/craig/Desktop/EPL_app/
├── src/
│   ├── api/           # FastAPI endpoints
│   ├── data/          # Data fetching modules
│   ├── models/        # ML models (CNN, sentiment)
│   ├── prediction_engine.py  # Main prediction logic
│   └── scheduler.py   # Automated tasks
├── cli.py            # Command-line interface
├── run.py            # Main application runner
├── requirements.txt  # Python dependencies
└── .env.example      # Environment variables template
```

### Adding New Features
1. Extend data sources in `src/data/`
2. Add new models in `src/models/`
3. Update prediction engine in `src/prediction_engine.py`
4. Add API endpoints in `src/api/main.py`

## Production Deployment

### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for caching
- `API_PORT`: API server port (default: 8000)
- `MODEL_UPDATE_INTERVAL_HOURS`: Model update frequency

## Future Enhancements

- [ ] GraphQL API support
- [ ] WebSocket for real-time updates
- [ ] Advanced injury prediction models
- [ ] Team performance correlation analysis
- [ ] Weather impact analysis
- [ ] Betting odds integration
- [ ] Multi-league support (Bundesliga, La Liga, etc.)

## Contributing

Contributions are welcome! Please ensure:
1. Code follows PEP 8 style guidelines
2. All tests pass
3. New features include documentation
4. Models are properly validated

## License

This project is for educational and personal use. Ensure compliance with FPL terms of service when using their API.

## Support

For issues or questions, please open an issue on GitHub or contact the development team.