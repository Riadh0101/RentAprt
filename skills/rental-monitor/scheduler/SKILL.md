---
name: rental-scheduler
description: 20-minute persistent cycle orchestrator, health check, and error recovery.
version: 1.0.0
---

# RENTAL SCHEDULER SKILL

## FREQUENCY
- Default cycle execution interval: **Every 20 minutes**.

## STARTUP CHECKLIST
1. Load SQLite database and previous tracking states.
2. Verify network, Telegram, and Email connectivity.
3. Perform an initial immediate search cycle.
4. Compare against historical records and dispatch alerts only for genuine updates.
5. Register background recurring timer.

## RESILIENCE & RETRIES
- Individual portal failures (e.g. rate limits or anti-bot blocks) must not crash the cycle.
- Exponential backoff retry on network transients.
- Hourly health check and daily digest dispatch.
