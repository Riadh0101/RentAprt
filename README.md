# Hermes Autonomous Rental Monitoring System

An autonomous monitoring agent designed to discover, track, evaluate, deduplicate, and notify about accommodation opportunities for students studying at **Istanbul Aydın University (IAU)** in Istanbul, Turkey.

---

## Architecture & Workflow

```text
SEARCH -> EXTRACT -> NORMALIZE -> SCORE -> DEDUPLICATE -> DATABASE -> NOTIFICATION (Telegram/Email)
```

1. **Continuous 20-minute cycle:** Rotates targeted Turkish search queries across Turkish real-estate portals, student residences, male student dorms, and Airbnb/Booking monthly stays.
2. **Effective Cost Normalization:** Converts daily/weekly/monthly rates into true effective monthly costs inclusive of mandatory cleaning fees, utilities, and monthly discount structures.
3. **Transit Distance Estimator:** Computes walking and commute minutes to Istanbul Aydın University (Beşyol/Florya campus) and nearest Metrobus stations.
4. **100-Point Scoring Engine:** Multi-factor scoring prioritizing budget ($\le$ 36,000 TL), proximity, furnishing, and reliability.
5. **Entity Resolution & Deduplication:** Multi-signal fuzzy matching prevents duplicate notifications and maintains canonical records.
6. **Instant Alerts:** Dual Telegram and Email alerts for $\ge 85$ score opportunities and significant price drops.

---

## Directory Structure

```text
RentAprt/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── main.py
│
├── docs/
│   ├── SPECIFICATION.md
│   ├── USER_PROMPT_AR.md
│   └── ARCHITECTURE.md
│
├── skills/
│   └── rental-monitor/
│       ├── SKILL.md
│       ├── search/SKILL.md
│       ├── extraction/SKILL.md
│       ├── scoring/SKILL.md
│       ├── deduplication/SKILL.md
│       ├── notification/SKILL.md
│       └── scheduler/SKILL.md
│
├── src/
│   ├── config.py
│   ├── db/
│   │   ├── models.py
│   │   └── database.py
│   ├── search/
│   │   ├── engine.py
│   │   └── sources/
│   ├── extraction/
│   │   ├── normalizer.py
│   │   └── distance.py
│   ├── scoring/
│   │   └── scorer.py
│   ├── deduplication/
│   │   └── matcher.py
│   ├── notification/
│   │   ├── telegram.py
│   │   ├── email_service.py
│   │   └── dispatcher.py
│   ├── scheduler/
│   │   └── runner.py
│   └── dashboard/
│       └── app.py
│
└── data/
    └── rentals.db
```

---

## Installation & Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   # or with uv:
   uv pip install -r requirements.txt
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to configure your Telegram Bot Token and SMTP Email credentials.

---

## Usage Commands

- **Run a single search & update cycle:**
  ```bash
  python main.py run-once
  ```

- **Start continuous 20-minute background monitoring:**
  ```bash
  python main.py monitor
  ```

- **Display live terminal dashboard:**
  ```bash
  python main.py dashboard
  ```

- **Generate daily market summary report:**
  ```bash
  python main.py summary
  ```

- **Run end-to-end self test:**
  ```bash
  python main.py test
  ```
