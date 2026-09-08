---
name: rental-notification
description: Multi-tier alert dispatcher for Telegram and SMTP Email.
version: 1.0.0
---

# NOTIFICATION SKILL

## CHANNELS
- **Primary:** Telegram Bot (Formatted markdown message with direct listing links)
- **Secondary:** SMTP Email

## NOTIFICATION TIERS
- **Tier 1 (Immediate Dual Alert - Telegram + Email):**
  - Score ≥ 85
  - Furnished property ≤ 25,000 TL near IAU
  - High-opportunity price reduction (>10% drop on top property)
- **Tier 2 (Telegram Only):**
  - Score 75–84
- **Tier 3 (Daily Digest):**
  - Score 65–74
- **Tier 4 (Silent):**
  - Score < 65

## TELEGRAM TEMPLATE
```text
🏠 NEW RENTAL MATCH
⭐ Score: 92/100
📍 Location: Beşyol
🏢 Type: 1+0 Studio
🛋️ Furnished: YES
📐 Size: 35 m²
💰 Rent: 22,000 TL/month
🚇 Metrobus: 4 min walk (Beşyol)
🎓 IAU: 7 min walk
💵 Deposit: 1 month
📅 Listed: 08/09/2026
🔗 ORIGINAL LISTING:
https://...
```
