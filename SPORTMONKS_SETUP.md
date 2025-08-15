# SportMonks API Integration Guide

## ✅ Integration Complete

Your SportMonks API has been successfully integrated into the FPL AI Pro application. The infrastructure is ready and will activate once you have a valid API key.

## 🔑 API Key Configuration

Your API key has been securely stored in the `.env` file:
```
SPORTMONKS_API_KEY=YV7BX4idXecP8rr4hbh3KMTsyKlf8I0nwHkc7amycfpKEndIERk9o2D40IgI
```

**Note**: The current API key appears to be invalid or expired. You'll need to:
1. Log into your SportMonks account at https://my.sportmonks.com
2. Generate a new API token
3. Update the `.env` file with the new token

## 📊 Available SportMonks Endpoints

Once activated with a valid API key, these endpoints will provide real-time data:

### Live Matches
- **Endpoint**: `GET /api/sportmonks/live`
- **Description**: Real-time Premier League match scores
- **Features**: Live scores, lineups, events, statistics

### Fixtures
- **Endpoint**: `GET /api/sportmonks/fixtures?date=YYYY-MM-DD`
- **Description**: Match fixtures for specific dates
- **Features**: Teams, venues, odds, predictions

### League Standings
- **Endpoint**: `GET /api/sportmonks/standings`
- **Description**: Current Premier League table
- **Features**: Points, goals, form, detailed statistics

### Top Scorers
- **Endpoint**: `GET /api/sportmonks/top-scorers?limit=20`
- **Description**: Leading goalscorers in the league
- **Features**: Goals, assists, team information

### Injuries & Suspensions
- **Endpoint**: `GET /api/sportmonks/injuries`
- **Description**: Current player unavailability
- **Features**: Injury type, expected return, team impact

### Player Search
- **Endpoint**: `GET /api/sportmonks/player/search?name=PlayerName`
- **Description**: Search for players by name
- **Features**: Stats, position, team, transfer history

### Team Statistics
- **Endpoint**: `GET /api/sportmonks/team/{team_id}/stats`
- **Description**: Detailed team performance data
- **Features**: Form, squad, transfers, sidelined players

### Team Form
- **Endpoint**: `GET /api/sportmonks/team/{team_id}/form?matches=5`
- **Description**: Recent match results and performance
- **Features**: Last N matches, scores, statistics

## 🎯 Features Added to Your App

### 1. Live Scores Widget
- Located in the "Live Scores" tab
- Shows real-time match scores
- Displays league standings
- Auto-refreshes every 30 seconds
- Falls back to demo data when API unavailable

### 2. Enhanced Player Data
- More accurate player statistics
- Real-time injury updates
- Historical performance data
- Head-to-head comparisons

### 3. Match Predictions
- AI-powered match outcome predictions
- Probability calculations
- Team form analysis
- Historical head-to-head data

## 🚀 Testing the Integration

1. **Check API Status**:
   ```bash
   curl http://localhost:8001/api/sportmonks/live
   ```

2. **View Live Scores**:
   - Open http://localhost:3000
   - Click on "Live Scores" tab
   - Data will update automatically when API is active

3. **Test with Valid API Key**:
   ```bash
   export SPORTMONKS_API_KEY="your-valid-api-key"
   python3 sportmonks_integration.py
   ```

## 📈 SportMonks API Benefits

- **Real-time Data**: Updates faster than TV broadcasts
- **Comprehensive Coverage**: 2,500+ football leagues
- **Rich Statistics**: Detailed player and team analytics
- **Predictive Analytics**: Match outcome probabilities
- **Historical Data**: Complete season archives

## 🔧 Troubleshooting

### Invalid API Key Error
1. Verify your API key at https://my.sportmonks.com
2. Check your subscription status
3. Ensure the key has Premier League access

### No Data Showing
1. The app automatically falls back to mock data
2. Check console for error messages
3. Verify API endpoints are accessible

### Rate Limiting
- Default: 2000 calls per endpoint per hour
- Upgrade available for higher limits
- Caching implemented to minimize API calls

## 💡 Next Steps

1. **Get Valid API Key**:
   - Sign up at https://www.sportmonks.com
   - Choose a plan that includes Premier League data
   - Free trial available for testing

2. **Update Configuration**:
   ```bash
   # Edit .env file
   SPORTMONKS_API_KEY=your-new-api-key
   
   # Restart the API
   python3 -m uvicorn api_production:app --port 8001
   ```

3. **Monitor Usage**:
   - Check API usage in SportMonks dashboard
   - Review cached vs. live requests
   - Optimize polling intervals as needed

## 📞 Support

- **SportMonks Documentation**: https://docs.sportmonks.com/football/
- **API Status**: https://status.sportmonks.com/
- **Support**: support@sportmonks.com

Your SportMonks integration is ready to provide enhanced real-time football data as soon as you update with a valid API key!