import math
from typing import Dict, Any, Tuple
from src.config import (
    AYDIN_UNIV_LAT, AYDIN_UNIV_LON,
    BESYOL_METROBUS_LAT, BESYOL_METROBUS_LON,
    TARGET_MAX_BUDGET_TL, EXCEPTIONAL_BUDGET_LIMIT_TL
)

# Coordinates dictionary for key Istanbul rental neighborhoods
NEIGHBORHOOD_COORDS = {
    "beşyol": (40.9880, 28.7990),
    "florya": (40.9780, 28.7900),
    "sefaköy": (41.0020, 28.7950),
    "cennet": (40.9950, 28.7850),
    "küçükçekmece": (40.9900, 28.7750),
    "gültepe": (41.0050, 28.8050),
    "yeşilköy": (40.9620, 28.8250),
    "avcılar": (40.9800, 28.7200),
    "yenibosna": (41.0000, 28.8350),
    "şirinevler": (40.9930, 28.8450)
}

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def estimate_walking_minutes(distance_km: float) -> int:
    """Estimate walking time assuming 4.5 km/h walking speed with road detour factor 1.25."""
    walking_speed_kmh = 4.5
    actual_walking_distance = distance_km * 1.25
    hours = actual_walking_distance / walking_speed_kmh
    return max(1, round(hours * 60))

def estimate_proximity(prop: Dict[str, Any]) -> Tuple[int, int]:
    """
    Returns (univ_walking_minutes, metrobus_walking_minutes).
    Uses coordinates if present, or neighborhood centroid fallback.
    """
    lat = prop.get("latitude")
    lon = prop.get("longitude")

    if not lat or not lon:
        loc_str = (prop.get("location") or prop.get("title") or "").lower()
        for neighborhood, (n_lat, n_lon) in NEIGHBORHOOD_COORDS.items():
            if neighborhood in loc_str:
                lat, lon = n_lat, n_lon
                break

    if not lat or not lon:
        # Default assumption: moderate proximity (~15 min)
        return 15, 12

    dist_univ = haversine_distance_km(lat, lon, AYDIN_UNIV_LAT, AYDIN_UNIV_LON)
    dist_metro = haversine_distance_km(lat, lon, BESYOL_METROBUS_LAT, BESYOL_METROBUS_LON)

    return estimate_walking_minutes(dist_univ), estimate_walking_minutes(dist_metro)

def cheap_filter(prop: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Fast deterministic filter (Cheap Filtering):
    Discards obvious bad matches instantly with zero LLM/API cost.
    """
    price = float(prop.get("price_tl", 0.0))
    if price <= 0:
        return False, "Invalid price (zero or missing)"

    if price > EXCEPTIONAL_BUDGET_LIMIT_TL:
        return False, f"Price {price} TL exceeds upper limit of {EXCEPTIONAL_BUDGET_LIMIT_TL} TL"

    rooms = str(prop.get("rooms", "")).lower()
    full_text = (prop.get("title", "") + " " + rooms + " " + str(prop.get("description", ""))).lower()
    
    # Allow 1+0, 1+1, Studio, Dormitory, and private rooms in shared apartment/Airbnb
    is_private_room = any(term in full_text for term in ["oda", "room", "tek kişilik", "airbnb", "öğrenci evi", "ev arkadaşı"])
    if any(unwanted in rooms for unwanted in ["3+1", "3+2", "4+1", "4+2", "5+1", "villa"]) and not is_private_room:
        return False, f"Room type '{rooms}' not 1+0 / 1+1 / Studio / Private Room"

    # Reject non-student/family-only listings if explicitly restricted
    desc = (prop.get("description") or "").lower()
    if "sadece aile" in desc or "aileye uygun" in desc and "öğrenci olmaz" in desc:
        return False, "Landlord explicitly refuses students (Family only)"

    return True, "Passed cheap filter"

def score_property(prop: Dict[str, Any]) -> Tuple[int, Dict[str, int], str]:
    """
    Calculates 0-100 property score based strictly on MASTER REQUIREMENTS.
    Returns (total_score, breakdown, classification).
    """
    univ_mins, metro_mins = estimate_proximity(prop)
    prop["univ_dist_min"] = univ_mins
    prop["metrobus_dist_min"] = metro_mins

    breakdown = {}

    # 1. Location (Max 40 points) - Criteria: 0-10 min walk = 40, 11-20 min = 37, Metrobus <=5 min = 35, 6-20 min = 28-32
    if univ_mins <= 10:
        loc_score = 40
    elif univ_mins <= 20:
        loc_score = 37
    elif metro_mins <= 5:
        loc_score = 35 # Direct Metrobus connection
    elif metro_mins <= 20:
        loc_score = max(28, 35 - int((metro_mins - 5) * 0.45))
    else:
        loc_score = max(10, 24 - int(metro_mins * 0.4))
    breakdown["location_transit"] = min(40, loc_score)

    # 2. Price (Max 25 points)
    price = float(prop.get("price_tl", 0.0))
    if price <= 20000:
        price_score = 25
    elif price <= 25000:
        price_score = 20
    elif price <= 30000:
        price_score = 15
    elif price <= 36000:
        price_score = 10
    elif price <= 40000:
        price_score = 5
    else:
        price_score = 0
    breakdown["price_budget"] = price_score

    # 3. Furnished (Max 15 points)
    # 1 = Full, 2 = Partial, 0 = Unfurnished
    furnished_code = int(prop.get("furnished", 0))
    if furnished_code == 1:
        furn_score = 15
    elif furnished_code == 2:
        furn_score = 8
    else:
        # Check text tags
        title_lower = (prop.get("title", "") + " " + prop.get("description", "")).lower()
        if "eşyalı" in title_lower or "furnished" in title_lower:
            furn_score = 15
            prop["furnished"] = 1
        else:
            furn_score = 0
    breakdown["furnishing"] = furn_score

    # 4. Quality & Specs (Max 10 points)
    qual_score = 0
    area = float(prop.get("area_m2") or 0.0)
    if area >= 35:
        qual_score += 3
    
    desc_str = (prop.get("title", "") + " " + prop.get("description", "")).lower()
    if "kombi" in desc_str or "doğalgaz" in desc_str or "merkezi" in desc_str:
        qual_score += 3
    if "asansör" in desc_str or "yeni" in desc_str or "sıfır" in desc_str:
        qual_score += 4
    else:
        qual_score += 2
    breakdown["quality_amenities"] = min(10, qual_score)

    # 5. Reliability & Freshness (Max 10 points)
    rel_score = 0
    if prop.get("contact_info"):
        rel_score += 4
    if prop.get("photos") and len(prop.get("photos", [])) > 0:
        rel_score += 3
    if prop.get("url") and "http" in prop.get("url"):
        rel_score += 3
    breakdown["reliability_freshness"] = min(10, rel_score)

    total_score = sum(breakdown.values())

    # Classification
    if total_score >= 90:
        classification = "EXCEPTIONAL"
    elif total_score >= 85:
        classification = "EXCELLENT"
    elif total_score >= 75:
        classification = "VERY_GOOD"
    elif total_score >= 65:
        classification = "GOOD"
    elif total_score >= 50:
        classification = "POTENTIAL"
    else:
        classification = "REJECT"

    # Handle over-budget exceptional rule
    if price > TARGET_MAX_BUDGET_TL and total_score >= 80:
        classification = "OVER_BUDGET_EXCEPTIONAL"

    return total_score, breakdown, classification
