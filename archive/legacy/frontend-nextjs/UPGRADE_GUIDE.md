# Frontend Upgrade Guide - Next.js 15 & New Backend API

## Changes Made

### 1. Dependencies Updated

**Next.js**: 14.0.0 → 15.1.3
**React**: 18.x → 19.0.0
**TailwindCSS**: 3.3.0 → 4.0.0
**All other packages**: Updated to latest compatible versions

### 2. New API Client Created

Created centralized API client at `/lib/api.js` that:
- Handles all backend communication
- Provides clean, typed functions for each endpoint
- Includes proper error handling
- Supports timeouts and request cancellation
- Works with the new backend structure

### 3. API Endpoints Changed

**Old Backend Structure:**
```
/api/players/predictions/enhanced
/api/models/info
```

**New Backend Structure:**
```
/api/predictions              # Get predictions
/api/predictions/enhanced     # Enhanced with Gemini AI
/api/predictions/models/info  # Model information
/api/players                  # Player data
/api/teams/optimize           # Team optimization
/api/teams/transfers          # Transfer suggestions
```

### 4. Component Updates

Updated `PlayerPredictionsEPL.js` to:
- Use new API client functions
- Handle new response structures
- Support React 19 changes
- Improved error handling

## Installation & Upgrade

### Step 1: Install Dependencies

```bash
cd frontend

# Remove old node_modules and lock file
rm -rf node_modules package-lock.json

# Install new dependencies
npm install
```

### Step 2: Configure Backend URL

Create or update `.env.local`:

```env
# For local development with local backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# For production (Cloud Run backend)
NEXT_PUBLIC_API_URL=https://epl-backend-77913915885.us-central1.run.app
```

### Step 3: Test Locally

```bash
# Start frontend (make sure backend is running)
npm run dev

# Open http://localhost:3000
```

### Step 4: Build for Production

```bash
# Build static export
npm run build

# Test the build
npm run start
```

## Breaking Changes

### 1. React 19 Changes

React 19 introduces some breaking changes. If you see warnings:

- Update `'use client'` directives as needed
- Some hooks behavior may have changed
- Check console for deprecation warnings

### 2. TailwindCSS 4.0

TailwindCSS 4 has new features. Current config should work but you may want to:

- Review `tailwind.config.js`
- Update custom utilities if needed
- Check for deprecated classes

### 3. Next.js 15 Changes

- Static export (`output: 'export'`) is still supported
- Image optimization is disabled (required for static export)
- Some experimental features available

## API Client Usage

### Import the client

```javascript
import { getPredictions, getEnhancedPredictions } from '../lib/api'
```

### Get Basic Predictions

```javascript
const predictions = await getPredictions({
  topN: 50,
  model: 'random_forest',
  position: 2, // Defenders
  maxPrice: 10.0
})
```

### Get Enhanced Predictions with Gemini AI

```javascript
const predictions = await getEnhancedPredictions({
  topN: 20,
  model: 'ensemble',
  useGemini: true
})
```

### Get Player Details

```javascript
import { getPlayerById } from '../lib/api'

const player = await getPlayerById(123)
```

### Optimize Team

```javascript
import { optimizeTeam } from '../lib/api'

const optimized = await optimizeTeam({
  budget: 100.0,
  formation: '3-4-3',
  excludedPlayers: [123, 456]
})
```

### Handle Errors

```javascript
import { handleApiError } from '../lib/api'

try {
  const predictions = await getPredictions()
} catch (error) {
  const errorMessage = handleApiError(error)
  console.error(errorMessage)
}
```

## Component Migration

### Old Way (Direct fetch)

```javascript
const response = await fetch(`${API_URL}/api/players/predictions/enhanced?top_n=20`)
const data = await response.json()
```

### New Way (API client)

```javascript
import { getEnhancedPredictions } from '../lib/api'

const predictions = await getEnhancedPredictions({ topN: 20 })
```

## Testing Checklist

- [ ] Frontend builds successfully (`npm run build`)
- [ ] No console errors in development
- [ ] API calls work with local backend
- [ ] API calls work with production backend
- [ ] Player predictions load correctly
- [ ] Filters work (position, top N, model type)
- [ ] Advanced stats (xG, xA, ICT) display correctly
- [ ] Gemini AI insights appear (if enabled)
- [ ] Error states display properly
- [ ] Loading states work
- [ ] Responsive design works on mobile

## Troubleshooting

### "Failed to fetch" errors

1. Check backend is running
2. Verify `NEXT_PUBLIC_API_URL` is correct
3. Check CORS settings in backend

### Type errors with React 19

1. Update `@types/react` and `@types/react-dom`
2. Check component prop types
3. Review React 19 migration guide

### Build fails

1. Clear `.next` directory: `rm -rf .next`
2. Clear `node_modules`: `rm -rf node_modules package-lock.json`
3. Reinstall: `npm install`
4. Rebuild: `npm run build`

### Styles not working

1. Check `tailwind.config.js` is correct
2. Ensure `globals.css` imports Tailwind
3. Clear `.next` and rebuild

## Rollback Instructions

If you need to rollback:

```bash
# Restore old package.json
git checkout HEAD~1 -- package.json

# Restore old component
mv components/PlayerPredictionsEPL.old.js components/PlayerPredictionsEPL.js

# Remove API client
rm lib/api.js

# Reinstall old dependencies
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

After successful upgrade:

1. **Update other components** to use new API client
2. **Add TypeScript** for better type safety (optional)
3. **Implement new features** from new backend
4. **Add tests** for components and API client
5. **Optimize performance** with React 19 features

## New Features Available

With the new backend, you can now:

- ✅ Use multi-model predictions (RandomForest, CNN, Ensemble)
- ✅ Get xG/xA analytics for all players
- ✅ Request Gemini AI insights
- ✅ Get detailed model information
- ✅ Retrain models on demand
- ✅ Optimize teams with better algorithms
- ✅ Get transfer suggestions
- ✅ Access payment/subscription endpoints

## Support

If you encounter issues:

1. Check backend logs
2. Check browser console
3. Review this guide
4. Check backend API documentation at `http://localhost:8000/docs`

---

**Upgrade completed!** 🚀

Your frontend is now running:
- Next.js 15
- React 19
- Modern API client
- Connected to refactored backend
