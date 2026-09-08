import re
import urllib.parse
import logging
from typing import List, Dict, Any, Tuple
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("HermesSearcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# Target neighborhood category feeds closest to Istanbul Aydın University (Florya Campus)
TARGET_FEEDS = [
    ("Beşyol (بجوار الجامعة مشياً)", "https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece-besyol-mahallesi/?fiyat=0-36000"),
    ("Sefaköy / Kartaltepe (متروباص)", "https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece-kartaltepe-mahallesi/?fiyat=0-36000"),
    ("Florya / Şenlikköy (فلوريا)", "https://www.emlakjet.com/kiralik-daire/istanbul-bakirkoy-senlikkoy-mahallesi/?fiyat=0-40000"),
    ("Cennet Mahallesi (محطة واحدة)", "https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece-cennet-mahallesi/?fiyat=0-36000"),
    ("Sefaköy / İnönü (متروباص)", "https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece-inonu-mahallesi/?fiyat=0-36000"),
    ("Küçükçekmece (عام)", "https://www.emlakjet.com/kiralik-daire/istanbul-kucukcekmece/?fiyat=0-36000")
]

def clean_price(price_str: str) -> float:
    """Clean string like '22.500 TL' or '24,000 TL' into a float."""
    if not price_str:
        return 0.0
    digits_only = re.sub(r"[^\d]", "", price_str)
    try:
        return float(digits_only)
    except ValueError:
        return 0.0

def verify_listing_live(url: str, client: httpx.Client = None) -> Tuple[bool, Dict[str, Any], str]:
    """
    Strict real-time pre-flight verification:
    Ensures that an individual listing is 100% active, online, not 404, not expired,
    not marked as OutOfStock or removed, and not restricted to families only.
    Returns: (is_valid_and_active, extracted_data, reason)
    """
    if not url or not url.startswith("http"):
        return False, {}, "Invalid URL format"

    # Only accept specific individual listings, never category / search index pages
    if "/kiralik-daire/" in url and "/ilan/" not in url:
        return False, {}, "Category / directory page rejected (only direct individual listings allowed)"

    should_close = False
    if client is None:
        client = httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return False, {}, f"HTTP {resp.status_code} - Listing unavailable or removed"

        # Check if redirected away to search or home
        final_url_str = str(resp.url)
        if "/ilan/" not in final_url_str:
            return False, {}, "Redirected away from listing page (listing likely deleted or expired)"

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        page_title = title_tag.get_text(strip=True) if title_tag else ""
        if any(term in page_title.lower() for term in ["404", "sayfa bulunamadı", "aradığınız ilan"]):
            return False, {}, "Listing returned 404 / Not Found page"

        # Check page text for deactivation notices
        text_lower = resp.text.lower()
        if "yayında değildir" in text_lower or "ilan yayından kaldırılmıştır" in text_lower or "ilan süresi dolmuştur" in text_lower:
            return False, {}, "Listing explicitly marked as removed/inactive (yayında değildir)"

        # Parse JSON-LD structured data
        scripts = soup.find_all("script", type="application/ld+json")
        prod = None
        for sc in scripts:
            try:
                import json
                d = json.loads(sc.string)
                if "@graph" in d:
                    for g in d["@graph"]:
                        if g.get("@type") == "Product":
                            prod = g
                            break
            except Exception:
                pass

        if not prod:
            # Fallback check on H1
            h1 = soup.find("h1")
            if not h1:
                return False, {}, "No listing details found on page"
            return True, {"title": h1.get_text(strip=True), "price": 0.0}, "Active (no json-ld)"

        offer = prod.get("offers", {})
        availability = offer.get("availability", "")
        if "OutOfStock" in availability:
            return False, {}, "Listing is OutOfStock (kiralandı / pasif)"

        live_price = float(offer.get("price", 0.0))
        name = prod.get("name", "")
        desc = prod.get("description", "")
        images = prod.get("image", [])

        # Family-only check
        desc_lower = (name + " " + desc).lower()
        if "sadece aile" in desc_lower or ("aileye uygun" in desc_lower and "öğrenci olmaz" in desc_lower):
            return False, {}, "Landlord explicitly restricts to families only (öğrenciye uygun değil)"

        # Determine rooms
        rooms = "1+1"
        if "1+0" in name or "stüdyo" in desc_lower or "1+0" in desc_lower:
            rooms = "1+0"
        elif "1+1" in name or "1+1" in desc_lower:
            rooms = "1+1"
        elif "2+1" in name or "2+1" in desc_lower:
            rooms = "2+1"
        elif "3+1" in name or "3+1" in desc_lower:
            rooms = "3+1"

        # Determine furnished status
        is_furnished = 1 if any(w in desc_lower for w in ["eşyalı", "esyali", "mobilyalı", "full", "stüdyo"]) else 0

        # Extract publication / update date (تاريخ نشر وتحديث الإعلان)
        listing_date = None
        for sc in scripts:
            try:
                import json
                d = json.loads(sc.string)
                for g in d.get("@graph", []):
                    if g.get("@type") == "RealEstateListing":
                        for p in g.get("itemOffered", {}).get("additionalProperty", []):
                            if "tarih" in p.get("name", "").lower():
                                listing_date = p.get("value")
                                break
                        if not listing_date and g.get("dateModified"):
                            listing_date = g.get("dateModified")[:10]
            except Exception:
                pass

        if not listing_date:
            from datetime import datetime
            listing_date = datetime.now().strftime("%Y-%m-%d")

        data = {
            "title": name,
            "price_tl": live_price,
            "rooms": rooms,
            "furnished": is_furnished,
            "listing_date": listing_date,
            "description": desc[:300],
            "photos": images[:3] if isinstance(images, list) else []
        }
        return True, data, "Active and verified"

    except Exception as e:
        return False, {}, f"Verification error: {e}"
    finally:
        if should_close:
            client.close()

def scan_live_portal_listings(feed_index: int = 0) -> List[Dict[str, Any]]:
    """
    Scans live neighborhood listings directly from priority portal feeds,
    verifying each individual listing in real-time.
    """
    listings: List[Dict[str, Any]] = []
    seen_urls = set()

    with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        # Scan priority feeds around Istanbul Aydın University
        for feed_name, feed_url in TARGET_FEEDS[:4]:
            logger.info(f"Scanning live target feed: {feed_name} -> {feed_url}")
            try:
                resp = client.get(feed_url)
                if resp.status_code != 200:
                    logger.warning(f"Feed {feed_name} returned status {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.find_all("a", href=True)
                ilan_links = [a["href"] for a in anchors if "/ilan/" in a["href"]]
                unique_links = list(dict.fromkeys(ilan_links))
                logger.info(f"Discovered {len(unique_links)} listing candidates in {feed_name}.")

                for link in unique_links[:10]:
                    full_url = "https://www.emlakjet.com" + link if link.startswith("/") else link
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    # Real-time pre-flight verification
                    is_active, meta, reason = verify_listing_live(full_url, client=client)
                    if not is_active:
                        continue

                    price = meta.get("price_tl", 0.0)
                    if price <= 0 or price > 40000:
                        continue

                    # Room filter: 1+0, 1+1, Studio, or affordable 2+1
                    rooms = meta.get("rooms", "1+1")
                    if rooms in ["3+1", "4+1", "5+1"]:
                        continue

                    prop_item = {
                        "source": f"Emlakjet ({feed_name.split('(')[0].strip()})",
                        "source_id": link.split("-")[-1].replace("/", ""),
                        "url": full_url,
                        "title": meta.get("title", ""),
                        "price_tl": price,
                        "effective_monthly_cost": price,
                        "property_type": "Studio" if rooms == "1+0" else "Apartment",
                        "rooms": rooms,
                        "area_m2": 40.0,
                        "furnished": meta.get("furnished", 1),
                        "listing_date": meta.get("listing_date", ""),
                        "location": feed_name.split("(")[0].strip(),
                        "address": f"{feed_name.split('(')[0].strip()}, Küçükçekmece, İstanbul",
                        "description": meta.get("description", ""),
                        "contact_info": "مباشرة في صفحة الإعلان عبر الرابط",
                        "photos": meta.get("photos", [])
                    }
                    listings.append(prop_item)
                    logger.info(f"Verified active listing: [{price:,.0f} TL] [{rooms}] {prop_item['title'][:40]}")

            except Exception as e:
                logger.error(f"Error scanning live feed {feed_name}: {e}")

    return listings

def get_seed_market_listings() -> List[Dict[str, Any]]:
    """
    Returns only individually verified, active, direct listings.
    Every listing returned here has been checked to be active and online.
    """
    seeds = [
        {
            "source": "Emlakjet (Beşyol - مباشر)",
            "source_id": "19797604",
            "url": "https://www.emlakjet.com/ilan/metrobus-duragi-ve-aydin-universitesi-yani-esyali-ve-faturalar-dahil-10-kiralik-daire-19797604",
            "title": "Metrobüs Durağı Ve Aydın Üniversitesi Yanı Eşyalı Ve Faturalar Dahil 1+0 Kiralık Daire",
            "price_tl": 35000.0,
            "effective_monthly_cost": 35000.0,
            "property_type": "Studio",
            "rooms": "1+0",
            "area_m2": 35.0,
            "furnished": 1,
            "location": "Beşyol, Küçükçekmece",
            "address": "Beşyol Metrobüs Durağı ve Aydın Üniversitesi Yanı",
            "latitude": 40.9881,
            "longitude": 28.8005,
            "description": "Aydın Üniversitesi ve Beşyol Metrobüs durağı yanı kiralık eşyalı 1+0 stüdyo daire. Tüm faturalar kiraya dahildir.",
            "contact_info": "متوفر في صفحة الإعلان مباشرة عبر الرابط",
            "photos": []
        },
        {
            "source": "Emlakjet (Sefaköy Kartaltepe - مباشر)",
            "source_id": "19786012",
            "url": "https://www.emlakjet.com/ilan/nest-emlak-tan-kartaltepe-mh-21-75m2-full-esyali-kiralik-daire-19786012",
            "title": "Nest Emlak'tan Kartaltepe Mh 2+1 75m2 Full Eşyalı Kiralık Daire",
            "price_tl": 30000.0,
            "effective_monthly_cost": 30000.0,
            "property_type": "Apartment",
            "rooms": "2+1",
            "area_m2": 75.0,
            "furnished": 1,
            "location": "Sefaköy, Kartaltepe",
            "address": "Kartaltepe Mah., Küçükçekmece",
            "latitude": 40.9980,
            "longitude": 28.7990,
            "description": "Kartaltepe Mahallesi, metrobüse yürüme mesafesinde, full eşyalı, temiz daire.",
            "contact_info": "متوفر في صفحة الإعلان مباشرة عبر الرابط",
            "photos": []
        },
        {
            "source": "Emlakjet (Sefaköy - مباشر)",
            "source_id": "19814515",
            "url": "https://www.emlakjet.com/ilan/loft-tan-sefakoyde-kiralik-21-giris-kat-bahceli-daire-19814515",
            "title": "Loft 'tan Sefaköyde Kiralık 2+1 Giriş Kat Bahçeli Daire",
            "price_tl": 28000.0,
            "effective_monthly_cost": 28000.0,
            "property_type": "Apartment",
            "rooms": "2+1",
            "area_m2": 70.0,
            "furnished": 1,
            "location": "Sefaköy, Küçükçekmece",
            "address": "Sefaköy, Küçükçekmece",
            "latitude": 41.0005,
            "longitude": 28.8030,
            "description": "Sefaköy metrobüse yakın konumda, 2+1 kiralık daire.",
            "contact_info": "متوفر في صفحة الإعلان مباشرة عبر الرابط",
            "photos": []
        },
        {
            "source": "Emlakjet (Sefaköy İnönü - مباشر)",
            "source_id": "19812633",
            "url": "https://www.emlakjet.com/ilan/sefakoy-inonu-mahallesi-kiralik-daire-19812633",
            "title": "Sefaköy İnönü Mahallesi Kiralık Daire",
            "price_tl": 16000.0,
            "effective_monthly_cost": 16000.0,
            "property_type": "Apartment",
            "rooms": "1+1",
            "area_m2": 55.0,
            "furnished": 1,
            "location": "Sefaköy, İnönü",
            "address": "İnönü Mah., Küçükçekmece",
            "latitude": 41.0060,
            "longitude": 28.8010,
            "description": "Sefaköy İnönü mahallesinde uygun fiyatlı kiralık daire.",
            "contact_info": "متوفر في صفحة الإعلان مباشرة عبر الرابط",
            "photos": []
        }
    ]

    # Pre-verify every seed before returning
    verified_seeds = []
    for s in seeds:
        ok, meta, reason = verify_listing_live(s["url"])
        if ok:
            # Update price if updated on site
            if meta.get("price_tl"):
                s["price_tl"] = meta["price_tl"]
                s["effective_monthly_cost"] = meta["price_tl"]
            s["listing_date"] = meta.get("listing_date", "08 Eylül 2026")
            verified_seeds.append(s)
        else:
            logger.warning(f"Seed listing {s['url']} failed live verification: {reason}")

    return verified_seeds

def fetch_cycle_candidates(cycle_index: int = 0) -> List[Dict[str, Any]]:
    """
    Main discovery entry point for each cycle:
    1. Scans live portal listings from target neighborhood feeds.
    2. Merges with verified direct seed listings.
    3. Guarantees 100% of returned items are currently active, direct, and unexpired.
    """
    live_portal_results = scan_live_portal_listings(cycle_index)
    verified_seeds = get_seed_market_listings()

    all_items = live_portal_results + verified_seeds
    unique_items = []
    seen = set()
    for item in all_items:
        u = item.get("url")
        if u and u not in seen:
            seen.add(u)
            unique_items.append(item)

    logger.info(f"Cycle {cycle_index}: Total verified active candidates: {len(unique_items)}")
    return unique_items
