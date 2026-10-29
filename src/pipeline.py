"""One monitoring cycle: FEEDS -> VERIFY -> FILTER -> SCORE -> STORE -> ALERT, plus the daily digest."""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from . import database as dbm
from .config import Settings
from .database import Database
from .models import CycleReport, FeedItem, Listing
from .notifier import (NEW_MATCH, PRICE_DROP, REACTIVATED, EmailNotifier, TelegramNotifier,
                       format_alert, format_digest, format_email, preview)
from .scoring import build_listing, check_eligibility, score_listing
from .scraper import ACTIVE, SOURCE, EmlakjetClient, FetchError, source_id_from_url

logger = logging.getLogger(__name__)

HEALTH_ALERT_AFTER = 3  # consecutive cycles with every feed failing

Event = Tuple[Listing, str, Optional[float]]  # (listing, alert type, previous price)


def read_watchlist(settings: Settings) -> List[FeedItem]:
    """Listing URLs the user wants tracked even if they drop out of the feeds."""
    path = settings.watchlist_path
    if not path or not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        url = line.split("#", 1)[0].strip()
        source_id = source_id_from_url(url) if url else None
        if source_id:
            items.append(FeedItem(source=SOURCE, source_id=source_id, url=url, feed_label="watchlist"))
        elif url:
            logger.warning("Ignoring watchlist entry that is not an Emlakjet listing URL: %s", url)
    return items


def _item_from_row(row: sqlite3.Row) -> FeedItem:
    location = ", ".join(p for p in (row["neighborhood"], row["district"]) if p)
    return FeedItem(source=row["source"], source_id=row["source_id"], url=row["url"],
                    title=row["title"], price=row["price"], rooms=row["rooms"],
                    area_m2=row["area_m2"], location=location, date_posted=row["listing_date"])


class Monitor:
    def __init__(self, settings: Settings, db: Database, client: EmlakjetClient,
                 telegram: Optional[TelegramNotifier] = None, email: Optional[EmailNotifier] = None):
        self.settings = settings
        self.db = db
        self.client = client
        self.telegram = telegram or TelegramNotifier(settings)
        self.email = email or EmailNotifier(settings)
        self.consecutive_feed_failures = 0

    # ---- cycle ----------------------------------------------------------

    def run_cycle(self, now: Optional[datetime] = None) -> CycleReport:
        now = now or dbm.utcnow()
        report = CycleReport(started_at=now.isoformat(timespec="seconds"))
        events: List[Event] = []
        seen_ids: set = set()

        items = self._collect_items(report)
        report.candidates = len(items)
        for item in items.values():
            self._process(item, self.db.get_row(item.source, item.source_id), now, report, events, seen_ids)

        for row in self.db.stale_active(seen_ids, self.settings.reverify_hours,
                                        self.settings.max_reverify_per_cycle, now):
            self._process(_item_from_row(row), row, now, report, events, seen_ids, force=True)

        self._dispatch_alerts(events, report)
        self._check_health(report)

        report.finished_at = dbm.utcnow().isoformat(timespec="seconds")
        self.db.record_run(report)
        logger.info("Cycle finished: %s", report.summary())
        return report

    def _collect_items(self, report: CycleReport) -> Dict[str, FeedItem]:
        items: Dict[str, FeedItem] = {}
        for label, url in self.settings.feed_urls():
            report.feeds_checked += 1
            try:
                found = self.client.fetch_feed(url, label)
            except FetchError as e:
                report.feeds_failed += 1
                logger.warning("Feed %s failed: %s", label, e)
                continue
            logger.info("Feed %s: %d listings", label, len(found))
            for item in found:
                items.setdefault(item.source_id, item)
        for item in read_watchlist(self.settings):
            items.setdefault(item.source_id, item)
        return items

    def _is_fresh(self, row: sqlite3.Row, now: datetime) -> bool:
        verified = datetime.fromisoformat(row["last_verified"])
        return now - verified < timedelta(hours=self.settings.reverify_hours)

    def _process(self, item: FeedItem, row: Optional[sqlite3.Row], now: datetime,
                 report: CycleReport, events: List[Event], seen_ids: set, force: bool = False):
        s = self.settings
        if row is not None:
            seen_ids.add(row["id"])

        # Cheap rejection from feed data, before fetching the listing page
        if item.price and item.price > s.exceptional_budget_limit_tl or (
                item.rooms and item.rooms not in s.allowed_rooms):
            report.rejected += 1
            if row is not None and row["status"] == dbm.ACTIVE:
                self.db.set_status(row["id"], dbm.REJECTED, "price or room layout out of range", now)
            return

        # Known listing at the same price and verified recently: no need to refetch
        if (not force and row is not None and self._is_fresh(row, now)
                and (item.price is None or item.price == row["price"])):
            if row["status"] == dbm.ACTIVE:
                self.db.touch_seen(row["id"], now)
            elif row["status"] == dbm.REJECTED:
                report.rejected += 1
            return

        try:
            status, detail, reason = self.client.fetch_listing(item.url)
        except FetchError as e:
            report.errors += 1
            logger.warning("Could not verify %s: %s", item.url, e)
            return
        report.verified += 1

        if status != ACTIVE:
            if item.feed_label == "watchlist" and (row is None or row["status"] == dbm.ACTIVE):
                logger.warning("Watchlist listing is no longer online (%s): %s", reason, item.url)
            if row is not None and row["status"] == dbm.ACTIVE:
                self.db.set_status(row["id"], dbm.REMOVED, reason, now)
                report.removed += 1
                logger.info("Listing removed: %s (%s)", item.url, reason)
            return

        listing = build_listing(item, detail, s)
        eligible, reason = check_eligibility(listing, s)
        if not eligible:
            report.rejected += 1
            if row is not None:
                self.db.set_status(row["id"], dbm.REJECTED, reason, now)
            logger.debug("Rejected %s: %s", item.url, reason)
            return

        score_listing(listing, s, now.date())
        change, old_price = self.db.upsert(listing, now)
        seen_ids.add(listing.id)
        if change == dbm.NEW:
            report.new += 1
            events.append((listing, NEW_MATCH, None))
        elif change == dbm.PRICE_DROP:
            report.price_drops += 1
            events.append((listing, PRICE_DROP, old_price))
        elif change == dbm.PRICE_INCREASE:
            report.price_increases += 1
        elif change == dbm.REACTIVATED:
            report.reactivated += 1
            events.append((listing, REACTIVATED, None))

    # ---- alerts ---------------------------------------------------------

    def _qualifies(self, listing: Listing, alert_type: str) -> bool:
        if alert_type == PRICE_DROP:
            return listing.score >= self.settings.score_daily_digest
        return (listing.score >= self.settings.score_instant_alert
                or listing.classification == "OVER_BUDGET_EXCEPTIONAL")

    def _high_tier(self, listing: Listing, alert_type: str) -> bool:
        return alert_type == PRICE_DROP or listing.score >= self.settings.score_multi_channel_alert

    def _pending_new_matches(self, exclude: set) -> List[Event]:
        """Qualifying active listings whose NEW_MATCH alert was never delivered (e.g. Telegram was down)."""
        pending = []
        for listing in self.db.active_listings(min_score=self.settings.score_daily_digest):
            if listing.id in exclude or not self._qualifies(listing, NEW_MATCH):
                continue
            if not self.db.was_alerted(listing.id, NEW_MATCH, "telegram"):
                pending.append((listing, NEW_MATCH, None))
        return pending

    def _dispatch_alerts(self, events: List[Event], report: CycleReport):
        due = [e for e in events if self._qualifies(e[0], e[1])]
        if self.telegram.enabled:
            due += self._pending_new_matches({e[0].id for e in due})
        due.sort(key=lambda e: e[0].score, reverse=True)

        def alert_price(listing: Listing, alert_type: str) -> Optional[float]:
            return listing.price if alert_type != NEW_MATCH else None

        sent = 0
        email_batch: List[Tuple[Listing, str]] = []
        for listing, alert_type, old_price in due:
            key_price = alert_price(listing, alert_type)
            if self.telegram.enabled:
                if sent >= self.settings.max_alerts_per_cycle:
                    break
                if not self.db.was_alerted(listing.id, alert_type, "telegram", key_price):
                    ok, error = self.telegram.send(format_alert(listing, alert_type, old_price))
                    self.db.log_alert(listing.id, alert_type, "telegram", ok, key_price, error)
                    sent += ok
                    if not ok:
                        logger.error("Telegram alert failed for %s: %s", listing.url, error)
            else:
                print("\n" + "=" * 60 + "\n[Telegram not configured — alert preview]\n"
                      + preview(format_alert(listing, alert_type, old_price)) + "\n" + "=" * 60)
            if (self.email.enabled and self._high_tier(listing, alert_type)
                    and not self.db.was_alerted(listing.id, alert_type, "email", key_price)):
                email_batch.append((listing, alert_type))

        if email_batch:
            ok, error = self.email.send(*format_email(email_batch))
            for listing, alert_type in email_batch:
                self.db.log_alert(listing.id, alert_type, "email", ok, alert_price(listing, alert_type), error)
            if not ok:
                logger.error("Email alert failed: %s", error)
        report.alerts_sent = sent

    def _check_health(self, report: CycleReport):
        if report.feeds_checked and report.feeds_failed == report.feeds_checked:
            self.consecutive_feed_failures += 1
        else:
            self.consecutive_feed_failures = 0
        if self.consecutive_feed_failures == HEALTH_ALERT_AFTER:
            message = (f"🚨 <b>Hermes — تحذير</b>\nفشل الوصول إلى جميع مصادر البحث في "
                       f"{HEALTH_ALERT_AFTER} دورات متتالية. يرجى التحقق من الاتصال أو من تغيّر موقع Emlakjet.")
            ok, error = self.telegram.send(message)
            self.db.log_alert(None, "HEALTH", "telegram", ok, None, error)
            logger.error("All feeds failed %d cycles in a row", HEALTH_ALERT_AFTER)

    # ---- digest ---------------------------------------------------------

    def daily_digest(self, send: bool = True) -> str:
        stats = self.db.statistics()
        top = self.db.active_listings(min_score=self.settings.score_daily_digest, limit=10)
        text = format_digest(stats, top)
        if send and self.telegram.enabled:
            ok, error = self.telegram.send(text)
            self.db.log_alert(None, "DAILY_DIGEST", "telegram", ok, None, error)
        if send and self.email.enabled and top:
            ok, error = self.email.send(*format_email([(p, NEW_MATCH) for p in top]))
            self.db.log_alert(None, "DAILY_DIGEST", "email", ok, None, error)
        return text
