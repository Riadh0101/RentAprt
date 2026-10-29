from datetime import date

import pytest

from src.config import load_settings
from src.models import FeedItem
from src.scoring import build_listing, check_eligibility, score_listing
from src.scraper import parse_listing
from tests.conftest import listing_html, listing_url

TODAY = date(2026, 10, 30)


def make(settings, source_id="1", price=20000, konum="Beşyol Mahallesi, Küçükçekmece", **page):
    item = FeedItem(source="Emlakjet", source_id=source_id, url=listing_url(source_id),
                    price=price, location=konum, date_posted="2026-10-20")
    _, detail, _ = parse_listing(listing_html(source_id, price, **page), item.url)
    return build_listing(item, detail, settings)


def test_prime_besyol_listing_scores_excellent(settings):
    listing = score_listing(make(settings, price=19000, aidat="0 TL"), settings, TODAY)
    b = listing.score_breakdown
    assert b["location_transit"] == 40
    assert b["price_budget"] == 25
    assert b["furnishing"] == 15
    assert listing.score >= 85
    assert listing.classification in ("EXCELLENT", "EXCEPTIONAL")
    assert listing.metrobus_station == "Beşyol"


def test_effective_cost_includes_aidat(settings):
    listing = make(settings, price=19800, aidat="1.000 TL")
    assert listing.effective_cost == 20800
    assert score_listing(listing, settings, TODAY).score_breakdown["price_budget"] == 20


def test_unfurnished_and_far_listing_scores_lower(settings):
    near = score_listing(make(settings, price=25000), settings, TODAY)
    far = score_listing(make(settings, "2", price=25000, furnished="Eşyasız",
                             street="Avcılar Merkez", locality="Avcılar", konum="Avcılar"), settings, TODAY)
    assert far.score_breakdown["furnishing"] == 0
    assert far.score_breakdown["location_transit"] < near.score_breakdown["location_transit"]
    assert far.score < near.score


def test_unknown_mahalle_is_not_guessed_from_district(settings):
    listing = score_listing(make(settings, street="Mehmet Akif Mahallesi",
                                 konum="Mehmet Akif Mahallesi, Küçükçekmece"), settings, TODAY)
    assert listing.univ_walk_min is None and listing.metrobus_walk_min is None
    assert listing.score_breakdown["location_transit"] == 15


def test_over_budget_classification(settings):
    listing = score_listing(make(settings, price=39000, aidat="0 TL"), settings, TODAY)
    assert listing.score_breakdown["price_budget"] == 0
    assert listing.classification == "OVER_BUDGET_EXCEPTIONAL"


def test_reliability_rewards_fresh_complete_listings(settings):
    fresh = score_listing(make(settings), settings, TODAY)
    stale = score_listing(make(settings, "2", updated="1 Ocak 2026", images=0, description="Kiralık."),
                          settings, TODAY)
    assert fresh.score_breakdown["reliability_freshness"] == 10
    assert stale.score_breakdown["reliability_freshness"] == 2  # only aidat/deposit disclosed


def test_bills_included_detected(settings):
    listing = make(settings, name="Aydın Üni Yanı Eşyalı FATURALAR DAHİL 1+0 Daire")
    assert listing.bills_included


@pytest.mark.parametrize("description, reason", [
    ("SADECE AİLEYE KİRALIKTIR.", "family-only listing"),
    ("Öğrenciye verilmez, temiz daire.", "landlord excludes students / single male tenants"),
    ("Bekara verilmez.", "landlord excludes students / single male tenants"),
    ("Kız öğrenciye uygundur.", "landlord excludes students / single male tenants"),
])
def test_restrictions_rejected(settings, description, reason):
    ok, why = check_eligibility(make(settings, description=description), settings)
    assert not ok and why == reason


def test_family_wording_allowed_when_students_welcome(settings):
    listing = make(settings, description="Aileye verilecek ama öğrenciye uygun, eşyalı daire.")
    assert check_eligibility(listing, settings) == (True, "eligible")


def test_room_and_price_limits(settings):
    ok, why = check_eligibility(make(settings, rooms_title="3+1 Oda", name="Geniş 3+1"), settings)
    assert not ok and "3+1" in why
    ok, why = check_eligibility(make(settings, price=45000), settings)
    assert not ok and "above" in why


def test_allowed_rooms_configurable(tmp_path):
    strict = load_settings(env={"ALLOWED_ROOMS": "1+0,1+1"}, base_dir=tmp_path)
    ok, _ = check_eligibility(make(strict, rooms_title="2+1 Oda", name="Geniş 2+1"), strict)
    assert not ok
