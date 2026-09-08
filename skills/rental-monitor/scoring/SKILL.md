---
name: rental-scoring
description: 100-point multi-factor accommodation scoring model.
version: 1.0.0
---

# PROPERTY SCORING SKILL

## SCORING BREAKDOWN (0 - 100)

### 1. Location & Transit (40 Points Max)
- 0–5 min walk to Istanbul Aydın University: 40 pts
- 6–10 min walk to IAU: 37 pts
- 11–20 min walk to IAU: 32 pts
- 21–30 min walk to IAU: 25 pts
- Direct Metrobus connection: 28–35 pts
- Difficult transit (>35 min / multiple transfers): <20 pts

### 2. Price vs Budget (25 Points Max)
- ≤ 20,000 TL: 25 pts
- 20,001–25,000 TL: 20 pts
- 25,001–30,000 TL: 15 pts
- 30,001–36,000 TL: 10 pts
- \> 36,000 TL: 0 pts (Flagged as OVER BUDGET)

### 3. Furnishing (15 Points Max)
- Fully Furnished (`Eşyalı`): 15 pts
- Partially Furnished: 8 pts
- Unfurnished: 0 pts

### 4. Quality & Amenities (10 Points Max)
- Elevator, natural gas heating (Kombi), building age ≤ 10 years, good condition, internet included.

### 5. Listing Reliability (10 Points Max)
- Verified broker/landlord, clear photos, complete description, recent listing date.

## CLASSIFICATION BRACKETS
- **90–100:** EXCEPTIONAL MATCH (Immediate Alert)
- **85–89:** EXCELLENT MATCH (Immediate Alert)
- **75–84:** VERY GOOD (Telegram Alert)
- **65–74:** GOOD (Stored for Daily Digest)
- **< 65:** REJECT / LOW PRIORITY
