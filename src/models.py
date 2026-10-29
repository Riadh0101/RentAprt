"""Data structures passed between pipeline stages."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Furnishing codes
UNFURNISHED, FURNISHED, PARTIAL = 0, 1, 2


@dataclass
class FeedItem:
    """A listing as summarised on a portal search page."""
    source: str
    source_id: str
    url: str
    title: str = ""
    price: Optional[float] = None
    rooms: Optional[str] = None
    area_m2: Optional[float] = None
    location: str = ""
    date_posted: Optional[str] = None
    feed_label: str = ""


@dataclass
class ListingDetail:
    """Data extracted from an individual listing page."""
    title: str
    price: float
    currency: str = "TRY"
    description: str = ""
    rooms: Optional[str] = None
    area_m2: Optional[float] = None
    furnished: Optional[int] = None
    elevator: Optional[bool] = None
    balcony: Optional[bool] = None
    heating: str = ""
    aidat: Optional[float] = None
    deposit: Optional[float] = None
    building_age: Optional[int] = None
    floor: str = ""
    neighborhood: str = ""
    district: str = ""
    updated_date: Optional[str] = None
    photos: List[str] = field(default_factory=list)


@dataclass
class Listing:
    """A normalised, scored listing ready to persist."""
    source: str
    source_id: str
    url: str
    title: str
    price: float
    effective_cost: float
    rooms: Optional[str] = None
    area_m2: Optional[float] = None
    furnished: Optional[int] = None
    elevator: Optional[bool] = None
    balcony: Optional[bool] = None
    heating: str = ""
    aidat: Optional[float] = None
    deposit: Optional[float] = None
    building_age: Optional[int] = None
    bills_included: bool = False
    floor: str = ""
    neighborhood: str = ""
    district: str = ""
    description: str = ""
    photos: List[str] = field(default_factory=list)
    listing_date: Optional[str] = None
    updated_date: Optional[str] = None
    univ_walk_min: Optional[int] = None
    metrobus_station: Optional[str] = None
    metrobus_walk_min: Optional[int] = None
    score: int = 0
    score_breakdown: Dict[str, int] = field(default_factory=dict)
    classification: str = ""
    id: Optional[int] = None

    @property
    def location(self) -> str:
        return ", ".join(p for p in (self.neighborhood, self.district) if p)


@dataclass
class CycleReport:
    started_at: str
    finished_at: str = ""
    feeds_checked: int = 0
    feeds_failed: int = 0
    candidates: int = 0
    rejected: int = 0
    verified: int = 0
    new: int = 0
    price_drops: int = 0
    price_increases: int = 0
    reactivated: int = 0
    removed: int = 0
    alerts_sent: int = 0
    errors: int = 0

    def summary(self) -> str:
        return (
            f"feeds {self.feeds_checked - self.feeds_failed}/{self.feeds_checked} ok, "
            f"candidates {self.candidates}, rejected {self.rejected}, verified {self.verified}, "
            f"new {self.new}, price drops {self.price_drops}, removed {self.removed}, "
            f"alerts {self.alerts_sent}, errors {self.errors}"
        )
