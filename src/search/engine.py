import logging
from typing import List, Dict, Any, Tuple
from ..config import config
from .sources.dormitories import DormitorySource
from .sources.web_scraper import WebScraperSource
from ..extraction.normalizer import PropertyNormalizer
from ..extraction.distance import DistanceCalculator
from ..scoring.scorer import PropertyScorer
from ..db.models import PropertyRecord

logger = logging.getLogger(__name__)

class SearchEngine:
    SEARCH_QUERIES = [
        "Beşyol kiralık 1+0 eşyalı",
        "Beşyol kiralık 1+1 eşyalı",
        "İstanbul Aydın Üniversitesi yakınında kiralık daire",
        "Metrobüs yakınında 1+0 kiralık eşyalı",
        "Sefaköy Cennet kiralık 1+1 eşyalı",
        "İstanbul Aydın Üniversitesi erkek öğrenci yurdu Beşyol",
        "Küçükçekmece öğrenciye uygun kiralık daire",
        "Airbnb monthly stay Küçükçekmece Beşyol studio"
    ]

    def __init__(self):
        self.current_cycle_index = 0

    def get_current_query(self) -> str:
        query = self.SEARCH_QUERIES[self.current_cycle_index % len(self.SEARCH_QUERIES)]
        return query

    def advance_cycle(self):
        self.current_cycle_index = (self.current_cycle_index + 1) % len(self.SEARCH_QUERIES)

    def execute_search_cycle(self) -> Tuple[List[PropertyRecord], int, int]:
        """
        Executes current search cycle.
        Returns: (candidate_properties, sources_checked_count, raw_found_count)
        """
        query = self.get_current_query()
        logger.info(f"Executing search cycle #{self.current_cycle_index + 1} with query: '{query}'")
        
        raw_items: List[Dict[str, Any]] = []
        sources_checked = 0

        # 1. Fetch Dormitories
        try:
            dorms = DormitorySource.fetch_listings()
            raw_items.extend(dorms)
            sources_checked += 1
        except Exception as e:
            logger.error(f"Error fetching dormitory sources: {e}")

        # 2. Fetch Web Scraper listings
        try:
            web_results = WebScraperSource.search_query(query)
            raw_items.extend(web_results)
            sources_checked += 1
        except Exception as e:
            logger.error(f"Error searching web query '{query}': {e}")

        self.advance_cycle()
        raw_found_count = len(raw_items)

        # 3. Normalize & Score candidates
        candidates: List[PropertyRecord] = []
        for item in raw_items:
            try:
                record = PropertyNormalizer.normalize_record(item)
                
                # Pre-filtering:
                # 1. Location must be in Istanbul
                full_loc_text = f"{record.location} {record.address} {record.title}".lower()
                if config.REQUIRE_ISTANBUL_ONLY:
                    # Filter out other Turkish cities if mistakenly returned (e.g. Izmir Bornova, Aydin Nazilli)
                    non_istanbul_markers = ["izmir", "i̇zmir", "bornova", "nazilli", "ankara", "bursa", "antalya"]
                    if any(marker in full_loc_text for marker in non_istanbul_markers) and "istanbul" not in full_loc_text and "küçükçekmece" not in full_loc_text and "florya" not in full_loc_text:
                        continue

                # 2. Maximum distance <= 30 km to university campus
                if record.latitude is not None and record.longitude is not None:
                    dist_km = DistanceCalculator.haversine_distance_km(
                        record.latitude, record.longitude,
                        config.TARGET_CAMPUS_LAT, config.TARGET_CAMPUS_LON
                    )
                    if dist_km > config.MAX_DISTANCE_KM_TO_UNIVERSITY:
                        continue

                # 3. Discard over-budget beyond buffer or invalid
                eff_price = record.effective_monthly_price or record.price
                if eff_price > (config.MAX_BUDGET_TL * 1.25):  # allow slight over-budget for exceptional classification
                    continue

                # Score the record
                PropertyScorer.calculate_score(record)
                candidates.append(record)
            except Exception as e:
                logger.warning(f"Error normalizing item {item.get('title')}: {e}")

        return candidates, sources_checked, raw_found_count
