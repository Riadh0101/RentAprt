import html
import logging
from typing import Dict, Any, Optional
import httpx
from src.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, ALERT_RECIPIENT_EMAIL
)
from datetime import datetime
from src.database import record_notification

logger = logging.getLogger("HermesNotifier")

def format_telegram_alert(prop: Dict[str, Any], alert_type: str = "NEW_MATCH") -> str:
    """Format property details into a clean Telegram HTML message."""
    send_time = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
    time_banner = f"⏱️ <b>تاريخ وتوقيت الإرسال:</b> <code>{send_time}</code>\n"

    score = prop.get("score", 0)
    classification = prop.get("classification", "MATCH")
    title = html.escape(prop.get("title", "Apartment Listing"))
    location = html.escape(prop.get("location", "Istanbul"))
    rooms = html.escape(prop.get("rooms", "1+1"))
    furnished_txt = "نعم (Furnished / Eşyalı)" if prop.get("furnished") == 1 else "جزئي" if prop.get("furnished") == 2 else "لا"
    price = f"{float(prop.get('price_tl', 0.0)):,.0f}"
    area = prop.get("area_m2") or "N/A"
    univ_mins = prop.get("univ_dist_min", "?")
    metro_mins = prop.get("metrobus_dist_min", "?")
    contact = html.escape(str(prop.get("contact_info") or "متوفر في الإعلان"))
    url = prop.get("url", "#")
    source = html.escape(prop.get("source", "Web"))

    listing_date = html.escape(str(prop.get("listing_date") or "اليوم / حديث"))

    if alert_type == "PRICE_DROP":
        old_p = f"{float(prop.get('old_price', 0.0)):,.0f}"
        drop_pct = prop.get("price_drop_pct", 0)
        header = f"🏷️ <b>AG Alert — انخفاض في السعر!</b>\n\n"
        price_block = f"📉 <b>السعر القديم:</b> <s>{old_p} TL</s>\n🔥 <b>السعر الجديد:</b> <b>{price} TL</b> (خصم {drop_pct}%)\n"
    elif classification == "OVER_BUDGET_EXCEPTIONAL":
        header = f"💎 <b>AG Alert — عرض استثنائي (يتجاوز الميزانية قليلاً)</b>\n\n"
        price_block = f"💰 <b>الإيجار الشهري:</b> <b>{price} TL</b> (يتجاوز 36k ولكن الموقع/الجودة ممتازة)\n"
    else:
        header = f"🏠 <b>AG Alert — شقة مطابقة جديدة</b>\n\n"
        price_block = f"💰 <b>الإيجار الشهري:</b> <b>{price} TL</b>\n"

    msg = (
        f"{time_banner}"
        f"{header}"
        f"⭐ <b>التقييم:</b> <code>{score}/100</code> — <b>[{classification}]</b>\n\n"
        f"📍 <b>المنطقة:</b> {location}\n"
        f"🏢 <b>النوع:</b> {rooms} | <b>المساحة:</b> {area} م²\n"
        f"🛋️ <b>مفروشة:</b> {furnished_txt}\n"
        f"{price_block}"
        f"🎓 <b>جامعة أيدن:</b> <b>{univ_mins} دقائق مشياً</b>\n"
        f"🚇 <b>محطة المتروباص:</b> <b>{metro_mins} دقائق مشياً</b>\n"
        f"📅 <b>تاريخ نشر/تحديث الإعلان:</b> <code>{listing_date}</code>\n"
        f"📞 <b>بيانات التواصل:</b> {contact}\n"
        f"🔗 <b>رابط الإعلان المباشر (اضغط للفتح فوراً):</b>\n{url}"
    )
    return msg

def send_telegram_message(message_html: str) -> bool:
    """Send message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info("[Telegram Disabled] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in .env.")
        print("\n" + "="*50)
        print("📢 [TELEGRAM PREVIEW - NOT CONFIGURED IN .env]:")
        # Strip simple tags for console output
        plain = message_html.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
        print(plain)
        print("="*50 + "\n")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert dispatched successfully.")
                return True
            else:
                logger.error(f"Telegram API failed with code {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Error dispatching Telegram message: {e}")
        return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_report(properties: list, recipient_email: str = None) -> bool:
    """Send a formatted HTML email report of properties to recipient."""
    recipient = recipient_email or ALERT_RECIPIENT_EMAIL or "Riadh0101@yahoo.fr"
    if not recipient:
        logger.warning("No email recipient configured.")
        return False

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.info(f"[Email Queued] SMTP_USERNAME or SMTP_PASSWORD not set in .env. Email to {recipient} requires an App Password.")
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🏠 Her Alert — تقرير نتائج البحث الجديد ({now_str})"

    # Build HTML email
    items_html = ""
    for idx, prop in enumerate(properties, 1):
        price = f"{float(prop.get('price_tl', 0)):,.0f} TL"
        items_html += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 16px; font-weight: bold; color: #1a73e8;">#{idx}. {html.escape(prop.get('title', ''))}</span>
                <span style="background: #e6f4ea; color: #137333; font-weight: bold; padding: 4px 10px; border-radius: 12px;">{prop.get('score')}/100 - {prop.get('classification')}</span>
            </div>
            <p style="margin: 4px 0; color: #555;">📍 <b>المنطقة:</b> {html.escape(prop.get('location', ''))} | 🏢 <b>النوع:</b> {prop.get('rooms')} | 🛋️ <b>مفروشة:</b> {'نعم' if prop.get('furnished') == 1 else 'لا'}</p>
            <p style="margin: 4px 0; color: #555;">📅 <b>تاريخ نشر/تحديث الإعلان:</b> <b>{html.escape(str(prop.get('listing_date') or 'اليوم / حديث'))}</b></p>
            <p style="margin: 4px 0; font-size: 16px; color: #d93025;">💰 <b>الإيجار الشهري:</b> <b>{price}</b></p>
            <p style="margin: 4px 0; color: #333;">🎓 <b>جامعة أيدن:</b> {prop.get('univ_dist_min')} دقيقة مشياً | 🚇 <b>المتروباص:</b> {prop.get('metrobus_dist_min')} دقيقة</p>
            <p style="margin: 4px 0; color: #666;">📞 <b>بيانات التواصل:</b> {html.escape(str(prop.get('contact_info') or 'متوفر في الإعلان'))}</p>
            <div style="margin-top: 10px;">
                <a href="{prop.get('url', '#')}" style="background: #1a73e8; color: #ffffff; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">فتح رابط الإعلان الأصلي 🔗</a>
            </div>
        </div>
        """

    full_html = f"""
    <div dir="rtl" style="font-family: Arial, Tahoma, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333;">
        <div style="max-width: 650px; margin: 0 auto; background: #ffffff; padding: 25px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <div style="border-bottom: 2px solid #1a73e8; padding-bottom: 12px; margin-bottom: 20px;">
                <h2 style="color: #1a73e8; margin: 0 0 6px 0;">🏠 AG Alert — نتائج البحث</h2>
                <p style="margin: 0; color: #666; font-size: 14px;">⏱️ <b>تاريخ وتوقيت الإرسال:</b> {now_str}</p>
            </div>
            <p style="font-size: 15px;">تم إجراء فحص شامل وجديد لسوق عقارات الطلاب في إسطنبول بمحيط <b>جامعة إسطنبول أيدن</b> وخط المتروباص، وهذه هي أفضل العروض المؤهلة المطابقة لشروطك:</p>
            {items_html}
            <div style="border-top: 1px solid #eee; padding-top: 15px; margin-top: 25px; font-size: 12px; color: #888; text-align: center;">
                نظام HERMES للمراقبة المستمرة — تم الإرسال آلياً إلى {recipient}
            </div>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient
    msg.attach(MIMEText(full_html, "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, [recipient], msg.as_string())
        server.quit()
        logger.info(f"Email report successfully sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        return False

def dispatch_alert(prop: Dict[str, Any], alert_type: str = "NEW_MATCH") -> bool:
    """Dispatch alert via Telegram and record in database."""
    msg = format_telegram_alert(prop, alert_type)
    success = send_telegram_message(msg)
    
    prop_id = prop.get("id")
    if prop_id:
        record_notification(prop_id, channel="telegram", alert_type=alert_type)
    
    return success
