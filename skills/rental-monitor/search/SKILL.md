---
name: rental-search
description: Multi-source search engine with query rotation for Istanbul rental listings and dorms.
version: 1.0.0
---

# RENTAL SEARCH SKILL

## PURPOSE
Discover fresh rental listings, student residences, and monthly stay opportunities in Istanbul near Istanbul Aydın University and Metrobus corridors.

## TARGET SOURCES
- **Turkish Portals:** Hepsiemlak, Zingat, Emlakjet, Sahibinden.
- **Student Residences / Dormitories:** Özel Erkek Öğrenci Yurdu, Istanbul Aydın University residences, Beşyol dorms.
- **Short/Mid-term Stays:** Airbnb (Monthly stay filters), Booking.com.
- **Social / Direct Listings:** Facebook Groups / Marketplace, Telegram channels.

## QUERY ROTATION MATRIX
- Cycle 1: `"Beşyol kiralık 1+0 eşyalı"`
- Cycle 2: `"Beşyol kiralık 1+1 eşyalı"`
- Cycle 3: `"İstanbul Aydın Üniversitesi yakınında kiralık daire"`
- Cycle 4: `"Metrobüs yakınında 1+0 kiralık eşyalı"`
- Cycle 5: `"Sefaköy Cennet kiralık 1+1 eşyalı"`
- Cycle 6: `"İstanbul Aydın Üniversitesi erkek öğrenci yurdu Beşyol"`
- Cycle 7: `"Küçükçekmece öğrenciye uygun kiralık daire"`
