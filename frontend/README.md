# FPL Prediction Frontend

Modern React/Next.js dashboard for the Fantasy Premier League AI prediction system.

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The frontend will be available at: http://localhost:3000

### 3. Start Backend API
In another terminal:
```bash
cd .. # Back to main project directory
python run.py
```

The API will be available at: http://localhost:8000

## ✨ Features

### 🎯 **Player Predictions**
- Top player predictions with AI confidence scores
- Position-based filtering and sorting
- Value analysis (points per £)
- Beautiful cards with hover effects
- Top 3 highlighted predictions

### 🏆 **Squad Optimizer**
- Budget constraint optimization (£80m - £120m)
- Linear programming algorithm
- Formation validation
- Position-by-position squad breakdown
- Cost and points analysis

### 📊 **Player Analysis**
- Individual player deep dive
- Performance charts (recent 5 gameweeks)
- Next 5 gameweeks predictions
- Goals, assists, and points tracking
- Interactive data visualization

### 📅 **Gameweek Information**
- Current gameweek status
- Transfer deadline countdown
- Live status indicators
- Tips and recommendations

## 🎨 Design System

### **Color Palette**
- **Primary**: Blue to purple gradient
- **Positions**: 
  - GK: Yellow/Orange
  - DEF: Green/Emerald
  - MID: Blue/Indigo
  - FWD: Red/Rose

### **Components**
- **Glass morphism** cards with backdrop blur
- **Responsive** grid layouts
- **Smooth animations** and hover effects
- **Loading states** with spinners
- **Error handling** with retry buttons

### **Typography**
- Inter font family
- Consistent sizing scale
- High contrast for accessibility

## 📱 Responsive Design

- **Mobile-first** approach
- **Breakpoints**:
  - Mobile: < 640px
  - Tablet: 640px - 1024px
  - Desktop: 1024px+
- **Touch-friendly** interactions
- **Optimized** for iOS Safari

## 🔧 Technical Stack

### **Core**
- Next.js 14
- React 18
- Tailwind CSS 3

### **Data Visualization**
- Recharts (charts and graphs)
- Custom data visualization components

### **Icons**
- Lucide React (beautiful, consistent icons)

### **Styling**
- Tailwind CSS
- Custom CSS properties
- CSS animations
- Glass morphism effects

## 📡 API Integration

### **Endpoints Used**
```javascript
// Player Predictions
GET /api/players/predictions?top_n=15

// Squad Optimization
POST /api/optimize/squad
{ "budget": 100.0 }

// Player Details
GET /api/players/{id}/details

// Gameweek Info
GET /api/gameweek/current

// Health Check
GET /api/health
```

### **Error Handling**
- Network error recovery
- Loading states
- User-friendly error messages
- Retry mechanisms

## 🚀 Deployment Options

### **Vercel (Recommended)**
```bash
npm install -g vercel
vercel
```

### **Netlify**
```bash
npm run build
# Deploy ./out folder to Netlify
```

### **Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 🔧 Environment Variables

Create `.env.local`:
```bash
# API Backend URL (for production)
NEXT_PUBLIC_API_URL=https://your-api-domain.com

# Development (uses proxy in next.config.js)
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Performance

### **Optimizations**
- Next.js automatic code splitting
- Image optimization
- Font optimization (Inter from Google Fonts)
- CSS purging with Tailwind

### **Bundle Size**
- Main bundle: ~200KB gzipped
- Chart library: ~50KB gzipped
- Icons: ~20KB gzipped

## 🧪 Testing

### **Component Testing**
```bash
npm install --save-dev @testing-library/react jest
npm run test
```

### **E2E Testing**
```bash
npm install --save-dev playwright
npx playwright test
```

## 📋 Development Workflow

### **File Structure**
```
frontend/
├── app/
│   ├── globals.css      # Global styles
│   ├── layout.js        # Root layout
│   └── page.js          # Home page
├── components/
│   ├── PlayerPredictions.js
│   ├── SquadOptimizer.js
│   ├── PlayerAnalysis.js
│   ├── GameweekInfo.js
│   ├── PlayerCard.js
│   └── ApiStatus.js
├── public/              # Static assets
└── package.json
```

### **Adding New Features**
1. Create component in `/components`
2. Add to main navigation in `page.js`
3. Implement API integration
4. Add error handling and loading states
5. Test responsive design

## 🎯 Future Enhancements

### **Planned Features**
- [ ] Transfer planner with multiple gameweek horizon
- [ ] Price change predictions
- [ ] Player comparison tool
- [ ] League standings integration
- [ ] Push notifications for deadlines
- [ ] Offline mode with service worker

### **Performance Improvements**
- [ ] React Query for data caching
- [ ] Virtual scrolling for large lists
- [ ] Progressive Web App features
- [ ] WebSocket for real-time updates

## 🐛 Troubleshooting

### **Common Issues**

**API not connecting:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check proxy configuration
cat next.config.js
```

**Build errors:**
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

**Styling issues:**
```bash
# Rebuild Tailwind CSS
npm run build
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License - see main project LICENSE file.