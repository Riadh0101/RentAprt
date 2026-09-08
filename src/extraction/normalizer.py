import re
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from ..db.models import PropertyRecord
from .distance import DistanceCalculator

class PropertyNormalizer:
    @staticmethod
    def generate_canonical_id(source: str, source_id: str, title: str, location: str, price: float, rooms: str) -> str:
        """
        Create a robust deduplication hash combining location, rooms, and price bracket or source ID.
        """
        if source_id:
            raw = f"{source}:{source_id}"
        else:
            norm_loc = re.sub(r'[^a-zA-Z0-9]', '', location.lower())
            norm_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:20])
            norm_rooms = rooms.replace(" ", "")
            # Round price to nearest 500 for slight variance across aggregators
            price_bucket = int(round(price / 500.0) * 500)
            raw = f"{norm_loc}:{norm_rooms}:{price_bucket}:{norm_title}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    @classmethod
    def normalize_price(cls, raw_item: Dict[str, Any]) -> float:
        """
        Calculate effective monthly price in Turkish Lira (TL).
        Handles daily, weekly, monthly rates, Airbnb/Booking taxes and discounts.
        """
        source = raw_item.get("source", "").lower()
        raw_price = raw_item.get("price", 0.0)
        currency = raw_item.get("currency", "TL").upper()
        
        # Currency conversion approximate exchange rate if in USD/EUR
        usd_rate = 34.0
        eur_rate = 37.0
        
        if currency == "USD" or "$" in str(raw_item.get("price_str", "")):
            raw_price = raw_price * usd_rate
        elif currency == "EUR" or "€" in str(raw_item.get("price_str", "")):
            raw_price = raw_price * eur_rate

        # Airbnb / Booking effective calculation
        if source in ["airbnb", "booking", "booking.com"]:
            # If price is daily, extrapolate to 30 days and apply 15% monthly discount estimate
            is_daily = raw_item.get("pricing_type", "monthly") == "daily" or raw_price < 5000
            if is_daily:
                base_month = raw_price * 30.0
                cleaning_fee = raw_item.get("cleaning_fee", 1200.0)
                service_fee = base_month * 0.12
                discount = base_month * 0.15  # monthly discount
                effective = (base_month + cleaning_fee + service_fee) - discount
                return round(effective, 2)
            else:
                cleaning = raw_item.get("cleaning_fee", 1000.0)
                return round(raw_price + cleaning, 2)

        return float(raw_price)

    @classmethod
    def normalize_rooms(cls, text: str) -> str:
        text_lower = (text or "").lower()
        if "1+0" in text_lower or "stüdyo" in text_lower or "studio" in text_lower:
            return "1+0"
        if "1+1" in text_lower:
            return "1+1"
        if "yurt" in text_lower or "dorm" in text_lower or "residence" in text_lower:
            return "Dormitory"
        if "2+1" in text_lower:
            return "2+1"
        return "1+0"  # default candidate

    @classmethod
    def normalize_furnished(cls, raw_item: Dict[str, Any]) -> bool:
        text = f"{raw_item.get('title', '')} {raw_item.get('description', '')} {raw_item.get('furnished_str', '')}".lower()
        if "eşyalı" in text or "esyali" in text or "furnished" in text or "mobilyalı" in text or "yurt" in text:
            return True
        if "eşyasız" in text or "unfurnished" in text or "boş" in text:
            return False
        return raw_item.get("furnished", True)

    @classmethod
    def normalize_record(cls, raw_item: Dict[str, Any]) -> PropertyRecord:
        source = raw_item.get("source", "WebSearch")
        source_id = str(raw_item.get("source_id", raw_item.get("id", "")))
        title = raw_item.get("title", "").strip()
        url = raw_item.get("url", "").strip()
        location = raw_item.get("location", "Beşyol")
        address = raw_item.get("address", location)
        
        price = float(raw_item.get("price", 0.0))
        effective_price = cls.normalize_price(raw_item)
        rooms = cls.normalize_rooms(f"{title} {raw_item.get('rooms', '')}")
        furnished = cls.normalize_furnished(raw_item)
        
        lat = raw_item.get("latitude")
        lon = raw_item.get("longitude")
        
        u_min, u_mode = DistanceCalculator.estimate_university_distance(f"{location} {address}", lat, lon)
        mb_min, mb_station = DistanceCalculator.estimate_metrobus_distance(f"{location} {address}", lat, lon)
        
        prop_type = "Studio / 1+0" if rooms == "1+0" else ("1+1 Apartment" if rooms == "1+1" else "Student Dormitory")
        
        canonical_id = cls.generate_canonical_id(source, source_id, title, location, effective_price, rooms)
        
        # Reliability & verification assessment
        verification = "LIKELY"
        if source in ["Özel Erkek Yurdu", "IAU Residence", "Hepsiemlak"]:
            verification = "VERIFIED"
        elif not url or not title or effective_price <= 0:
            verification = "NEEDS_VERIFICATION"

        record = PropertyRecord(
            canonical_id=canonical_id,
            source=source,
            source_property_id=source_id,
            url=url,
            title=title,
            property_type=prop_type,
            rooms=rooms,
            price=price if price > 0 else effective_price,
            currency="TL",
            effective_monthly_price=effective_price,
            area_m2=raw_item.get("area_m2", 35.0),
            furnished=furnished,
            location=location,
            address=address,
            latitude=lat,
            longitude=lon,
            metrobus_station=mb_station,
            metrobus_distance_min=mb_min,
            university_distance_min=u_min,
            university_travel_mode=u_mode,
            floor=str(raw_item.get("floor", "2")),
            building_age=int(raw_item.get("building_age", 5)),
            elevator=bool(raw_item.get("elevator", True)),
            heating=raw_item.get("heating", "Kombi (Doğalgaz)"),
            internet_included=bool(raw_item.get("internet_included", True if "yurt" in title.lower() else False)),
            aidat=raw_item.get("aidat", 500.0),
            deposit=raw_item.get("deposit", effective_price),
            agency_fee=raw_item.get("agency_fee", "1 Month" if "sahibinden" not in source.lower() else "None"),
            student_allowed=True,
            foreigner_allowed=True,
            landlord_name=raw_item.get("landlord_name", "Agent / Owner"),
            phone_if_public=raw_item.get("phone", ""),
            listing_date=raw_item.get("listing_date", datetime.utcnow().strftime("%d/%m/%Y")),
            status="active",
            verification_status=verification,
            description=raw_item.get("description", ""),
            source_urls=[url] if url else []
        )
        return record
