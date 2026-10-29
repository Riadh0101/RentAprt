# Hermes Autonomous Rental Monitoring System

Continuously watches live Emlakjet listings around **Istanbul Aydın University** (Florya / Beşyol
campus), scores each one for a student tenant, tracks price changes and removals, and alerts via
**Telegram** (and optionally email).

```text
FEEDS (6 neighbourhoods + watchlist) -> VERIFY listing page -> FILTER -> SCORE -> SQLite -> ALERT
```

- **Real data only.** Listings come from Emlakjet's own structured data (schema.org JSON-LD) on
  neighbourhood search pages and listing pages. Every stored listing was verified online.
- **Efficient & polite.** A listing page is fetched only when it is new, its price changed, or it
  hasn't been verified for `REVERIFY_HOURS`. Requests are spaced and retried on 429/5xx.
- **Change detection.** New listings, price drops/increases, removals (404/410/expired/OutOfStock)
  and reactivations are recorded with full price history.
- **No duplicate alerts.** Each alert is sent once per listing (price drops once per new price).
  Failed deliveries are retried on the next cycle.
- **True monthly cost.** Price scoring uses rent + aidat (building fee).
- **Student filters.** Rejects family-only, "no students", "no single tenants" and female-only
  listings (Turkish text is matched case-insensitively, including `İ`).

## Setup

```bash
uv venv .venv
uv pip install -p .venv -r requirements-dev.txt   # or: pip install -r requirements-dev.txt
cp .env.example .env                              # then fill in Telegram / SMTP
```

All settings are documented in [.env.example](.env.example). Without Telegram configured, alerts
are printed to the console instead.

## Usage

| Command | What it does |
|---|---|
| `python main.py check` | Validate configuration and Emlakjet connectivity |
| `python main.py run-once` | One cycle, then show the dashboard (`run_single_search.bat`) |
| `python main.py monitor [--interval N]` | Cycle every N minutes + daily digest (`start_monitor.bat`) |
| `python main.py dashboard [--min-score N]` | Statistics and top listings |
| `python main.py summary [--send]` | Daily digest; `--send` delivers it via Telegram/email |
| `python main.py test` | Run the test suite (`pytest`) |

Add listing URLs you want tracked regardless of the feeds to [watchlist.txt](watchlist.txt).

## Alert rules

| Event | Condition | Channels |
|---|---|---|
| New / reactivated listing | score ≥ `SCORE_INSTANT_ALERT` (75), or over-budget but otherwise strong | Telegram |
| … high score | score ≥ `SCORE_MULTI_CHANNEL_ALERT` (85) | Telegram + email |
| Price drop | score ≥ `SCORE_DAILY_DIGEST` (65) | Telegram + email |
| Daily digest | every day at `DAILY_DIGEST_HOUR` | Telegram + email |
| Health warning | all feeds failed 3 cycles in a row | Telegram |

Scoring details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project layout

```text
main.py              CLI entry point (run_cycle.py is a compatibility wrapper)
watchlist.txt        Extra listing URLs to track
src/config.py        Settings from .env (feeds, budget, thresholds, credentials)
src/scraper.py       Emlakjet feed + listing parsing, HTTP with retries
src/scoring.py       Normalisation, eligibility filters, 0–100 score
src/geo.py           Neighbourhood centroids, walking times to campus / Metrobüs
src/database.py      SQLite: listings, price history, alert log, cycle runs
src/notifier.py      Telegram / email delivery and message formatting
src/pipeline.py      The monitoring cycle and daily digest
src/scheduler.py     APScheduler loop (python -m src.scheduler)
src/dashboard.py     Terminal output
tests/               pytest suite (offline; real-page fixtures in tests/fixtures)
hermes/skills/       Hermes agent skill descriptions
```

## Limitations

- Emlakjet does not publish coordinates; walking times use approximate neighbourhood centroids
  (`src/geo.py`). Neighbourhoods not in that table are shown as "location unknown" and get a
  neutral location score — add them to `NEIGHBORHOOD_COORDS` to improve accuracy.
- Only Emlakjet is scraped. Sahibinden, Hepsiemlak and Airbnb block or require JavaScript and are
  not supported.
- If Emlakjet changes its page structure, `python main.py check` and the fixture tests in
  `tests/test_parsing.py` are the first things to run.
