import math
from typing import Tuple, Optional
from ..config import config

class DistanceCalculator:
    # IAU Beşyol Campus coordinates
    IAU_LAT = config.TARGET_CAMPUS_LAT
    IAU_LON = config.TARGET_CAMPUS_LON

    # Known walking times (minutes) from central neighborhoods to IAU Beşyol
    NEIGHBORHOOD_WALK_TIMES = {
        "beşyol": 4,
        "besyol": 4,
        "florya": 12,
        "sefaköy": 16,
        "sefakov": 16,
        "cennet": 18,
        "cennet mahallesi": 18,
        "küçükçekmece": 25,
        "kucukcekmece": 25,
        "gültepe": 28,
        "gultepe": 28,
        "avcılar": 35,
        "avcilar": 35,
        "bakırköy": 40,
        "bakirkoy": 40,
        "şirinevler": 30,
        "yenibosna": 25
    }

    # Walking minutes to closest Metrobus station
    NEIGHBORHOOD_METROBUS_TIMES = {
        "beşyol": (4, "Beşyol"),
        "besyol": (4, "Beşyol"),
        "florya": (6, "Florya"),
        "sefaköy": (5, "Sefaköy"),
        "cennet": (5, "Cennet Mahallesi"),
        "küçükçekmece": (8, "Küçükçekmece"),
        "gültepe": (10, "Sefaköy")
    }

    @classmethod
    def haversine_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in kilometers."""
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @classmethod
    def estimate_university_distance(cls, location_text: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Tuple[int, str]:
        """
        Returns (estimated_minutes, travel_mode: 'walk' | 'metrobus')
        """
        if lat is not None and lon is not None:
            dist_km = cls.haversine_distance_km(lat, lon, cls.IAU_LAT, cls.IAU_LON)
            # Walking speed ~4.5 km/h -> ~13.3 min per km
            walk_min = int(dist_km * 13.3)
            if walk_min <= 20:
                return max(2, walk_min), "walk"
            else:
                # Metrobus / transit estimate
                transit_min = int(10 + (dist_km * 4))
                return transit_min, "metrobus"

        loc_lower = (location_text or "").lower()
        for neighborhood, minutes in cls.NEIGHBORHOOD_WALK_TIMES.items():
            if neighborhood in loc_lower:
                mode = "walk" if minutes <= 20 else "metrobus"
                return minutes, mode

        # Fallback default
        return 35, "metrobus"

    @classmethod
    def estimate_metrobus_distance(cls, location_text: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Tuple[int, str]:
        """
        Returns (minutes_to_metrobus, station_name)
        """
        if lat is not None and lon is not None:
            closest_station = "Beşyol"
            min_dist = 9999.0
            for st_name, (st_lat, st_lon) in config.METROBUS_STATIONS.items():
                d = cls.haversine_distance_km(lat, lon, st_lat, st_lon)
                if d < min_dist:
                    min_dist = d
                    closest_station = st_name
            walk_min = max(2, int(min_dist * 13.3))
            return walk_min, closest_station

        loc_lower = (location_text or "").lower()
        for neighborhood, (minutes, station) in cls.NEIGHBORHOOD_METROBUS_TIMES.items():
            if neighborhood in loc_lower:
                return minutes, station

        return 12, "Metrobus Line"
