from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.config import load_settings
from src.database import ACTIVE, REMOVED, Database
from src.notifier import EmailNotifier, TelegramNotifier
from src.pipeline import Monitor
from src.scraper import EmlakjetClient
from tests.conftest import FakeSite, feed_html, listing_html, listing_url
from tests.test_notifier import FakeSMTP

T0 = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
GOOD = dict(id="100", price=21000, rooms="1+1", konum="Beşyol Mahallesi, Küçükçekmece")
WEAK = dict(id="200", price=34000, rooms="1+0", konum="Beşyol Mahallesi, Küçükçekmece")


class TelegramRecorder:
    def __init__(self, status=200):
        self.messages, self.status = [], status

    def handler(self, request):
        import json
        self.messages.append(json.loads(request.content)["text"])
        return httpx.Response(self.status, text="{}")


@pytest.fixture
def env():
    return {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "1"}


def build(settings, site: FakeSite, tg: TelegramRecorder, smtp=None) -> Monitor:
    db = Database(settings.db_path)
    client = EmlakjetClient(settings, http=site.client(), sleep=lambda s: None, retries=0)
    telegram = TelegramNotifier(settings, http=httpx.Client(transport=httpx.MockTransport(tg.handler)))
    return Monitor(settings, db, client, telegram, EmailNotifier(settings, smtp_factory=smtp))


def publish(site, *entries, prices=None):
    site.feeds["besyol"] = feed_html(list(entries))
    for e in entries:
        page = {"furnished": "Eşyasız", "updated": "1 Ocak 2026", "images": 0, "description": "Kiralık."} \
            if e["id"] == WEAK["id"] else {}
        site.set_listing(e["id"], listing_html(e["id"], e["price"], rooms_title=f"{e['rooms']} Oda", **page))


def listing_requests(site):
    return [u for u in site.requests if "/ilan/" in u]


def test_full_lifecycle_new_unchanged_price_drop_removed(settings, site):
    tg = TelegramRecorder()
    monitor = build(settings, site, tg)
    publish(site, GOOD, WEAK)

    r1 = monitor.run_cycle(T0)
    assert (r1.new, r1.verified, r1.alerts_sent) == (2, 2, 1)
    assert len(tg.messages) == 1 and "21,000 TL" in tg.messages[0]

    # Same feed shortly after: no page refetches, no repeated alerts
    site.requests.clear()
    r2 = monitor.run_cycle(T0 + timedelta(minutes=20))
    assert listing_requests(site) == [] and r2.new == 0 and len(tg.messages) == 1

    # Price drop on the feed triggers a refetch and exactly one alert
    publish(site, dict(GOOD, price=19000), WEAK)
    r3 = monitor.run_cycle(T0 + timedelta(minutes=40))
    assert r3.price_drops == 1 and len(tg.messages) == 2
    assert "<s>21,000 TL</s>" in tg.messages[1]
    monitor.run_cycle(T0 + timedelta(minutes=60))
    assert len(tg.messages) == 2

    # Listing disappears from the feed and its page 404s -> removed after REVERIFY_HOURS
    site.feeds["besyol"] = feed_html([WEAK])
    del site.listings[GOOD["id"]]
    r5 = monitor.run_cycle(T0 + timedelta(hours=8))
    assert r5.removed == 1
    assert monitor.db.get_row("Emlakjet", GOOD["id"])["status"] == REMOVED
    assert monitor.db.get_row("Emlakjet", WEAK["id"])["status"] == ACTIVE


def test_family_only_and_over_limit_listings_not_stored(settings, site):
    tg = TelegramRecorder()
    monitor = build(settings, site, tg)
    site.feeds["besyol"] = feed_html([dict(GOOD), dict(id="300", price=50000)])
    site.set_listing("100", listing_html("100", 21000, description="SADECE AİLEYE KİRALIKTIR."))
    report = monitor.run_cycle(T0)
    assert report.rejected == 2 and report.new == 0
    assert monitor.db.active_listings() == [] and tg.messages == []
    assert not any(u.endswith("-300") for u in site.requests)  # over-limit never fetched


def test_failed_telegram_alert_is_retried_next_cycle(settings, site):
    tg = TelegramRecorder(status=500)
    monitor = build(settings, site, tg)
    publish(site, GOOD)
    assert monitor.run_cycle(T0).alerts_sent == 0
    tg.status = 200
    assert monitor.run_cycle(T0 + timedelta(minutes=20)).alerts_sent == 1
    monitor.run_cycle(T0 + timedelta(minutes=40))
    assert len(tg.messages) == 2  # failed attempt + successful retry, then nothing more


def test_unconfigured_telegram_prints_preview(tmp_path, site, capsys):
    settings = load_settings(env={"REQUEST_DELAY_SECONDS": "0"}, base_dir=tmp_path)
    tg = TelegramRecorder()
    monitor = build(settings, site, tg)
    publish(site, GOOD)
    monitor.run_cycle(T0)
    assert "alert preview" in capsys.readouterr().out
    assert tg.messages == []


def test_high_score_listing_emailed_once(tmp_path, site):
    settings = load_settings(env={"REQUEST_DELAY_SECONDS": "0", "TELEGRAM_BOT_TOKEN": "t",
                                  "TELEGRAM_CHAT_ID": "1", "SMTP_USERNAME": "me@example.com",
                                  "SMTP_PASSWORD": "pw", "ALERT_RECIPIENT_EMAIL": "to@example.com"},
                             base_dir=tmp_path)
    FakeSMTP.instances.clear()
    monitor = build(settings, site, TelegramRecorder(), smtp=FakeSMTP)
    publish(site, GOOD, WEAK)
    monitor.run_cycle(T0)
    monitor.run_cycle(T0 + timedelta(minutes=20))
    emails = [m for s in FakeSMTP.instances for m in s.sent]
    assert len(emails) == 1


def test_watchlist_listing_is_tracked(tmp_path, site):
    (tmp_path / "watchlist.txt").write_text(f"# comment\n{listing_url('555')}\nnot a url\n", encoding="utf-8")
    settings = load_settings(env={"REQUEST_DELAY_SECONDS": "0"}, base_dir=tmp_path)
    site.set_listing("555", listing_html("555", 24000))
    monitor = build(settings, site, TelegramRecorder())
    assert monitor.run_cycle(T0).new == 1
    assert monitor.db.get_row("Emlakjet", "555")["neighborhood"] == "Beşyol Mahallesi"


def test_health_alert_after_consecutive_feed_failures(settings, site):
    tg = TelegramRecorder()
    monitor = build(settings, site, tg)
    site.feed_status = 503
    for i in range(4):
        report = monitor.run_cycle(T0 + timedelta(minutes=20 * i))
        assert report.feeds_failed == report.feeds_checked
    health = [m for m in tg.messages if "تحذير" in m]
    assert len(health) == 1


def test_daily_digest_lists_top_listings(settings, site):
    tg = TelegramRecorder()
    monitor = build(settings, site, tg)
    publish(site, GOOD)
    monitor.run_cycle(T0)
    text = monitor.daily_digest(send=True)
    assert "21,000 TL" in text or "21,500 TL" in text
    assert tg.messages[-1] == text
