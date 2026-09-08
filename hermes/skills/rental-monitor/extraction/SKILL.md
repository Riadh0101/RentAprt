---
name: rental-extraction
description: "Extract and normalize rental property details, monthly effective pricing, and transit proximity."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [extraction, normalization, pricing, coordinates, transit]
---

# PROPERTY EXTRACTION & NORMALIZATION SKILL

## PURPOSE

Convert unstructured or raw listing pages into uniform, verified property records with normalized monthly pricing and accurate transit times.

## EXTRACTION FIELDS

Extract and parse:
* **Identification:** Source name, Listing ID, Canonical URL.
* **Basic Specs:** Title, Property Type (1+0, 1+1, Dormitory), Area (m² net/gross), Floor level, Total floors, Building age, Elevator (Asansör).
* **Furnishing & Comfort:** Furnished (`Eşyalı`), Heating (`Kombi Doğalgaz`, `Merkezi`, etc.), Air conditioning, Balcony.
* **Financial Breakdown:**
  * Advertised rent (`Fiyat`)
  * Currency (converted to TL)
  * Building maintenance fee (`Aidat`)
  * Security deposit (`Depozito`)
  * Real estate commission / Agency fee (`Emlakçı Komisyonu`)
* **Contact & Freshness:** Contact phone number, advertiser name.
* **Listing Publication / Update Date (`تاريخ نشر وتحديث الإعلان`):** **MANDATORY FIELD.** Must be extracted from structured data (`RealEstateListing.dateModified` or `additionalProperty: İlan Güncelleme Tarihi`) or page text, and preserved as `listing_date` to be included in all Telegram alerts and Email reports.

---

## PRICE NORMALIZATION

Convert all costs into **REAL EFFECTIVE MONTHLY COST (TL / Month)**:

$$\text{Effective Monthly Cost} = \text{Monthly Rent} + \text{Aidat} + \frac{\text{Amortized One-Time Fees (if applicable)}}{12}$$

For Airbnb / Booking.com:
$$\text{Total Monthly Cost} = \text{Base Rent} + \text{Cleaning Fee} + \text{Platform Service Fee} + \text{Taxes} - \text{Monthly Discount}$$

Always display both **Advertised Price** and **Real Effective Monthly Cost**.

---

## TRANSIT & PROXIMITY CALCULATIONS

Reference Points:
* **Istanbul Aydın University (Main Florya Campus):** `40.9882° N, 28.7997° E` (Beşyol / Küçükçekmece)
* **Nearest Metrobus Station:** Beşyol Metrobüs İstasyonu (`40.9875° N, 28.8020° E`)

Determine:
1. Walking distance to Istanbul Aydın University (minutes).
2. Walking distance to nearest Metrobus station (minutes).
3. Estimated total commute time by Metrobus if outside walking range.

> **Integrity Rule:** If exact coordinates or address are ambiguous, mark as `UNKNOWN`. Never invent estimated distances.
