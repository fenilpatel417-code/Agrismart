from fastapi import APIRouter, Response
import time
import datetime as _dt
from routers.market import DISTRICTS, generate_weather_for_district

router = APIRouter(prefix="/api", tags=["weather"])

# In-memory weather cache
_weather_cache = {}
WEATHER_CACHE_DURATION = 1800  # 30 minutes in seconds

@router.get("/weather")
async def get_weather(response: Response):
    """Retrieve weather forecast for all districts with a 30-minute cache."""
    response.headers["Cache-Control"] = "public, max-age=1800"
    
    current_time = time.time()
    today_key = _dt.date.today().isoformat()  # Cache key includes today's date for auto-invalidation
    
    # Check cache first (keyed by today's date so it resets at midnight)
    if today_key in _weather_cache:
        cached_data, timestamp = _weather_cache[today_key]
        if current_time - timestamp < WEATHER_CACHE_DURATION:
            print("[CACHE HIT] Returning cached weather forecasts")
            return cached_data
            
    print("[CACHE MISS] Generating fresh weather forecasts")
    
    # Generate and save to cache
    weather_forecasts = {}
    for d in DISTRICTS:
        weather_forecasts[d["id"]] = generate_weather_for_district(d["id"], d["en"], d["gu"])
    
    # Clear old day keys and store new
    _weather_cache.clear()
    _weather_cache[today_key] = (weather_forecasts, current_time)
    return weather_forecasts
