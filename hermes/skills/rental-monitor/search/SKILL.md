---
name: rental-search
description: "Discover new rental listings and student dormitories in Istanbul near Istanbul Aydin University."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [search, rental, istanbul, turkish-keywords]
---

# RENTAL SEARCH SKILL

## PURPOSE

Discover fresh rental opportunities in Istanbul for the student accommodation task at Istanbul Aydın University.

## TARGET SOURCES

### 1. Major Turkish Real Estate Portals
* Emlakjet (`emlakjet.com`)
* Zingat (`zingat.com`)
* Hepsiemlak (`hepsiemlak.com`)
* Sahibinden (`sahibinden.com`)
* Endeksa (`endeksa.com`)
* Hürriyet Emlak

### 2. Student Dormitories & Residences
* Özel Öğrenci Yurdu (Private Dormitories)
* Erkek Öğrenci Yurdu (Male Student Dormitories)
* Öğrenci Residence listings around Beşyol, Florya, Sefaköy, and Küçükçekmece.

### 3. Medium/Monthly Stays
* Airbnb (monthly filter applied)
* Booking.com (monthly accommodation filter)

### 4. Public Social / Community Sources
* Facebook Marketplace (publicly accessible rental listings)
* Telegram channels / public student groups
* Reddit / X search results

> **Note:** Respect robots.txt, rate limits, and access controls. Do NOT attempt to break CAPTCHAs or bypass anti-bot challenges. If a site is protected, mark as `BLOCKED / MANUAL CHECK REQUIRED` and rely on open engines/search queries.

---

## SEARCH LOCATIONS (PRIORITY ORDER)

1. **Beşyol** (Campus location)
2. **Florya**
3. **Sefaköy**
4. **Cennet**
5. **Küçükçekmece**
6. **Gültepe**
7. Metrobus line stops (Avcılar, Yenibosna, Şirinevler, Bahçelievler)

---

## TURKISH SEARCH QUERY ROTATION

Rotate keywords across 20-minute cycles to maximize fresh discovery without triggering rate limits:

* **Cycle 1:** `"Beşyol kiralık 1+0 eşyalı"`
* **Cycle 2:** `"Beşyol kiralık 1+1 eşyalı"`
* **Cycle 3:** `"İstanbul Aydın Üniversitesi yakınında kiralık daire"`
* **Cycle 4:** `"Florya kiralık daire eşyalı 1+1"`
* **Cycle 5:** `"Sefaköy metrobüs yakın kiralık eşyalı"`
* **Cycle 6:** `"Cennet mahallesi kiralık 1+0 1+1"`
* **Cycle 7:** `"Beşyol erkek öğrenci yurdu"`
* **Cycle 8:** `"Küçükçekmece öğrenciye uygun kiralık"`

---

## REAL-TIME PRE-FLIGHT VERIFICATION (فلترة الإعلانات المحذوفة والتحقق المباشر)

To ensure that NO expired, removed, or invalid listings are ever sent:
1. **Direct Individual Listings Only:** Only accept individual property pages (e.g., `https://www.emlakjet.com/ilan/...`). Reject category, search, or catalog URLs.
2. **HTTP 200 & Redirection Check:** Fetch the URL with follow-redirects. If status is not 200 or redirected away from `/ilan/`, discard immediately.
3. **Deactivation & Inactive Detection:** Discard any listing containing `"yayında değildir"`, `"ilan yayından kaldırılmıştır"`, `"ilan süresi dolmuştur"`, or `"aradığınız sayfa bulunamadı"`.
4. **Availability Check:** In JSON-LD structured data, ensure `offers.availability` is not `OutOfStock`.
5. **Restriction Check:** Discard listings with landlord restrictions against students (`sadece aile`, `öğrenci olmaz`).
6. **Live Data Refresh:** Extract the live price and room configuration directly from the active page before scoring.

---

## OUTPUT SCHEMA

Return structured candidate listings:
* `source`: Portal or site name
* `url`: Direct canonical URL
* `title`: Listing title
* `price_raw`: Advertised price and currency
* `property_type`: `1+0`, `1+1`, or `dormitory`
* `furnished`: `True`, `False`, or `Unknown`
* `location_district`: Neighborhood / district
* `listing_date`: Date or freshness indicator
* `advertiser_contact`: Phone number or agent name if publicly visible
