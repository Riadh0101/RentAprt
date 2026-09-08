---
name: rental-scheduler
description: "Run continuous 20-minute rental monitoring cycles with fault-tolerant recovery and health checks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [scheduler, cron, 20min, lifecycle, resilience]
---

# RENTAL MONITORING SCHEDULER SKILL

## PURPOSE

Maintain continuous, robust execution of the Hermes rental monitoring workflow every **20 minutes** on a 24/7 basis.

---

## EXECUTION CADENCE

* **Cycle Frequency:** Every 20 minutes (`*/20 * * * *`).
* **Initial Bootstrap:** Upon service startup, immediately execute cycle #1 without waiting 20 minutes.

---

## 20-MINUTE CYCLE SEQUENCE

```
1. Initialize cycle logger & timestamp
2. Rotate Turkish query target for this tick
3. Fetch latest listings across search providers
4. Cheap Filter: Drop obvious mismatches (>36k, unfurnished, 3+ rooms)
5. Deep Parse: Normalize pricing and compute transit distances
6. Calculate Score (0–100)
7. SQLite Query: Check existing listings, detect price drops
8. Insert/Update Database
9. Dispatch Telegram/Email alerts for items with Score >= 75
10. Commit transaction & log cycle metrics (found, filtered, alerted)
```

---

## FAULT TOLERANCE & RECOVERY

* **Web Portal Timeout / Block:** Record source status as `BLOCKED / MANUAL CHECK REQUIRED` and proceed immediately with the other providers. Do NOT throw unhandled exceptions or stop the worker.
* **Network Disconnection:** Sleep 60 seconds, retry with exponential backoff up to 3 times before deferring to the next 20-minute cycle.
* **Notification Error:** If Telegram API fails (e.g. rate limit), buffer alerts in SQLite `pending_notifications` table to retry in the next cycle.
* **Process Crash:** Windows Task Scheduler / systemd service automatically restarts the process with exit code inspection.

---

## HOURLY HEALTH CHECK

Every 60 minutes (every 3 cycles), verify:
* Database connection responsive.
* Last cycle finished successfully in `< 120s`.
* Outbound internet access intact.
* If 3 consecutive cycles fail completely, dispatch an alert:
  `🚨 HERMES RENTAL MONITOR FAILURE: No successful search in last 60 minutes.`
