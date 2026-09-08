from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class PropertyRecord:
    id: Optional[int] = None
    canonical_id: Optional[str] = None
    source: str = ""
    source_property_id: str = ""
    url: str = ""
    title: str = ""
    property_type: str = ""  # 1+0, 1+1, Studio, Dormitory
    rooms: str = ""
    price: float = 0.0
    currency: str = "TL"
    effective_monthly_price: float = 0.0
    area_m2: Optional[float] = None
    furnished: bool = True
    location: str = ""  # e.g. Beşyol, Florya
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metrobus_station: Optional[str] = None
    metrobus_distance_min: Optional[int] = None
    university_distance_min: Optional[int] = None
    university_travel_mode: str = "walk"
    floor: Optional[str] = None
    building_age: Optional[int] = None
    elevator: Optional[bool] = None
    heating: Optional[str] = None
    internet_included: Optional[bool] = None
    aidat: Optional[float] = None
    deposit: Optional[float] = None
    agency_fee: Optional[str] = None
    student_allowed: bool = True
    foreigner_allowed: bool = True
    landlord_name: Optional[str] = None
    phone_if_public: Optional[str] = None
    listing_date: Optional[str] = None
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_price_change: Optional[str] = None
    status: str = "active"  # active, removed, price_reduced
    score: int = 0
    verification_status: str = "LIKELY"  # VERIFIED, LIKELY, NEEDS_VERIFICATION, SUSPICIOUS
    description: str = ""
    source_urls: List[str] = field(default_factory=list)

@dataclass
class PriceHistoryRecord:
    id: Optional[int] = None
    property_id: int = 0
    old_price: float = 0.0
    new_price: float = 0.0
    changed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class SearchRunRecord:
    run_id: Optional[int] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None
    sources_checked: int = 0
    listings_found: int = 0
    new_listings: int = 0
    price_changes: int = 0
    errors: int = 0
    log_summary: str = ""

@dataclass
class NotificationRecord:
    id: Optional[int] = None
    property_id: int = 0
    notification_type: str = "NEW_LISTING"  # NEW_LISTING, PRICE_REDUCTION, DAILY_REPORT
    sent_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    channel: str = "telegram"
    status: str = "sent"  # sent, failed, pending
