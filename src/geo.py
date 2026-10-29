"""Distance and walking-time estimates relative to the campus and Metrobüs stations.

Emlakjet does not publish coordinates, so listings are placed at the centroid of their
neighbourhood (mahalle). All coordinates here are approximate. Mahalles missing from the
table are reported as "location unknown" rather than guessed from the district.
"""
import math
from typing import Dict, Optional, Tuple

from .config import METROBUS_STATIONS
from .textutil import fold

WALK_SPEED_KMH = 4.5
ROAD_DETOUR_FACTOR = 1.25

# Approximate mahalle centroids around the campus, keyed by folded name
NEIGHBORHOOD_COORDS: Dict[str, Tuple[float, float]] = {
    "besyol": (40.9925, 28.7985),
    "kartaltepe": (40.9990, 28.7990),
    "inonu": (41.0045, 28.8010),
    "sefakoy": (41.0020, 28.7950),
    "cennet": (40.9920, 28.7830),
    "senlikkoy": (40.9800, 28.7930),
    "florya": (40.9780, 28.7900),
    "yesilkoy": (40.9620, 28.8250),
    "kemalpasa": (40.9970, 28.7880),
    "fevzi cakmak": (41.0060, 28.7840),
    "gultepe": (41.0050, 28.8050),
    "tevfikbey": (41.0080, 28.7930),
    "yarimburgaz": (41.0120, 28.7800),
    "halkali": (41.0300, 28.7850),
    "atakent": (41.0230, 28.7720),
    "avcilar": (40.9800, 28.7200),
    "yenibosna": (41.0000, 28.8350),
    "sirinevler": (40.9930, 28.8450),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def walking_minutes(distance_km: float) -> int:
    hours = distance_km * ROAD_DETOUR_FACTOR / WALK_SPEED_KMH
    return max(1, round(hours * 60))


def locate(*texts: Optional[str]) -> Optional[Tuple[float, float]]:
    """Coordinates of the first known neighbourhood mentioned in `texts`, most specific first."""
    for text in texts:
        folded = fold(text)
        if not folded:
            continue
        for name, coords in NEIGHBORHOOD_COORDS.items():
            if name in folded:
                return coords
    return None


def nearest_station(lat: float, lon: float) -> Tuple[str, int]:
    """(station name, walking minutes) of the closest Metrobüs station."""
    name, (s_lat, s_lon) = min(
        METROBUS_STATIONS.items(), key=lambda kv: haversine_km(lat, lon, *kv[1])
    )
    return name, walking_minutes(haversine_km(lat, lon, s_lat, s_lon))


def campus_walk_minutes(lat: float, lon: float, campus: Tuple[float, float]) -> int:
    return walking_minutes(haversine_km(lat, lon, *campus))
