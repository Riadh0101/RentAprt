from ..db.models import PropertyRecord

class PropertyScorer:
    @classmethod
    def calculate_score(cls, prop: PropertyRecord) -> int:
        """
        Computes 0–100 accommodation score for student requirements.
        """
        location_score = cls._score_location(prop)
        price_score = cls._score_price(prop)
        furnishing_score = cls._score_furnishing(prop)
        quality_score = cls._score_quality(prop)
        reliability_score = cls._score_reliability(prop)

        total = location_score + price_score + furnishing_score + quality_score + reliability_score
        
        # Clamp to 0 - 100
        prop.score = max(0, min(100, int(round(total))))
        return prop.score

    @classmethod
    def _score_location(cls, prop: PropertyRecord) -> float:
        """Location & Transit (Max 40 points)."""
        u_min = prop.university_distance_min or 30
        mb_min = prop.metrobus_distance_min or 15
        mode = prop.university_travel_mode

        if mode == "walk" or u_min <= 10:
            if u_min <= 5:
                return 40.0
            elif u_min <= 10:
                return 37.0
            elif u_min <= 20:
                return 32.0
            else:
                return 25.0
        
        # Metrobus proximity
        if mb_min <= 5:
            return 35.0
        elif mb_min <= 10:
            return 30.0
        elif mb_min <= 15:
            return 25.0
        elif u_min <= 35:
            return 20.0
        else:
            return 12.0

    @classmethod
    def _score_price(cls, prop: PropertyRecord) -> float:
        """Price vs Budget (Max 25 points). Target <= 36,000 TL."""
        p = prop.effective_monthly_price or prop.price

        if p <= 0:
            return 0.0
        if p <= 20000:
            return 25.0
        elif p <= 25000:
            return 20.0
        elif p <= 30000:
            return 15.0
        elif p <= 36000:
            return 10.0
        else:
            return 0.0  # Over budget

    @classmethod
    def _score_furnishing(cls, prop: PropertyRecord) -> float:
        """Furnished status (Max 15 points)."""
        if prop.furnished:
            return 15.0
        return 0.0

    @classmethod
    def _score_quality(cls, prop: PropertyRecord) -> float:
        """Quality & Amenities (Max 10 points)."""
        score = 5.0  # base
        if prop.elevator:
            score += 1.5
        if prop.heating and ("kombi" in prop.heating.lower() or "doğalgaz" in prop.heating.lower() or "central" in prop.heating.lower()):
            score += 1.5
        if prop.internet_included:
            score += 1.0
        if prop.building_age is not None and prop.building_age <= 10:
            score += 1.0
        if prop.area_m2 and prop.area_m2 >= 30:
            score += 1.0
        return min(10.0, score)

    @classmethod
    def _score_reliability(cls, prop: PropertyRecord) -> float:
        """Reliability & Freshness (Max 10 points)."""
        score = 5.0
        if prop.verification_status == "VERIFIED":
            score += 3.0
        elif prop.verification_status == "LIKELY":
            score += 2.0
        elif prop.verification_status == "SUSPICIOUS":
            score -= 3.0
            
        if prop.phone_if_public:
            score += 1.0
        if prop.url and "http" in prop.url:
            score += 1.0
        return max(0.0, min(10.0, score))
