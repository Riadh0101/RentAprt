import logging
import requests
from datetime import datetime
from typing import Optional
from ..config import config
from ..db.models import PropertyRecord

logger = logging.getLogger(__name__)

class TelegramNotifier:
    @classmethod
    def format_property_alert(cls, prop: PropertyRecord, alert_type: str = "NEW_LISTING") -> str:
        current_time_str = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
        score_emoji = "⭐" if prop.score >= 85 else "✨"
        furnished_str = "YES (Tam Eşyalı)" if prop.furnished else "NO (Eşyasız)"
        
        header = "🏠 Her Alert — NEW RENTAL MATCH"
        if alert_type == "PRICE_REDUCTION":
            header = "🏷️ Her Alert — PRICE REDUCTION"
        elif alert_type == "EXCEPTIONAL":
            header = "🔥 Her Alert — EXCEPTIONAL OPPORTUNITY"

        metrobus_info = f"{prop.metrobus_distance_min} min walk ({prop.metrobus_station})" if prop.metrobus_distance_min else "Near station"
        uni_info = f"{prop.university_distance_min} min walk" if prop.university_distance_min else "Close to campus"

        msg = f"""🕒 <b>Sent:</b> <code>{current_time_str}</code>
<b>{header}</b>

{score_emoji} <b>Score:</b> {prop.score}/100
📍 <b>Location:</b> {prop.location}
🏢 <b>Type:</b> {prop.property_type}
🛋️ <b>Furnished:</b> {furnished_str}
📐 <b>Area:</b> {int(prop.area_m2 or 0)} m²
💰 <b>Rent:</b> {int(prop.effective_monthly_price or prop.price):,} TL/month
🚇 <b>Metrobus:</b> {metrobus_info}
🎓 <b>Istanbul Aydın Univ:</b> {uni_info}
💵 <b>Deposit:</b> {int(prop.deposit or 0):,} TL
🏢 <b>Agency Fee:</b> {prop.agency_fee or 'None'}
📅 <b>Listing Date (تاريخ نشر الإعلان):</b> {prop.listing_date or 'Recent / غير محدد'}
🔎 <b>Status:</b> {prop.verification_status}

🔗 <b>ORIGINAL LISTING:</b>
{prop.url}
"""
        return msg.strip()

    @classmethod
    def send_message(cls, text: str) -> bool:
        if not config.TELEGRAM_ENABLED or not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            logger.info("[Telegram Disabled or Unconfigured] Mock Alert output:\n" + text)
            return True

        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.error(f"Telegram API failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
