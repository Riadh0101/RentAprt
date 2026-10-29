import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings  # noqa: E402
from src.database import Database  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://www.emlakjet.com"


def listing_url(source_id: str, slug: str = "kiralik-daire") -> str:
    return f"{BASE}/ilan/{slug}-{source_id}"


def feed_html(entries: List[Dict]) -> str:
    """Search page in Emlakjet's JSON-LD shape. Entry keys: id, name, price, rooms, m2, konum, date."""
    graph = [{
        "@type": "RealEstateListing",
        "name": e.get("name", f"Kiralık {e.get('rooms', '1+1')} Daire"),
        "url": listing_url(e["id"]),
        "datePosted": e.get("date", "2026-10-25"),
        "offers": {"@type": "Offer", "url": listing_url(e["id"]), "price": e["price"],
                   "priceCurrency": "TRY", "availability": "https://schema.org/InStock"},
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Konum", "value": e.get("konum", "Beşyol Mahallesi, Küçükçekmece")},
            {"@type": "PropertyValue", "name": "Oda Sayısı", "value": e.get("rooms", "1+1")},
            {"@type": "PropertyValue", "name": "Metrekare", "value": f"{e.get('m2', 50)} m²"},
        ],
    } for e in entries]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return f'<html><head><title>Feed</title><script type="application/ld+json">{ld}</script></head></html>'


def listing_html(source_id: str, price: float, name: str = "Beşyol Eşyalı 1+1 Kiralık Daire",
                 description: str = "Aydın Üniversitesi'ne yürüme mesafesinde, temiz, bakımlı, kombili, "
                                    "eşyalı daire. Öğrenciye uygundur. Metrobüse çok yakın.",
                 rooms_title: str = "1+1 Oda", furnished: str = "Eşyalı", aidat: str = "500 TL",
                 deposit: str = "30000 TL", elevator: str = "Var", heating: str = "Kombi Doğalgaz",
                 street: str = "Beşyol Mahallesi", locality: str = "Küçükçekmece",
                 updated: str = "28 Ekim 2026", availability: str = "InStock", m2: int = 50,
                 images: int = 4) -> str:
    url = listing_url(source_id)
    graph = [
        {"@type": "Product", "url": url, "name": name, "description": description,
         "image": [f"https://imaj.emlakjet.com/listing/{source_id}/{i}.jpg" for i in range(images)],
         "offers": {"@type": "Offer", "url": url, "price": price, "priceCurrency": "TRY",
                    "availability": f"https://schema.org/{availability}"}},
        {"@type": "RealEstateListing", "@id": url + "#listing", "dateModified": "2026-10-28T10:00:00+03:00",
         "itemOffered": {"@type": "Residence",
                         "floorSize": {"@type": "QuantitativeValue", "value": m2, "unitCode": "MTK"},
                         "additionalProperty": [
                             {"@type": "PropertyValue", "name": "İlan Güncelleme Tarihi", "value": updated},
                             {"@type": "PropertyValue", "name": "Isıtma Tipi", "value": heating},
                             {"@type": "PropertyValue", "name": "Kullanım Durumu", "value": "Boş"},
                             {"@type": "PropertyValue", "name": "Aidat", "value": aidat},
                             {"@type": "PropertyValue", "name": "Depozito", "value": deposit},
                             {"@type": "PropertyValue", "name": "Asansör", "value": elevator},
                             {"@type": "PropertyValue", "name": "Eşya Durumu", "value": furnished},
                         ]},
         "address": {"@type": "PostalAddress", "streetAddress": street, "addressLocality": locality,
                     "addressRegion": "İstanbul"}},
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    title = f"İstanbul {locality} {street} {rooms_title} Kiralık Daire {price:,.0f} TL"
    return f'<html><head><title>{title}</title><script type="application/ld+json">{ld}</script></head></html>'


class FakeSite:
    """Routes requests to in-memory pages; records every request URL."""

    def __init__(self):
        self.feeds: Dict[str, str] = {}      # feed slug fragment -> html
        self.listings: Dict[str, Callable[[], httpx.Response]] = {}
        self.requests: List[str] = []
        self.feed_status = 200

    def set_listing(self, source_id: str, html: Optional[str] = None, status: int = 200,
                    redirect_home: bool = False):
        def respond(request: httpx.Request) -> httpx.Response:
            if redirect_home:
                return httpx.Response(302, headers={"Location": BASE + "/"})
            return httpx.Response(status, text=html or "")
        self.listings[source_id] = respond

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if url == BASE + "/":
            return httpx.Response(200, text="<html><head><title>Emlakjet</title></head></html>")
        if "/kiralik-daire/" in url:
            if self.feed_status != 200:
                return httpx.Response(self.feed_status)
            for fragment, html in self.feeds.items():
                if fragment in url:
                    return httpx.Response(200, text=html)
            return httpx.Response(200, text=feed_html([]))
        if "/ilan/" in url:
            source_id = url.rstrip("/").rsplit("-", 1)[-1]
            if source_id in self.listings:
                return self.listings[source_id](request)
            return httpx.Response(404)
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), follow_redirects=True)


@pytest.fixture
def env() -> Dict[str, str]:
    return {}


@pytest.fixture
def settings(tmp_path, env):
    return load_settings(env={"REQUEST_DELAY_SECONDS": "0", **env}, base_dir=tmp_path)


@pytest.fixture
def db(settings) -> Database:
    return Database(settings.db_path)


@pytest.fixture
def site() -> FakeSite:
    return FakeSite()
