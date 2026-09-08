---
name: rental-extraction
description: Property normalization, effective monthly cost calculation, and transit estimation.
version: 1.0.0
---

# PROPERTY EXTRACTION SKILL

## PURPOSE
Standardize incoming raw rental listings into structured property schemas and compute real all-inclusive monthly costs.

## DATA NORMALIZATION
- Standardize price into Turkish Lira (`TL / month`).
- Calculate real effective cost for Airbnb / Booking:
  `Effective Monthly Cost = (Base Rate + Cleaning + Platform Fees + Mandatory Taxes) - Monthly Discounts`
- Validate room layouts: standardizing `1+0`, `1+1`, `Studio`, `Dorm Room`.

## LOCATION & TRANSIT RESOLUTION
- Compute walking time & distance to **Istanbul Aydın University (Beşyol/Florya Campus)**.
- Compute walking time & distance to the nearest **Metrobus Station** (Beşyol, Florya, Sefaköy, Cennet).
- Set verification flags: `VERIFIED`, `LIKELY`, `NEEDS_VERIFICATION`, or `SUSPICIOUS`.
