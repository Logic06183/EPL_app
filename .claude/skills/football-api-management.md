# ⚽ Football API Management - Best Practices

## Overview
This skill covers managing football/FPL API integrations with reliability, caching, rate limiting, and fallback strategies.

---

## 🎯 Official FPL API (FREE & RELIABLE)

### Primary Endpoints

**1. Bootstrap Static** (Main Data Source)
```python
FPL_API_BASE = "https://fantasy.premierleague.com/api"
endpoint = f"{FPL_API_BASE}/bootstrap-static/"

# Returns:
# - elements: All 753 players with stats (xG, xA, ICT, form, ownership)
# - teams: All 20 Premier League teams
# - events: All 38 gameweeks with deadlines
# - element_types: Position types (GKP, DEF, MID, FWD)
```

**2. Fixtures**
```python
endpoint = f"{FPL_API_BASE}/fixtures/"
# Returns all fixtures with scores, stats, bonus points
```

**3. Player Details**
```python
endpoint = f"{FPL_API_BASE}/element-summary/{player_id}/"
# Returns detailed history, fixtures for specific player
```

### ✅ Why FPL Official API is Best:

1. **Free** - No API keys required
2. **Reliable** - 99.9% uptime during season
3. **Comprehensive** - xG, xA, ICT, bonus, ownership, transfers
4. **Real-time** - Updates live during matches
5. **No Rate Limits** - Reasonable usage accepted
6. **Official Data** - Direct from Premier League Fantasy

---

## 🛡️ Best Practices for API Reliability

### 1. Implement Caching

**In-Memory Cache (Fast)**
```python
from cachetools import TTLCache

# Cache for 5 minutes
memory_cache = TTLCache(maxsize=100, ttl=300)

async def get_fpl_data_cached():
    cache_key = "fpl:bootstrap_data"

    # Check cache first
    if cache_key in memory_cache:
        logger.info("Returning cached FPL data")
        return memory_cache[cache_key]

    # Fetch fresh data
    response = await session.get(f"{FPL_API_BASE}/bootstrap-static/")
    data = response.json()

    # Store in cache
    memory_cache[cache_key] = data
    return data
```

**Why Cache?**
- Reduces API calls by 90%+
- Faster response times (<10ms vs 500ms+)
- Protects against rate limiting
- Works during API downtime

### 2. Add Retry Logic with Exponential Backoff

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(url):
    """Retry failed requests with exponential backoff"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

**Benefits:**
- Automatic retry on network failures
- Exponential backoff: 2s → 4s → 8s delays
- Prevents overwhelming the API

### 3. Implement Graceful Fallbacks

```python
async def get_fpl_data():
    """Get FPL data with fallback to mock data"""
    try:
        # Try fetching from API
        data = await fetch_with_retry(f"{FPL_API_BASE}/bootstrap-static/")
        return data

    except Exception as e:
        logger.error(f"FPL API failed: {e}")

        # Fallback: Return minimal mock data
        return {
            "elements": load_cached_players(),  # From last successful fetch
            "teams": load_cached_teams(),
            "events": [{"id": 1, "name": "Gameweek 1", "is_current": True}]
        }
```

### 4. Set Appropriate Timeouts

```python
# Good: Reasonable timeouts
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)

# Bad: No timeout (hangs forever)
response = requests.get(url)
```

### 5. Add Request Headers (Be a Good Citizen)

```python
headers = {
    "User-Agent": "YourApp/1.0 (your.email@example.com)",
    "Accept": "application/json"
}

response = await client.get(url, headers=headers)
```

---

## 🔄 API Call Pattern (Production-Ready)

```python
class FPLDataManager:
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=300)  # 5 min cache
        self.session = None

    async def get_session(self):
        """Reuse HTTP session for connection pooling"""
        if not self.session:
            timeout = httpx.Timeout(30.0, connect=10.0)
            self.session = httpx.AsyncClient(
                timeout=timeout,
                headers={"User-Agent": "EPL AI Pro/1.0"}
            )
        return self.session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_bootstrap_data(self):
        """Get FPL bootstrap data with caching & retry"""
        cache_key = "fpl:bootstrap"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Fetch from API
            session = await self.get_session()
            response = await session.get(f"{FPL_API_BASE}/bootstrap-static/")
            response.raise_for_status()

            data = response.json()
            self.cache[cache_key] = data

            # Also save to disk for fallback
            save_backup(data, "fpl_backup.json")

            return data

        except Exception as e:
            logger.error(f"API fetch failed: {e}")

            # Try loading from disk backup
            backup_data = load_backup("fpl_backup.json")
            if backup_data:
                logger.warning("Using backup data from disk")
                return backup_data

            # Last resort: minimal mock data
            return get_minimal_mock_data()
```

---

## 🌐 Alternative Football APIs (If Needed)

### 1. API-Football (RapidAPI)
**Pros:**
- Comprehensive: Multiple leagues, live scores, stats
- Well-documented
- 100 free requests/day

**Cons:**
- Requires API key
- Rate limited (100/day free tier)
- No xG/xA in free tier

```python
import requests

url = "https://api-football-v1.p.rapidapi.com/v3/players"
headers = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}
response = requests.get(url, headers=headers)
```

### 2. SportMonks API
**Pros:**
- xG, xA, detailed metrics
- Multiple sports
- Good uptime

**Cons:**
- Paid ($0-$500+/month)
- Complex setup
- Requires subscription

```python
url = "https://api.sportmonks.com/v3/football/fixtures"
params = {"api_token": os.getenv("SPORTMONKS_API_KEY")}
response = requests.get(url, params=params)
```

### 3. FotMob (Unofficial)
**Pros:**
- Free
- xG, xA, heat maps
- Mobile-friendly

**Cons:**
- Unofficial (can break anytime)
- No API docs
- Not recommended for production

---

## 📊 Monitoring API Health

### Add Health Checks

```python
@app.get("/health/apis")
async def check_api_health():
    """Check if external APIs are responding"""
    checks = {}

    # Test FPL API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FPL_API_BASE}/bootstrap-static/")
            checks["fpl_api"] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
    except Exception as e:
        checks["fpl_api"] = {"status": "down", "error": str(e)}

    return checks
```

### Log API Performance

```python
import time

async def fetch_with_metrics(url):
    """Track API performance"""
    start = time.time()

    try:
        response = await client.get(url)
        duration_ms = (time.time() - start) * 1000

        logger.info(f"API call success: {url} ({duration_ms:.0f}ms)")
        return response.json()

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        logger.error(f"API call failed: {url} ({duration_ms:.0f}ms) - {e}")
        raise
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Connection timeout"
**Solution:**
```python
# Increase timeout
timeout = httpx.Timeout(60.0, connect=15.0)
client = httpx.AsyncClient(timeout=timeout)
```

### Issue 2: "Too many requests" (429 error)
**Solution:**
```python
# Add rate limiting
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=60)  # Max 10 calls per minute
async def rate_limited_fetch(url):
    return await client.get(url)
```

### Issue 3: "Connection refused"
**Solution:**
```python
# Check cache first, then retry
if cache_key in cache:
    return cache[cache_key]

try:
    data = await fetch_with_retry(url)
except Exception:
    # Use backup data
    data = load_backup()
```

### Issue 4: "Inconsistent data"
**Solution:**
```python
# Validate response before caching
def validate_fpl_data(data):
    """Ensure data has required fields"""
    required = ["elements", "teams", "events"]
    return all(key in data for key in required)

if validate_fpl_data(data):
    cache[cache_key] = data
else:
    logger.error("Invalid FPL data structure")
```

---

## 🎯 Quick Reference

### DO ✅
- Cache aggressively (5-10 min TTL)
- Use retry logic with exponential backoff
- Set timeouts (30s for API calls)
- Implement fallbacks
- Reuse HTTP sessions (connection pooling)
- Log API performance
- Save backup data to disk

### DON'T ❌
- Make API calls on every request
- Use infinite timeouts
- Ignore errors (always have fallbacks)
- Hardcode API URLs (use environment variables)
- Skip User-Agent headers
- Call APIs synchronously in async functions

---

## 📦 Recommended Python Packages

```bash
# Install these for robust API management
pip install httpx          # Modern async HTTP client
pip install tenacity       # Retry with exponential backoff
pip install cachetools     # In-memory caching
pip install ratelimit      # Rate limiting
```

---

## 🧪 Testing Your API Integration

```python
import pytest

@pytest.mark.asyncio
async def test_fpl_api_available():
    """Test that FPL API is responding"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{FPL_API_BASE}/bootstrap-static/")
        assert response.status_code == 200
        data = response.json()
        assert "elements" in data
        assert len(data["elements"]) > 700  # At least 700 players

@pytest.mark.asyncio
async def test_caching_works():
    """Test that caching reduces API calls"""
    manager = FPLDataManager()

    # First call fetches from API
    data1 = await manager.get_bootstrap_data()

    # Second call should use cache (instant)
    import time
    start = time.time()
    data2 = await manager.get_bootstrap_data()
    duration = time.time() - start

    assert duration < 0.01  # Should be < 10ms (cached)
    assert data1 == data2
```

---

## 🎓 Summary

**For EPL/FPL Apps:**
1. **Use Official FPL API first** - Free, reliable, comprehensive
2. **Always implement caching** - 5-10 min TTL minimum
3. **Add retry logic** - Exponential backoff (3 retries)
4. **Have fallbacks** - Backup data or mock data
5. **Monitor health** - Track API performance
6. **Be a good citizen** - Use User-Agent, respect rate limits

**Your current app is using the official FPL API correctly!** The API is working perfectly. If you're experiencing issues, they're likely from:
- Missing caching configuration
- No retry logic
- Frontend not handling loading states
- CORS issues (solved by backend proxy)

---

*Generated for EPL AI Pro - November 23, 2025*
