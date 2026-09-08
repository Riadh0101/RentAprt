import logging
from typing import Optional
from ..db.models import PropertyRecord, NotificationRecord
from ..db.database import Database
from .telegram import TelegramNotifier
from .email_service import EmailNotifier

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    def __init__(self, db: Database):
        self.db = db

    def process_and_notify(self, prop: PropertyRecord, action_type: str):
        """
        Applies multi-tier notification rules:
        - Tier 1: Score >= 85 or Price <= 25k near IAU or Price Reduction -> Immediate Telegram + Email
        - Tier 2: Score 75-84 -> Telegram only
        - Tier 3: Score 65-74 -> Stored for Daily Report
        - Tier 4: Score < 65 -> Silent
        """
        score = prop.score
        eff_price = prop.effective_monthly_price or prop.price

        is_immediate = False
        is_high_tier = False

        if action_type == "PRICE_REDUCED":
            is_immediate = True
            is_high_tier = True
        elif score >= 85 or (eff_price <= 25000 and (prop.university_distance_min or 30) <= 10):
            is_immediate = True
            is_high_tier = True
        elif score >= 75:
            is_immediate = True
            is_high_tier = False

        if not is_immediate:
            logger.info(f"Listing {prop.title[:30]} (Score: {score}) saved for daily report.")
            return

        # 1. Send Telegram Notification
        msg = TelegramNotifier.format_property_alert(prop, alert_type=action_type)
        t_ok = TelegramNotifier.send_message(msg)
        if t_ok and prop.id:
            self.db.record_notification(
                NotificationRecord(
                    property_id=prop.id,
                    notification_type=action_type,
                    channel="telegram",
                    status="sent"
                )
            )

        # 2. Send Email if High Tier
        if is_high_tier:
            e_ok = EmailNotifier.send_property_alert(prop, alert_type=action_type)
            if e_ok and prop.id:
                self.db.record_notification(
                    NotificationRecord(
                        property_id=prop.id,
                        notification_type=action_type,
                        channel="email",
                        status="sent"
                    )
                )
