---
name: rental-deduplication
description: Cross-platform entity resolution and duplicate detection.
version: 1.0.0
---

# PROPERTY DEDUPLICATION SKILL

## PURPOSE
Prevent duplicate properties across multiple Turkish portals and aggregate listings into a single canonical record.

## COMPARISON SIGNALS
1. **Source IDs & Exact URLs**
2. **Contact Phone Numbers**
3. **Normalized Address & Geo-coordinates**
4. **Price & Room Configuration** (e.g. 1+0 vs 1+1, area m²)
5. **Building Attributes** (Floor, Age, Heating type)
6. **Title & Description Semantic Similarity**

## CONFIDENCE THRESHOLDS
- **≥ 95% Match:** Same property -> merge into canonical record, append secondary URL to `source_urls`.
- **80–94% Match:** Likely duplicate -> merge with lower-confidence flag.
- **60–79% Match:** Possible duplicate -> retain for manual verification.
- **< 60% Match:** Distinct property.
