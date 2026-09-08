---
name: rental-notification
description: "Dispatch instant high-priority Telegram alerts and email notifications for qualified rental matches."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [notification, telegram, email, alert, formatting]
---

# RENTAL NOTIFICATION SKILL

## PURPOSE

Format and deliver actionable, real-time alerts via **Telegram** (instant push) and **Email** (backup record) whenever a qualified property or price drop is discovered.

---

## NOTIFICATION RULES
 
* **Score ≥ 75 (`VERY GOOD` / `EXCELLENT` / `EXCEPTIONAL`):**
  * Immediate **Telegram Alert** with Title `AG Alert` and timestamp banner.
  * Direct 100% active, verified clickable link (`/ilan/...`).
* **Cycle Completion Report:**
  * Rich HTML summary report sent to `Riadh0101@Yahoo.fr` via authenticated Yahoo SMTP (`smtp.mail.yahoo.com:465`).
* **Price Drop Alert:**
  * Triggered immediately whenever an existing property drops by ≥ 5%.

---

## TELEGRAM MESSAGE FORMAT (HTML)

Title must strictly be **`AG Alert`** and timestamp banner must be placed directly above the alert card:

```html
⏱️ <b>تاريخ وتوقيت الإرسال:</b> <code>2026-09-08 | 12:30:00</code>
🏠 <b>AG Alert — شقة مطابقة جديدة</b>

⭐ <b>Score:</b> 88/100 (EXCELLENT)
📍 <b>Location:</b> Beşyol Mah., Küçükçekmece
🏢 <b>Type:</b> 1+1 (Furnished / Eşyalı)
📐 <b>Area:</b> 50 m² | Floor: 2 | Heating: Kombi

💰 <b>Monthly Rent:</b> 22,500 TL
💵 <b>Aidat:</b> 400 TL | <b>Deposit:</b> 22,500 TL

🎓 <b>University:</b> 7 min walk (Istanbul Aydın Univ)
🚇 <b>Metrobus:</b> 4 min walk (Beşyol Metrobüs)

📞 <b>Contact:</b> +90 5XX XXX XX XX (Owner/Agent)
📅 <b>Listed:</b> Today

🔗 <b>Direct Link:</b>
https://www.emlakjet.com/ilan/...
```

### Price Drop Variant
```html
🏷️ <b>AG Alert — PRICE REDUCTION!</b>

📉 <b>Old Price:</b> 28,000 TL
🔥 <b>New Price:</b> 23,000 TL (-17.8%)
⭐ <b>Updated Score:</b> 89/100

📍 <b>Location:</b> Florya / Beşyol
🏢 <b>Type:</b> 1+0 Studio (Furnished)
🎓 <b>University:</b> 9 min walk

🔗 <a href="https://example.com/listing/12345"><b>VIEW DISCOUNTED LISTING</b></a>
```

---

## SECURITY & ANTI-SPAM SAFEGUARDS

1. Never expose raw authentication credentials, bot tokens, or API secrets in message logs.
2. Maintain an in-memory & SQLite lock (`notifications_sent` table) so an alert for property `X` is never repeated within 48 hours unless a price drop occurs.
