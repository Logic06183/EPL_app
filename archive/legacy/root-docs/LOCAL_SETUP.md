# 🏠 FPL Predictor Pro - Local Demo Setup

Run the complete FPL prediction system locally on your computer to see all features in action before deployment!

## 🚀 Quick Start (One Command)

```bash
cd /Users/craig/Desktop/EPL_app
python local_demo.py
```

That's it! The script will:
- ✅ Check and install Python dependencies
- ✅ Set up SQLite database with sample data
- ✅ Start the FastAPI backend on port 8000
- ✅ Start the Next.js frontend on port 3000
- ✅ Open your browser automatically

## 📋 What You'll See

### **🌐 Web Dashboard (http://localhost:3000)**
- **AI Predictions**: Top player predictions with confidence scores
- **Squad Optimizer**: Optimize your 15-man squad for maximum points
- **Player Analysis**: Deep dive into individual player metrics
- **Gameweek Info**: Current gameweek status and fixtures

### **🔗 API Server (http://localhost:8000)**
- **Interactive Docs**: Full API documentation at `/docs`
- **All Endpoints**: Live API with real responses
- **Demo Data**: 20 sample players with predictions

### **👤 Demo Account**
- **User**: `demo_user`
- **Tier**: Premium (all features unlocked)
- **Auto-login**: No signup required

## 🎯 Test Features

### **1. AI Predictions**
- View top 50 player predictions
- See confidence scores and expected points
- Filter by position (GK, DEF, MID, FWD)
- Real ML model predictions

### **2. Squad Optimizer**
- Optimize 15-player squad within £100m budget
- Position constraints (2 GK, 5 DEF, 5 MID, 3 FWD)
- Max 3 players per team
- Linear programming optimization

### **3. Alerts & Intelligence**
- **Price Alerts**: Players likely to rise/fall tonight
- **Injury Alerts**: Latest injury news and severity
- **Sentiment Analysis**: News sentiment impact on predictions
- **Live Updates**: Mock live gameweek data

### **4. Sample Data Includes**
- **Premier League stars**: Haaland, Salah, Kane, etc.
- **Realistic prices**: Current 2023-24 season prices
- **Form data**: Recent performance metrics
- **Injury status**: Sample injured/suspended players
- **News sentiment**: Positive/negative news analysis

## 🔧 Manual Setup (If Needed)

### **Backend Only**
```bash
# Install Python dependencies
pip install -r requirements_local.txt

# Start backend server
python -m src.api.local_main
```

### **Frontend Only**
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start development server
npm run dev
```

## 📊 Architecture Overview

```
┌─────────────────────┐    HTTP/JSON    ┌─────────────────────┐
│   Next.js Frontend  │ ←──────────────→ │   FastAPI Backend   │
│   (localhost:3000)  │                 │   (localhost:8000)  │
└─────────────────────┘                 └─────────────────────┘
                                                   │
                                                   ▼
                                        ┌─────────────────────┐
                                        │   SQLite Database   │
                                        │   (local storage)   │
                                        └─────────────────────┘
```

## 🧪 Testing Scenarios

### **User Journey 1: Casual Fan**
1. Open dashboard → See top predictions
2. Check Haaland's prediction → 12.5 points
3. View price alerts → Salah likely to rise
4. Try squad optimizer → Get optimized team

### **User Journey 2: Serious Player**
1. Navigate to Analysis tab → Deep player metrics
2. Check injury alerts → De Bruyne out 4-6 weeks
3. View sentiment analysis → News impact on players
4. Test API endpoints → Use /docs for testing

### **User Journey 3: Developer**
1. Explore API docs → http://localhost:8000/docs
2. Test all endpoints → See live responses
3. Check database → SQLite with sample data
4. Review code structure → Ready for deployment

## 🎨 UI Features

### **Modern Design**
- ✨ Glass morphism effects
- 🌈 Gradient backgrounds
- 📱 Mobile-responsive
- 🌙 Dark theme ready

### **Interactive Elements**
- 🎯 Live prediction cards
- 📊 Animated charts (coming)
- 🔔 Real-time alerts
- 🎮 Smooth transitions

## 🛠️ Development Mode

### **Hot Reload**
- Backend: Auto-reloads on code changes
- Frontend: Live updates with Next.js
- Database: Persistent across restarts

### **Debug Mode**
- API logs in terminal
- Browser dev tools enabled
- Error handling with stack traces

## 📈 Sample Data Details

### **Players (20 total)**
- **Goalkeepers**: Pickford, Alisson, Ramsdale
- **Defenders**: Van Dijk, Saliba, James (injured)
- **Midfielders**: Salah, Saka, De Bruyne (injured)
- **Forwards**: Haaland, Kane, Núñez

### **Predictions**
- **Range**: 2.1 - 12.5 points
- **Confidence**: 0.65 - 0.89
- **Based on**: Form, price, opposition

### **Alerts (4 types)**
- **Price Rise**: Salah (+£0.1m likely)
- **Price Fall**: James (-£0.1m likely)  
- **Injury**: De Bruyne (4-6 weeks out)
- **Suspension**: Toney (betting ban)

## 🚨 Troubleshooting

### **Port Already in Use**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000  
lsof -ti:3000 | xargs kill -9
```

### **Dependencies Missing**
```bash
# Reinstall Python packages
pip install -r requirements_local.txt

# Reinstall Node packages
cd frontend && npm install
```

### **Database Issues**
```bash
# Delete and recreate database
rm -f data/local_fpl.db
python local_demo.py
```

## 🎯 Next Steps After Testing

Once you've tested the local version:

1. **Production Deployment** → See `DEPLOYMENT_STRATEGY.md`
2. **Add Features** → Extend with new ML models
3. **Scale Database** → Switch to PostgreSQL
4. **Add Authentication** → Implement Supabase auth
5. **Launch Marketing** → Go live with FPL community

## 💡 Tips for Testing

- **Try different browsers** → Chrome, Safari, Firefox
- **Test mobile view** → Resize browser window
- **Check API responses** → Use /docs endpoint
- **Test error handling** → Disconnect internet
- **Performance testing** → Open dev tools

---

## 🎉 Ready to Test!

Your complete FPL prediction system is now running locally. Test all the features, see how everything works together, and get ready to launch the next big FPL tool!

```bash
python local_demo.py
```

**Dashboard**: http://localhost:3000  
**API Docs**: http://localhost:8000/docs