import httpx
import pytest

from src import geo
from src.models import FURNISHED, PARTIAL, UNFURNISHED
from src.scraper import (ACTIVE, INACTIVE, EmlakjetClient, FetchError, parse_feed, parse_listing,
                         parse_turkish_date, source_id_from_url)
from src.textutil import fold, normalize_rooms, parse_number
from tests.conftest import FIXTURES, listing_html, listing_url


def test_fold_handles_turkish_dotted_capital_i():
    assert "sadece aile" in fold("SADECE AİLEYE KİRALIKTIR")
    assert fold("Öğrenciye Uygun Eşyalı") == "ogrenciye uygun esyali"


@pytest.mark.parametrize("text, expected", [
    ("35.000 TL", 35000.0), ("1,200 TL", 1200.0), ("75 m²", 75.0), (30000, 30000.0),
    ("0 TL", 0.0), ("", None), (None, None),
])
def test_parse_number(text, expected):
    assert parse_number(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Beşyolda 2+1eşyalı daire", "2+1"), ("1 + 0 stüdyo", "1+0"), ("Stüdyo", "1+0"),
    ("Kiralık daire", None),
])
def test_normalize_rooms(text, expected):
    assert normalize_rooms(text) == expected


def test_turkish_dates():
    assert parse_turkish_date("12 Ekim 2026") == "2026-10-12"
    assert parse_turkish_date("3 Ağustos 2026") == "2026-08-03"
    assert parse_turkish_date("2026-10-28T10:33:57+03:00") == "2026-10-28"
    assert parse_turkish_date("yesterday") is None


def test_source_id_from_url():
    assert source_id_from_url(listing_url("19797604", "esyali-10-kiralik-daire")) == "19797604"
    assert source_id_from_url("https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece") is None


def test_parse_real_feed_fixture():
    items = parse_feed((FIXTURES / "emlakjet_feed_besyol.html").read_text(encoding="utf-8"), "Beşyol")
    by_id = {i.source_id: i for i in items}
    assert set(by_id) == {"19920711", "19797604"}
    studio = by_id["19797604"]
    assert studio.price == 30000 and studio.rooms == "1+0" and studio.area_m2 == 50
    assert studio.location == "Beşyol Mahallesi, Küçükçekmece"
    assert by_id["19920711"].rooms == "2+1"


def test_parse_real_listing_fixture():
    html = (FIXTURES / "emlakjet_listing_19797604.html").read_text(encoding="utf-8")
    status, d, _ = parse_listing(html, listing_url("19797604"))
    assert status == ACTIVE
    assert d.price == 30000 and d.rooms == "1+0" and d.area_m2 == 50
    assert d.furnished == FURNISHED          # from "Eşya Durumu", not "Kullanım Durumu: Boş"
    assert d.elevator is True and d.aidat == 0 and d.deposit == 30000
    assert d.neighborhood == "Beşyol Mahallesi" and d.district == "Küçükçekmece"
    assert d.updated_date == "2026-10-28"
    assert len(d.photos) == 5


@pytest.mark.parametrize("value, expected", [
    ("Eşyalı", FURNISHED), ("Yarı Eşyalı", PARTIAL), ("Eşyasız", UNFURNISHED), ("Boş", UNFURNISHED),
    ("", None),
])
def test_furnishing_values(value, expected):
    _, d, _ = parse_listing(listing_html("1", 20000, furnished=value), listing_url("1"))
    assert d.furnished == expected


def test_inactive_listings():
    assert parse_listing(listing_html("1", 20000, availability="OutOfStock"), listing_url("1"))[0] == INACTIVE
    assert parse_listing(listing_html("1", 20000), "https://www.emlakjet.com/")[0] == INACTIVE
    removed = "<html><head><title>x</title></head><body>Bu ilan yayında değildir</body></html>"
    assert parse_listing(removed, listing_url("1"))[0] == INACTIVE
    assert parse_listing("<html><title>Sayfa Bulunamadı</title></html>", listing_url("1"))[0] == INACTIVE


def test_client_retries_then_raises(settings):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = EmlakjetClient(settings, http=http, sleep=lambda s: None, retries=2)
    with pytest.raises(FetchError):
        client.fetch_feed("https://www.emlakjet.com/kiralik-daire/x")
    assert len(calls) == 3


def test_client_404_listing_is_inactive(settings, site):
    client = EmlakjetClient(settings, http=site.client(), sleep=lambda s: None)
    assert client.fetch_listing(listing_url("999"))[0] == INACTIVE


def test_geo_locates_neighbourhood_and_walk_times(settings):
    coords = geo.locate("Beşyol Mahallesi", "Küçükçekmece")
    assert coords == geo.NEIGHBORHOOD_COORDS["besyol"]
    assert geo.campus_walk_minutes(*coords, settings.campus) <= 10
    station, minutes = geo.nearest_station(*coords)
    assert station == "Beşyol" and minutes <= 5
    assert geo.locate("Unknown place") is None
    far = geo.locate("Avcılar")
    assert geo.campus_walk_minutes(*far, settings.campus) > 60
