# Hermes Autonomous Rental Monitoring System Specification

## Overview
An autonomous, continuous monitoring system designed to locate and track the best accommodation options for a student studying Mechanical Engineering at Istanbul Aydın University (IAU - Florya / Beşyol campus).

## Core Requirements
- **Preferred Types:** 1+0 (Studio), 1+1, Student Residences, Private / Male Student Dormitories.
- **Furnishing:** Fully furnished preferred (`Eşyalı`).
- **Budget Target:** $\le$ 36,000 TL/month.
- **Priority Locations:**
  1. Beşyol (immediate walking distance to IAU)
  2. Florya
  3. Sefaköy
  4. Cennet
  5. Küçükçekmece
  6. Gültepe
  7. Any Metrobus-accessible location in Istanbul.

## Cycle Pipeline
The system operates autonomously on a 20-minute cycle:
1. **Search:** Query rotation across Turkish portals, dormitories, Airbnb/Booking, and social platforms.
2. **Extract & Normalize:** Standardize listing details and compute effective total monthly costs.
3. **Distance Calculation:** Estimate transit and walking time to IAU and nearest Metrobus station.
4. **Scoring Engine:** 0–100 weighted evaluation (Location: 40, Price: 25, Furnished: 15, Quality: 10, Reliability: 10).
5. **Deduplication:** Fuzzy canonical property matching across multiple listing sites.
6. **Change Detection:** Track price drops, reactivation, or listing removals in SQLite database.
7. **Notification:** Dispatch instant alerts via Telegram Bot (primary) and SMTP Email (secondary) for high-score listings ($\ge 85$) or price drops.
8. **Daily Digest:** Compile 24-hour market recap and top 10 listings.
