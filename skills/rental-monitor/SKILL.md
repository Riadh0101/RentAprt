---
name: rental-monitor
description: Master orchestrator for autonomous student accommodation and rental property monitoring near Istanbul Aydın University.
version: 1.0.0
---

# HERMES RENTAL MONITOR — MASTER ORCHESTRATOR

## PURPOSE
You are the MASTER ORCHESTRATOR for an autonomous Istanbul rental-property monitoring system.
Your mission is to continuously find and monitor the best accommodation for a student studying Mechanical Engineering at Istanbul Aydın University (IAU - Florya / Beşyol).

## CORE REQUIREMENTS
- **Room Types:** 1+0 (Studio) or 1+1 (also male dormitories / student residences).
- **Furnishing:** Fully furnished preferred (`Eşyalı`).
- **Target Budget:** ≤ 36,000 TL/month.
- **Priority Locations:**
  1. Beşyol (Walking distance to IAU)
  2. Florya
  3. Sefaköy
  4. Cennet
  5. Küçükçekmece
  6. Gültepe
  7. Other Metrobus-accessible stations.

## SUB-SKILLS
- **Search:** `skills/rental-monitor/search/SKILL.md`
- **Extraction:** `skills/rental-monitor/extraction/SKILL.md`
- **Scoring:** `skills/rental-monitor/scoring/SKILL.md`
- **Deduplication:** `skills/rental-monitor/deduplication/SKILL.md`
- **Notification:** `skills/rental-monitor/notification/SKILL.md`
- **Scheduler:** `skills/rental-monitor/scheduler/SKILL.md`

## EXECUTION WORKFLOW
Every 20-minute cycle:
1. Trigger Search Skill across rotating Turkish & international portals.
2. Extract and normalize listing data into canonical structures.
3. Compute transit & walking distances to IAU and Metrobus.
4. Apply 100-point scoring algorithm.
5. Deduplicate against existing properties in SQLite database.
6. Detect state changes (New, Price Reduced, Reactivated).
7. Dispatch instant alerts via Telegram/Email if Score ≥ 85 or significant price drop.
8. Update database and log cycle health.
