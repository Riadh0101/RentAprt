"""Normalisation, eligibility filtering and 0–100 scoring (see docs/ARCHITECTURE.md)."""
from datetime import date
from typing import Optional, Tuple

from . import geo
from .config import Settings
from .models import FURNISHED, PARTIAL, FeedItem, Listing, ListingDetail
from .textutil import contains_any, fold

# Listing text that rules the student out regardless of anything else
_HARD_RESTRICTIONS = (
    "öğrenciye verilmez", "öğrenci olmaz", "öğrenciye uygun değil", "öğrenciye kiralanmaz",
    "bekara verilmez", "bekar olmaz", "bekara uygun değil", "bekara kiralanmaz",
    "kız öğrenciye", "kız öğrenci", "bayan öğrenci", "sadece bayan",
)
# Family-only wording; overridden if the listing also says it suits students
_FAMILY_ONLY = (
    "sadece aile", "sadece ailelere", "aileye kiralanacak", "aileye verilecek",
    "aileye verilir", "evli çift",
)
_BILLS_INCLUDED = ("faturalar dahil", "fatura dahil", "faturalar kiraya dahil")
_GOOD_HEATING = ("kombi", "dogalgaz", "merkezi", "yerden")

CLASSIFICATIONS = (
    (90, "EXCEPTIONAL"), (85, "EXCELLENT"), (75, "VERY_GOOD"), (65, "GOOD"), (50, "POTENTIAL"),
)


def _text_furnishing(text: str) -> Optional[int]:
    folded = fold(text)
    if "yari esyali" in folded:
        return PARTIAL
    if "esyasiz" in folded:
        return 0
    if "esyali" in folded or "mobilyali" in folded or "furnished" in folded:
        return FURNISHED
    return None


def build_listing(item: FeedItem, detail: ListingDetail, settings: Settings) -> Listing:
    """Merge feed summary and page detail into a Listing with distance estimates."""
    text = f"{detail.title} {detail.description}"
    furnished = detail.furnished if detail.furnished is not None else _text_furnishing(text)
    feed_parts = [p.strip() for p in item.location.split(",")] if item.location else []
    neighborhood = detail.neighborhood or (feed_parts[0] if feed_parts else "")
    district = detail.district or (feed_parts[1] if len(feed_parts) > 1 else "")

    listing = Listing(
        source=item.source,
        source_id=item.source_id,
        url=item.url,
        title=detail.title or item.title,
        price=detail.price,
        effective_cost=detail.price + (detail.aidat or 0.0),
        rooms=detail.rooms or item.rooms,
        area_m2=detail.area_m2 or item.area_m2,
        furnished=furnished,
        elevator=detail.elevator,
        balcony=detail.balcony,
        heating=detail.heating,
        aidat=detail.aidat,
        deposit=detail.deposit,
        building_age=detail.building_age,
        bills_included=contains_any(fold(text), _BILLS_INCLUDED),
        floor=detail.floor,
        neighborhood=neighborhood,
        district=district,
        description=detail.description,
        photos=detail.photos,
        listing_date=item.date_posted,
        updated_date=detail.updated_date,
    )

    coords = geo.locate(neighborhood, item.location)
    if coords:
        listing.univ_walk_min = geo.campus_walk_minutes(*coords, settings.campus)
        listing.metrobus_station, listing.metrobus_walk_min = geo.nearest_station(*coords)
    return listing


def check_eligibility(listing: Listing, settings: Settings) -> Tuple[bool, str]:
    """Hard requirements; a failing listing is never stored or alerted."""
    if listing.price <= 0:
        return False, "missing price"
    if listing.effective_cost > settings.exceptional_budget_limit_tl:
        return False, f"cost {listing.effective_cost:,.0f} TL above {settings.exceptional_budget_limit_tl:,.0f} TL"
    if listing.rooms and listing.rooms not in settings.allowed_rooms:
        return False, f"room layout {listing.rooms} not allowed"
    text = fold(f"{listing.title} {listing.description}")
    if contains_any(text, _HARD_RESTRICTIONS):
        return False, "landlord excludes students / single male tenants"
    if contains_any(text, _FAMILY_ONLY) and "ogrenciye uygun" not in text:
        return False, "family-only listing"
    return True, "eligible"


def _location_points(listing: Listing) -> int:
    walk, metro = listing.univ_walk_min, listing.metrobus_walk_min
    if walk is None or metro is None:
        return 15  # neighbourhood unknown
    walk_pts = 40 if walk <= 5 else 37 if walk <= 10 else 32 if walk <= 20 else 25 if walk <= 30 else 0
    metro_pts = 35 if metro <= 5 else 32 if metro <= 10 else 28 if metro <= 15 else 20 if metro <= 20 else 10
    return max(walk_pts, metro_pts)


def _price_points(cost: float, budget: float) -> int:
    if cost > budget:
        return 0
    return 25 if cost <= 20000 else 20 if cost <= 25000 else 15 if cost <= 30000 else 10


def _quality_points(listing: Listing) -> int:
    pts = 0
    pts += 2 if listing.elevator else 0
    pts += 2 if any(h in fold(listing.heating) for h in _GOOD_HEATING) else 0
    pts += 2 if (listing.area_m2 or 0) >= 30 else 0
    pts += 2 if listing.building_age is not None and listing.building_age <= 10 else 0
    pts += 2 if listing.bills_included else 0
    pts += 1 if listing.balcony else 0
    pts += 1 if listing.rooms in ("1+0", "1+1") else 0
    return min(10, pts)


def _days_old(iso_date: Optional[str], today: date) -> Optional[int]:
    try:
        return (today - date.fromisoformat(iso_date)).days if iso_date else None
    except ValueError:
        return None


def _reliability_points(listing: Listing, today: date) -> int:
    pts = 3 if len(listing.photos) >= 3 else 1 if listing.photos else 0
    pts += 2 if len(listing.description) >= 80 else 0
    age = _days_old(listing.updated_date or listing.listing_date, today)
    pts += 3 if age is not None and age <= 7 else 1 if age is not None and age <= 30 else 0
    pts += 2 if listing.deposit is not None or listing.aidat is not None else 0
    return min(10, pts)


def score_listing(listing: Listing, settings: Settings, today: Optional[date] = None) -> Listing:
    """Fill score, score_breakdown and classification in place and return the listing."""
    today = today or date.today()
    furnishing = 15 if listing.furnished == FURNISHED else 8 if listing.furnished == PARTIAL else 0
    breakdown = {
        "location_transit": _location_points(listing),
        "price_budget": _price_points(listing.effective_cost, settings.max_budget_tl),
        "furnishing": furnishing,
        "quality_amenities": _quality_points(listing),
        "reliability_freshness": _reliability_points(listing, today),
    }
    total = sum(breakdown.values())
    classification = next((label for floor, label in CLASSIFICATIONS if total >= floor), "REJECT")
    if listing.effective_cost > settings.max_budget_tl and total >= settings.score_daily_digest:
        classification = "OVER_BUDGET_EXCEPTIONAL"

    listing.score = total
    listing.score_breakdown = breakdown
    listing.classification = classification
    return listing
