---
name: rental-scoring
description: "Calculate an objective 0-100 property score matching student requirements at Istanbul Aydin University."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [scoring, evaluation, rank, apartment-score]
---

# PROPERTY SCORING SKILL

## PURPOSE

Evaluate each candidate listing against the adopted student constraints and calculate an objective score from **0 to 100**.

---

## SCORING MATRIX (100 TOTAL POINTS)

### 1. LOCATION & TRANSIT (40 Points Max)
Proximity to Istanbul Aydın University (Florya / Beşyol) & Metrobus line:
* **0–10 min walk to University:** 40 pts
* **11–20 min walk to University:** 37 pts
* **Direct Metrobus connection (≤ 5 min walk to station):** 35 pts
* **Direct Metrobus connection (6–20 min walk to station):** 28–32 pts
* **Metrobus transit time within 30 min to Beşyol station:** Supported
* **Complex / indirect transit (> 20 min walk to Metrobus or > 30 min ride):** < 25 pts

### 2. PRICE & BUDGET (25 Points Max)
Target threshold: ≤ 36,000 TL/month (effective all-inclusive):
* **≤ 20,000 TL:** 25 pts ⭐⭐⭐⭐⭐
* **20,001 – 25,000 TL:** 20 pts ⭐⭐⭐⭐
* **25,001 – 30,000 TL:** 15 pts ⭐⭐⭐
* **30,001 – 36,000 TL:** 10 pts ⭐⭐
* **36,001 – 40,000 TL:** 5 pts (Classified as `OVER BUDGET - EXCEPTIONAL` if prime location / luxury)
* **> 40,000 TL:** 0 pts (Rejected)

### 3. FURNISHING (15 Points Max)
* **Fully Furnished (`Tam Eşyalı`):** 15 pts
* **Partially Furnished (`Kısmi Eşyalı`):** 8 pts
* **Unfurnished (`Boş`):** 0 pts

### 4. QUALITY & COMFORT (10 Points Max)
* Modern building / good condition: +3 pts
* Heating present (Kombi Doğalgaz / Merkezi): +3 pts
* Elevator present (required if floor > 3): +2 pts
* Good net area / room comfort (≥ 30 m² for studio/room, ≥ 45 m² for 1+1): +2 pts

### 5. RELIABILITY, CONTACT & ACTIVE STATUS (10 Points Max)
* Direct phone / verified contact: +4 pts
* Authentic photos: +3 pts
* Fresh active listing (verified active, not cancelled/removed): +3 pts

---

## CLASSIFICATION TIERS

* **90 – 100:** `EXCEPTIONAL` → Instant Alert
* **85 – 89:** `EXCELLENT` → Instant Alert
* **75 – 84:** `VERY GOOD` → Instant Alert
* **65 – 74:** `GOOD` → Database record / digest
* **50 – 64:** `POTENTIAL` → Monitor for price drops
* **< 50:** `REJECT` → Discard
