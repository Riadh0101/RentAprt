# System Architecture & Pipeline

```text
               Scheduler (src/scheduler.py)
     every CYCLE_INTERVAL_MINUTES  +  daily digest
                         │
                         ↓
  Emlakjet neighbourhood feeds (6)  +  watchlist.txt
  JSON-LD summaries: price, rooms, m², mahalle
                         │
                         ↓
  Cheap filter on feed data (price limit, room layout)
                         │
                         ↓
  Known, same price, verified < REVERIFY_HOURS ? ──yes──> mark seen, skip
                         │ no
                         ↓
  Fetch listing page (src/scraper.py) ── 404/410/expired/OutOfStock ──> REMOVED
                         │ active
                         ↓
  Normalise: furnishing, aidat, deposit, elevator, heating, mahalle,
  walking minutes to IAU and nearest Metrobüs (src/geo.py)
                         │
                         ↓
  Eligibility filter: budget, rooms, family-only / no-students wording
                         │
                         ↓
  Score 0–100 (src/scoring.py)
                         │
                         ↓
  SQLite upsert keyed by (source, listing id) (src/database.py)
  NEW · PRICE_DROP · PRICE_INCREASE · REACTIVATED · price history
                         │
                         ↓
  Stale-listing sweep: re-verify active listings not seen this cycle
                         │
                         ↓
  Alerts (src/pipeline.py + src/notifier.py), de-duplicated in alert_log
        ┌────────────────┴────────────────┐
        ↓                                 ↓
   Telegram (instant)          Email (high score / price drop, batched)
```

## Scoring Breakdown (0–100 Points)

Implemented in `src/scoring.py`. Cost = monthly rent + aidat.

1. **Location & Transit (40 pts)** — the better of:
   - Walk to IAU: ≤5 min 40, ≤10 min 37, ≤20 min 32, ≤30 min 25
   - Walk to nearest Metrobüs station: ≤5 min 35, ≤10 min 32, ≤15 min 28, ≤20 min 20, else 10
   - Neighbourhood unknown: 15
2. **Price vs Budget (25 pts):** ≤20,000 TL 25 · ≤25,000 TL 20 · ≤30,000 TL 15 ·
   ≤`TARGET_MAX_BUDGET_TL` 10 · above budget 0 (classified `OVER_BUDGET_EXCEPTIONAL` if the total
   is still ≥ `SCORE_DAILY_DIGEST`). Listings above `EXCEPTIONAL_BUDGET_LIMIT_TL` are discarded.
3. **Furnishing (15 pts):** furnished 15 · partially furnished 8 · unfurnished/unknown 0
4. **Quality & Amenities (10 pts):** elevator 2 · kombi/doğalgaz/central heating 2 · ≥30 m² 2 ·
   building ≤10 years 2 · bills included 2 · balcony 1 · 1+0/1+1 layout 1
5. **Reliability & Freshness (10 pts):** ≥3 photos 3 (any photo 1) · description ≥80 chars 2 ·
   updated ≤7 days 3 (≤30 days 1) · aidat/deposit disclosed 2

Classification: ≥90 EXCEPTIONAL · ≥85 EXCELLENT · ≥75 VERY_GOOD · ≥65 GOOD · ≥50 POTENTIAL · else REJECT.

## Eligibility filters (never stored or alerted)

- Cost above `EXCEPTIONAL_BUDGET_LIMIT_TL`, or room layout not in `ALLOWED_ROOMS`
- "No students", "no single tenants" or female-only wording
- Family-only wording, unless the listing also says it suits students
