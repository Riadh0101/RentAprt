# System Architecture & Pipeline

```text
                    HERMES AUTONOMOUS ORCHESTRATOR
                                 │
                        ┌────────┴────────┐
                        │   Scheduler     │
                        │    20 minutes   │
                        └────────┬────────┘
                                 │
                           Search Engine
                                 │
         ┌───────────────────────┼───────────────────────┐
         ↓                       ↓                       ↓
    Turkish Portals         Airbnb / Booking        Social & Dorms
  (Hepsiemlak, Zingat,     (Monthly effective       (Özel Erkek Yurdu,
   Emlakjet, Sahibinden)       stay pricing)           Student Res)
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ↓
                         Data Extraction
                                 ↓
                     Effective Price & Distance
                                 ↓
                          Cheap Filtering
                    (Price > 36k, Non 1+0/1+1)
                                 ↓
                           Scoring Engine
                        (0 - 100 Multi-Factor)
                                 ↓
                        Deduplication Engine
                    (Canonical Entity Resolution)
                                 ↓
                          SQLite Database
                (Properties, Price History, Runs)
                                 ↓
                      Change & Anomaly Detector
                (New, Price Reduction, Reactivation)
                                 ↓
                    ┌────────────┴────────────┐
                    ↓                         ↓
              Telegram Bot               SMTP Email
             (Instant Alert)           (Instant Alert)
```

## Scoring Breakdown (0–100 Points)
1. **Location & Transit (40 pts):**
   - 0–5 min walk to IAU: 40 pts
   - 6–10 min walk to IAU: 37 pts
   - 11–20 min walk to IAU: 32 pts
   - 21–30 min walk to IAU: 25 pts
   - Direct Metrobus connection: 28–35 pts
   - Difficult transit: <20 pts
2. **Price vs Budget (25 pts):**
   - $\le$ 20,000 TL: 25 pts
   - 20,001–25,000 TL: 20 pts
   - 25,001–30,000 TL: 15 pts
   - 30,001–36,000 TL: 10 pts
   - \> 36,000 TL: 0 pts (Marked as OVER BUDGET)
3. **Furnishing Status (15 pts):**
   - Fully Furnished: 15 pts
   - Partially Furnished: 8 pts
   - Unfurnished: 0 pts
4. **Property Quality & Amenities (10 pts):**
   - Condition, building age, elevator, heating (Kombi/Doğalgaz), balcony, internet.
5. **Listing Reliability & Freshness (10 pts):**
   - Clear photos, verified agency/landlord, complete description, fresh posting date.
