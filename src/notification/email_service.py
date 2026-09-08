import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import config
from ..db.models import PropertyRecord

logger = logging.getLogger(__name__)

class EmailNotifier:
    @classmethod
    def send_property_alert(cls, prop: PropertyRecord, alert_type: str = "NEW_LISTING") -> bool:
        subject = f"[Her Alert] New Match in {prop.location} - {int(prop.effective_monthly_price or prop.price):,} TL (Score: {prop.score})"
        if alert_type == "PRICE_REDUCTION":
            subject = f"[Her Alert] Reduced to {int(prop.effective_monthly_price or prop.price):,} TL - {prop.location}"

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px;">
                <h2 style="margin: 0;">🏠 Her Alert — Rental Monitor</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd; border-top: none;">
                <p><strong>Score:</strong> <span style="font-size: 1.2em; color: #27ae60;">{prop.score}/100</span></p>
                <p><strong>Location:</strong> {prop.location}</p>
                <p><strong>Type:</strong> {prop.property_type}</p>
                <p><strong>Rent:</strong> <strong>{int(prop.effective_monthly_price or prop.price):,} TL / month</strong></p>
                <p><strong>Furnished:</strong> {'Yes' if prop.furnished else 'No'}</p>
                <p><strong>Walking to IAU Campus:</strong> {prop.university_distance_min} min</p>
                <p><strong>Walking to Metrobus:</strong> {prop.metrobus_distance_min} min ({prop.metrobus_station})</p>
                <hr>
                <p><a href="{prop.url}" style="background-color: #3498db; color: white; padding: 10px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">View Original Listing</a></p>
            </div>
        </body>
        </html>
        """

        if not config.EMAIL_ENABLED or not config.SMTP_USERNAME:
            logger.info(f"[Email Disabled or Unconfigured] Mock Alert sent for {prop.title}")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config.EMAIL_FROM or config.SMTP_USERNAME
            msg["To"] = config.EMAIL_TO
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.sendmail(msg["From"], [config.EMAIL_TO], msg.as_string())

            logger.info("Email alert dispatched successfully.")
            return True
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
