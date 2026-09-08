---
name: rental-deduplication
description: "Detect duplicate properties across portals, create canonical records, and track price changes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deduplication, canonical, price-drop, fingerprint]
---

# PROPERTY DEDUPLICATION & TRACKING SKILL

## PURPOSE

Prevent duplicate alerts for the same physical property listed across multiple websites (e.g. Sahibinden + Hepsiemlak + Emlakjet), and actively detect price reductions or reactivation.

---

## FINGERPRINT MATCHING ATTRIBUTES

Compute a composite property signature using:
1. **Normalized Location:** District + Neighborhood (`İlçe` + `Mahalle`).
2. **Floor & Area:** Floor number, building total floors, and Net/Gross m².
3. **Room Layout:** `1+0` vs `1+1`.
4. **Phone / Advertiser:** Normalized contact phone number or agency name.
5. **Exact Building Attributes:** Elevator + Heating type + Balcony status.
6. **Title & Description Similarity:** Token cosine similarity / Levenshtein distance on core keywords.

---

## CONFIDENCE THRESHOLDS

* **≥ 90% Confidence:** Confirmed duplicate → Merge into canonical record, append secondary source URL to `source_urls`.
* **75% – 89% Confidence:** Likely duplicate → Check price and contact; flag as linked variant.
* **< 75% Confidence:** Treat as separate unique property.

---

## PRICE CHANGE DETECTION

When a duplicate or re-scraped listing matches an existing database entry:
* Compare `new_price` with `stored_price`:
  * If `new_price < stored_price`:
    * Calculate percentage decrease: $\frac{P_{\text{old}} - P_{\text{new}}}{P_{\text{old}}} \times 100$
    * Record in `price_history` table.
    * Re-run Scoring Skill (lower price increases score).
    * If reduction is significant (≥ 5% or drops below 30k/25k threshold), trigger a **PRICE REDUCTION ALERT**.
  * If `new_price == stored_price`: Update `last_seen_at` timestamp quietly (NO alert).
