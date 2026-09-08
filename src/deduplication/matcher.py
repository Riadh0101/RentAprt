import difflib
from typing import List, Optional, Tuple
from ..db.models import PropertyRecord

class DeduplicationMatcher:
    @classmethod
    def calculate_similarity(cls, a: PropertyRecord, b: PropertyRecord) -> float:
        """
        Calculate matching confidence score (0.0 to 1.0) between two property records.
        """
        if a.canonical_id and b.canonical_id and a.canonical_id == b.canonical_id:
            return 1.0
        if a.url and b.url and a.url == b.url:
            return 1.0
        if a.source_property_id and b.source_property_id and a.source_property_id == b.source_property_id and a.source == b.source:
            return 1.0

        score = 0.0

        # Location similarity (weight: 0.3)
        loc_a = (a.location or "").lower()
        loc_b = (b.location or "").lower()
        if loc_a == loc_b and loc_a != "":
            score += 0.3
        elif loc_a in loc_b or loc_b in loc_a:
            score += 0.2

        # Price similarity (weight: 0.3)
        pa = a.effective_monthly_price or a.price
        pb = b.effective_monthly_price or b.price
        if pa > 0 and pb > 0:
            ratio = min(pa, pb) / max(pa, pb)
            if ratio >= 0.95:
                score += 0.3
            elif ratio >= 0.90:
                score += 0.2
            elif ratio >= 0.80:
                score += 0.1

        # Room configuration (weight: 0.2)
        if a.rooms and b.rooms and a.rooms == b.rooms:
            score += 0.2

        # Title / Description text similarity (weight: 0.2)
        seq = difflib.SequenceMatcher(None, (a.title or "").lower(), (b.title or "").lower())
        title_sim = seq.ratio()
        score += title_sim * 0.2

        return round(score, 2)

    @classmethod
    def find_duplicate(cls, candidate: PropertyRecord, existing_list: List[PropertyRecord], threshold: float = 0.80) -> Optional[Tuple[PropertyRecord, float]]:
        for existing in existing_list:
            sim = cls.calculate_similarity(candidate, existing)
            if sim >= threshold:
                return existing, sim
        return None
