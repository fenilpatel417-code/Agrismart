from fastapi import APIRouter, Response, Query
import time
import datetime as _dt
from routers.market import DISTRICT_TOWNS, get_crops_for_apmc, get_deterministic_price

router = APIRouter(prefix="/api", tags=["mandi"])

# In-memory APMC Mandi rates cache by date key
_mandi_cache = {}
MANDI_CACHE_DURATION = 3600  # 1 hour in seconds

def _today_str():
    """Return today's date as an ISO string."""
    return _dt.date.today().isoformat()

@router.get("/mandi")
async def get_mandi(response: Response, date: str = Query(default=None)):
    """Retrieve APMC Mandi price records for a specific date (defaults to today) with a 1-hour cache."""
    if date is None:
        date = _today_str()
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    current_time = time.time()
    # Check cache first using the selected date as key
    if date in _mandi_cache:
        cached_data, timestamp = _mandi_cache[date]
        if current_time - timestamp < MANDI_CACHE_DURATION:
            print(f"[CACHE HIT] Returning cached Mandi rates for date: {date}")
            return cached_data
            
    print(f"[CACHE MISS] Generating fresh Mandi rates for date: {date}")
    
    mandi_prices_list = []
    
    # Generate prices only for the specified target date
    for dist_id, towns in DISTRICT_TOWNS.items():
        for town_en, town_gu in towns:
            apmc_en = f"{town_en} APMC"
            apmc_gu = f"{town_gu} APMC"
            
            crops = get_crops_for_apmc(town_en)
            for crop in crops:
                crop_gu_map = {
                    "Cotton": "કપાસ", "Groundnut": "મગફળી", "Wheat": "ઘઉં", "Onion": "ડુંગળી",
                    "Potato": "બટાકા", "Cumin": "જીરું", "Mustard": "રાઈ", "Fennel": "વરિયાળી",
                    "Castor": "દિવેલા", "Bajra": "બાજરી", "Maize": "મકાઈ", "Paddy": "ડાંગર"
                }
                crop_gu = crop_gu_map.get(crop, crop)
                
                min_pr, max_pr, mod_pr, arr, trd, trd_dir = get_deterministic_price(date, apmc_en, crop)
                mandi_prices_list.append({
                    "date": date,
                    "apmc_en": apmc_en,
                    "apmc_gu": apmc_gu,
                    "crop_en": crop,
                    "crop_gu": crop_gu,
                    "arrival": arr,
                    "min_price": min_pr,
                    "max_price": max_pr,
                    "modal_price": mod_pr,
                    "trend": trd,
                    "trend_dir": trd_dir
                })
                    
    _mandi_cache[date] = (mandi_prices_list, current_time)
    return mandi_prices_list
