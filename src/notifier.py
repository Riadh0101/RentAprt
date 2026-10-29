"""Telegram and email delivery plus message formatting (Arabic, matching the user's alerts)."""
import html
import logging
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, Dict, Optional, Sequence, Tuple

import httpx

from .config import Settings
from .models import FURNISHED, PARTIAL, Listing

logger = logging.getLogger(__name__)

NEW_MATCH, PRICE_DROP, REACTIVATED = "NEW_MATCH", "PRICE_DROP", "REACTIVATED"
TELEGRAM_LIMIT = 4096

_HEADERS = {
    NEW_MATCH: "🏠 <b>Hermes — شقة مطابقة جديدة</b>",
    PRICE_DROP: "🏷️ <b>Hermes — انخفاض في السعر!</b>",
    REACTIVATED: "♻️ <b>Hermes — إعلان عاد للنشر</b>",
}

Result = Tuple[bool, str]


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _money(value: Optional[float]) -> str:
    return f"{value:,.0f} TL" if value is not None else "—"


def _furnished_text(code: Optional[int]) -> str:
    return {FURNISHED: "نعم (Eşyalı)", PARTIAL: "جزئي (Yarı eşyalı)"}.get(code, "لا / غير محدد")


def _minutes(value: Optional[int]) -> str:
    return f"≈{value} دقيقة مشياً" if value is not None else "غير معروف"


def format_alert(listing: Listing, alert_type: str, old_price: Optional[float] = None) -> str:
    header = _HEADERS.get(alert_type, _HEADERS[NEW_MATCH])
    if listing.classification == "OVER_BUDGET_EXCEPTIONAL" and alert_type == NEW_MATCH:
        header = "💎 <b>Hermes — عرض استثنائي (يتجاوز الميزانية قليلاً)</b>"

    if alert_type == PRICE_DROP and old_price:
        pct = (old_price - listing.price) / old_price * 100
        price_block = (f"📉 <b>السعر القديم:</b> <s>{_money(old_price)}</s>\n"
                       f"🔥 <b>السعر الجديد:</b> <b>{_money(listing.price)}</b> (−{pct:.1f}%)\n")
    else:
        price_block = f"💰 <b>الإيجار الشهري:</b> <b>{_money(listing.price)}</b>\n"
    if listing.aidat:
        price_block += f"🧾 <b>العائدات (Aidat):</b> {_money(listing.aidat)} — <b>الإجمالي:</b> {_money(listing.effective_cost)}\n"
    if listing.bills_included:
        price_block += "✅ <b>الفواتير مشمولة بالإيجار</b>\n"

    station = f" ({_e(listing.metrobus_station)})" if listing.metrobus_station else ""
    lines = [
        f"⏱️ <code>{datetime.now():%Y-%m-%d %H:%M}</code>",
        header,
        "",
        f"⭐ <b>التقييم:</b> <code>{listing.score}/100</code> — <b>[{_e(listing.classification)}]</b>",
        f"📝 {_e(listing.title)}",
        f"📍 <b>المنطقة:</b> {_e(listing.location or 'Istanbul')}",
        f"🏢 <b>النوع:</b> {_e(listing.rooms or '?')} | <b>المساحة:</b> {_e(int(listing.area_m2)) if listing.area_m2 else '?'} م²",
        f"🛋️ <b>مفروشة:</b> {_furnished_text(listing.furnished)}",
        price_block.rstrip("\n"),
        f"💵 <b>التأمين (Depozito):</b> {_money(listing.deposit)}",
        f"🎓 <b>جامعة أيدن:</b> {_minutes(listing.univ_walk_min)}",
        f"🚇 <b>المتروباص{station}:</b> {_minutes(listing.metrobus_walk_min)}",
        f"📅 <b>آخر تحديث للإعلان:</b> <code>{_e(listing.updated_date or listing.listing_date or 'غير محدد')}</code>",
        "",
        f'🔗 <a href="{_e(listing.url)}">فتح الإعلان الأصلي</a>',
    ]
    return "\n".join(lines)[:TELEGRAM_LIMIT]


def format_digest(stats: Dict, top: Sequence[Listing]) -> str:
    lines = [
        "📊 <b>Hermes — الملخص اليومي لسوق الإيجار</b>",
        "",
        f"• الإعلانات النشطة: <b>{stats['active']}</b> (من أصل {stats['total_tracked']})",
        f"• جديدة خلال 24 ساعة: <b>{stats['new_recent']}</b>",
        f"• انخفاضات أسعار خلال 24 ساعة: <b>{stats['price_drops_recent']}</b>",
        f"• إعلانات أزيلت: {stats['removed']}",
        f"• متوسط التكلفة الشهرية: {_money(stats['average_cost'])} | الأدنى: {_money(stats['lowest_cost'])}",
        f"• دورات البحث خلال 24 ساعة: {stats['runs_recent']}",
        "",
        "🏆 <b>أفضل العروض حالياً:</b>",
    ]
    if not top:
        lines.append("لا توجد عروض مؤهلة حالياً.")
    for i, p in enumerate(top, 1):
        lines.append(
            f'{i}. <a href="{_e(p.url)}">{_e(p.title[:60])}</a>\n'
            f"   ⭐ {p.score}/100 | 💰 {_money(p.effective_cost)} | 📍 {_e(p.location)} | "
            f"🎓 {_minutes(p.univ_walk_min)}"
        )
    return "\n".join(lines)[:TELEGRAM_LIMIT]


def format_email(items: Sequence[Tuple[Listing, str]]) -> Tuple[str, str]:
    """(subject, html body) for a batch of alerted listings."""
    labels = {NEW_MATCH: "جديد", PRICE_DROP: "انخفاض سعر", REACTIVATED: "عاد للنشر"}
    cards = []
    for listing, alert_type in items:
        cards.append(f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:14px;margin-bottom:14px;background:#fff">
          <div style="font-size:16px;font-weight:bold;color:#1a73e8">{_e(listing.title)}</div>
          <div style="margin:6px 0;color:#137333;font-weight:bold">{listing.score}/100 — {_e(listing.classification)} — {labels.get(alert_type, alert_type)}</div>
          <p style="margin:4px 0">📍 {_e(listing.location)} | 🏢 {_e(listing.rooms or '?')} | 🛋️ {_furnished_text(listing.furnished)}</p>
          <p style="margin:4px 0;color:#d93025">💰 {_money(listing.price)} (الإجمالي مع العائدات: {_money(listing.effective_cost)})</p>
          <p style="margin:4px 0">🎓 {_minutes(listing.univ_walk_min)} | 🚇 {_minutes(listing.metrobus_walk_min)}</p>
          <a href="{_e(listing.url)}" style="background:#1a73e8;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px;display:inline-block">فتح الإعلان الأصلي 🔗</a>
        </div>""")
    body = f"""<div dir="rtl" style="font-family:Arial,Tahoma,sans-serif;background:#f8f9fa;padding:20px;color:#333">
      <div style="max-width:650px;margin:0 auto">
        <h2 style="color:#1a73e8">🏠 Hermes — عروض سكن جديدة قرب جامعة إسطنبول أيدن</h2>
        <p>⏱️ {datetime.now():%Y-%m-%d %H:%M}</p>
        {''.join(cards)}
      </div></div>"""
    subject = f"🏠 Hermes — {len(items)} عرض سكن جديد ({datetime.now():%Y-%m-%d %H:%M})"
    return subject, body


class TelegramNotifier:
    def __init__(self, settings: Settings, http: Optional[httpx.Client] = None):
        self.settings = settings
        self.http = http

    @property
    def enabled(self) -> bool:
        return self.settings.telegram_enabled

    def send(self, text: str) -> Result:
        if not self.enabled:
            return False, "telegram not configured"
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {"chat_id": self.settings.telegram_chat_id, "text": text,
                   "parse_mode": "HTML", "disable_web_page_preview": False}
        try:
            if self.http is not None:
                resp = self.http.post(url, json=payload, timeout=15)
            else:
                with httpx.Client(timeout=15) as client:
                    resp = client.post(url, json=payload)
        except httpx.HTTPError as e:
            return False, f"{type(e).__name__}: {e}"
        if resp.status_code == 200:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"


class EmailNotifier:
    def __init__(self, settings: Settings, smtp_factory: Optional[Callable] = None):
        self.settings = settings
        self._smtp_factory = smtp_factory

    @property
    def enabled(self) -> bool:
        s = self.settings
        return bool(s.email_enabled and s.smtp_username and s.smtp_password and s.alert_recipient_email)

    def _connect(self):
        s = self.settings
        if self._smtp_factory:
            return self._smtp_factory(s.smtp_server, s.smtp_port)
        if s.smtp_port == 465:
            return smtplib.SMTP_SSL(s.smtp_server, s.smtp_port, timeout=20)
        server = smtplib.SMTP(s.smtp_server, s.smtp_port, timeout=20)
        server.starttls()
        return server

    def send(self, subject: str, html_body: str) -> Result:
        if not self.enabled:
            return False, "email not configured"
        s = self.settings
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = s.email_from or s.smtp_username
        msg["To"] = s.alert_recipient_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        try:
            server = self._connect()
            try:
                server.login(s.smtp_username, s.smtp_password)
                server.sendmail(msg["From"], [s.alert_recipient_email], msg.as_string())
            finally:
                server.quit()
        except (smtplib.SMTPException, OSError) as e:
            return False, f"{type(e).__name__}: {e}"
        return True, ""


def preview(text: str) -> str:
    """Plain-text rendering of a Telegram HTML message for the console."""
    return html.unescape(re.sub(r"<[^>]+>", "", text))
