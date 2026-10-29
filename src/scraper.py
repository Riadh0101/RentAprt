"""Emlakjet scraping: neighbourhood feeds and individual listing pages (via schema.org JSON-LD)."""
import json
import logging
import re
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from .config import Settings
from .models import FURNISHED, PARTIAL, UNFURNISHED, FeedItem, ListingDetail
from .textutil import fold, normalize_rooms, parse_number

logger = logging.getLogger(__name__)

SOURCE = "Emlakjet"
BASE_URL = "https://www.emlakjet.com"

ACTIVE, INACTIVE = "ACTIVE", "INACTIVE"

_REMOVED_MARKERS = ("yayında değildir", "yayından kaldırılmıştır", "ilan süresi dolmuştur")
_NOT_FOUND_TITLES = ("404", "sayfa bulunamadı", "aradığınız ilan")
_TR_MONTHS = {
    "ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6,
    "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12,
}
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    """Raised when a page cannot be fetched after retries."""


def source_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"/ilan/[^?#]*?-(\d+)/?(?:[?#]|$)", url)
    return match.group(1) if match else None


def parse_turkish_date(text: Optional[str]) -> Optional[str]:
    """'12 Ekim 2026' or '2026-10-12T17:12:47+03:00' -> '2026-10-12'."""
    if not text:
        return None
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return iso.group(0)
    match = re.match(r"(\d{1,2})\s+(\S+)\s+(\d{4})", fold(text))
    if match and match.group(2) in _TR_MONTHS:
        return f"{match.group(3)}-{_TR_MONTHS[match.group(2)]:02d}-{int(match.group(1)):02d}"
    return None


def _json_ld_nodes(soup: BeautifulSoup) -> Iterator[Dict[str, Any]]:
    """Yield every JSON-LD object on the page, flattening @graph containers."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in data if isinstance(data, list) else [data]:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                yield from (g for g in graph if isinstance(g, dict))
            else:
                yield node


def _properties(node: Dict[str, Any]) -> Dict[str, Any]:
    """additionalProperty list -> {folded name: value}."""
    props = node.get("additionalProperty") or []
    return {fold(p.get("name")): p.get("value") for p in props if isinstance(p, dict)}


def parse_feed(html: str, feed_label: str = "") -> List[FeedItem]:
    """Extract listing summaries from a search/category page's JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")
    items: List[FeedItem] = []
    for node in _json_ld_nodes(soup):
        if node.get("@type") != "RealEstateListing":
            continue
        url = node.get("url") or (node.get("offers") or {}).get("url") or ""
        source_id = source_id_from_url(url)
        if not source_id:
            continue
        props = _properties(node)
        items.append(FeedItem(
            source=SOURCE,
            source_id=source_id,
            url=url,
            title=node.get("name", ""),
            price=parse_number((node.get("offers") or {}).get("price")),
            rooms=normalize_rooms(props.get("oda sayisi")) or normalize_rooms(node.get("name")),
            area_m2=parse_number(props.get("metrekare")),
            location=props.get("konum") or "",
            date_posted=parse_turkish_date(node.get("datePosted")),
            feed_label=feed_label,
        ))
    return items


def _furnishing(value: Optional[str]) -> Optional[int]:
    folded = fold(value)
    if not folded:
        return None
    if "yari" in folded or "kismen" in folded:
        return PARTIAL
    if "esyasiz" in folded or "mobilyasiz" in folded:
        return UNFURNISHED
    if "esyali" in folded or "mobilyali" in folded:
        return FURNISHED
    if folded == "bos":  # "Eşya Durumu: Boş" = no furniture
        return UNFURNISHED
    return None


def _yes_no(value: Optional[str]) -> Optional[bool]:
    folded = fold(value)
    if folded in ("var", "evet"):
        return True
    if folded in ("yok", "hayir"):
        return False
    return None


def parse_listing(html: str, final_url: str) -> Tuple[str, Optional[ListingDetail], str]:
    """Parse a listing page. Returns (ACTIVE | INACTIVE, detail, reason)."""
    if "/ilan/" not in final_url:
        return INACTIVE, None, "redirected away from the listing page"

    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(strip=True) if soup.title else ""
    if any(m in page_title.lower() for m in _NOT_FOUND_TITLES):
        return INACTIVE, None, "listing page not found"
    lowered = html.lower()
    if any(m in lowered for m in _REMOVED_MARKERS):
        return INACTIVE, None, "listing marked as removed or expired"

    product, estate = None, None
    for node in _json_ld_nodes(soup):
        if node.get("@type") == "Product" and product is None:
            product = node
        elif node.get("@type") == "RealEstateListing" and estate is None:
            estate = node
    if product is None:
        return INACTIVE, None, "no structured listing data on page"

    offer = product.get("offers") or {}
    if "OutOfStock" in str(offer.get("availability", "")):
        return INACTIVE, None, "listing is no longer available (OutOfStock)"
    price = parse_number(offer.get("price"))
    if not price:
        return INACTIVE, None, "listing has no price"

    estate = estate or {}
    offered = estate.get("itemOffered") or {}
    props = _properties(offered)
    address = estate.get("address") or {}
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
    age = parse_number(props.get("bina yasi"))

    detail = ListingDetail(
        title=product.get("name", "").strip(),
        price=price,
        currency=offer.get("priceCurrency", "TRY"),
        description=(product.get("description") or "").strip(),
        rooms=normalize_rooms(page_title) or normalize_rooms(product.get("name")),
        area_m2=parse_number((offered.get("floorSize") or {}).get("value")),
        furnished=_furnishing(props.get("esya durumu")),
        elevator=_yes_no(props.get("asansor")),
        balcony=_yes_no(props.get("balkon")),
        heating=props.get("isitma tipi") or "",
        aidat=parse_number(props.get("aidat")),
        deposit=parse_number(props.get("depozito")),
        building_age=int(age) if age is not None else None,
        floor=str(props.get("bulundugu kat") or props.get("kat") or ""),
        neighborhood=(address.get("streetAddress") or "").strip(),
        district=(address.get("addressLocality") or "").strip(),
        updated_date=parse_turkish_date(props.get("ilan guncelleme tarihi"))
        or parse_turkish_date(estate.get("dateModified")),
        photos=[i for i in images if isinstance(i, str)][:5],
    )
    return ACTIVE, detail, "active"


class EmlakjetClient:
    """HTTP access to Emlakjet with retries and a polite delay between requests."""

    def __init__(self, settings: Settings, http: Optional[httpx.Client] = None,
                 sleep=time.sleep, retries: int = 2):
        self.settings = settings
        self.http = http or httpx.Client(
            headers={
                "User-Agent": settings.user_agent,
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )
        self._sleep = sleep
        self._retries = retries
        self._last_request = 0.0

    def close(self):
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _get(self, url: str) -> httpx.Response:
        last_error = ""
        for attempt in range(self._retries + 1):
            wait = self.settings.request_delay_seconds - (time.monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self.http.get(url)
            except httpx.HTTPError as e:
                last_error = f"{type(e).__name__}: {e}"
            else:
                if resp.status_code not in _RETRY_STATUSES:
                    return resp
                last_error = f"HTTP {resp.status_code}"
            if attempt < self._retries:
                self._sleep(2 ** attempt * 2)
        raise FetchError(f"{url}: {last_error}")

    def fetch_feed(self, url: str, label: str = "") -> List[FeedItem]:
        resp = self._get(url)
        if resp.status_code != 200:
            raise FetchError(f"{url}: HTTP {resp.status_code}")
        return parse_feed(resp.text, label)

    def fetch_listing(self, url: str) -> Tuple[str, Optional[ListingDetail], str]:
        resp = self._get(url)
        if resp.status_code in (404, 410):
            return INACTIVE, None, f"HTTP {resp.status_code}"
        if resp.status_code != 200:
            raise FetchError(f"{url}: HTTP {resp.status_code}")
        return parse_listing(resp.text, str(resp.url))
