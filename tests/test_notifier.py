import json
import smtplib

import httpx

from src.config import load_settings
from src.models import FURNISHED, Listing
from src.notifier import (NEW_MATCH, PRICE_DROP, EmailNotifier, TelegramNotifier, format_alert,
                          format_digest, format_email)


def sample(**kw) -> Listing:
    data = dict(source="Emlakjet", source_id="1", url="https://www.emlakjet.com/ilan/a-1?x=1&y=2",
                title="Beşyol <Lüks> & Eşyalı 1+1", price=22000, effective_cost=22500, aidat=500,
                rooms="1+1", area_m2=50, furnished=FURNISHED, neighborhood="Beşyol Mahallesi",
                district="Küçükçekmece", univ_walk_min=4, metrobus_station="Beşyol",
                metrobus_walk_min=3, score=88, classification="EXCELLENT", id=1)
    data.update(kw)
    return Listing(**data)


def test_alert_escapes_html_and_contains_key_facts():
    msg = format_alert(sample(), NEW_MATCH)
    assert "&lt;Lüks&gt; &amp; Eşyalı" in msg
    assert 'href="https://www.emlakjet.com/ilan/a-1?x=1&amp;y=2"' in msg
    assert "88/100" in msg and "22,000 TL" in msg and "22,500 TL" in msg and "Beşyol" in msg


def test_price_drop_alert_shows_old_price_and_percentage():
    msg = format_alert(sample(price=20000), PRICE_DROP, old_price=25000)
    assert "<s>25,000 TL</s>" in msg and "20.0%" in msg


def test_digest_and_email_render():
    stats = dict(active=2, total_tracked=3, new_recent=1, price_drops_recent=0, removed=1,
                 average_cost=24000, lowest_cost=20000, runs_recent=5)
    assert "a-1?x=1&amp;y=2" in format_digest(stats, [sample()])
    subject, body = format_email([(sample(), NEW_MATCH)])
    assert "1" in subject and "&lt;Lüks&gt;" in body


def test_telegram_unconfigured_reports_failure(tmp_path):
    ok, error = TelegramNotifier(load_settings(env={}, base_dir=tmp_path)).send("hi")
    assert not ok and "not configured" in error


def test_telegram_success_and_api_error(tmp_path):
    settings = load_settings(env={"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "42"}, base_dir=tmp_path)
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200 if len(sent) == 1 else 400, text="bad request")

    tg = TelegramNotifier(settings, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert tg.send("<b>x</b>") == (True, "")
    ok, error = tg.send("<b>y</b>")
    assert not ok and "400" in error
    assert sent[0] == {"chat_id": "42", "text": "<b>x</b>", "parse_mode": "HTML",
                       "disable_web_page_preview": False}


class FakeSMTP:
    instances = []

    def __init__(self, host, port, fail=False):
        self.host, self.port, self.fail, self.sent = host, port, fail, []
        FakeSMTP.instances.append(self)

    def login(self, user, password):
        if self.fail:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def sendmail(self, sender, recipients, message):
        self.sent.append((sender, recipients, message))

    def quit(self):
        pass


def test_email_send_and_auth_failure(tmp_path):
    settings = load_settings(env={"SMTP_USERNAME": "me@example.com", "SMTP_PASSWORD": "pw",
                                  "ALERT_RECIPIENT_EMAIL": "parent@example.com"}, base_dir=tmp_path)
    ok, _ = EmailNotifier(settings, smtp_factory=FakeSMTP).send("s", "<p>b</p>")
    assert ok
    sender, recipients, _ = FakeSMTP.instances[-1].sent[0]
    assert sender == "me@example.com" and recipients == ["parent@example.com"]

    failing = EmailNotifier(settings, smtp_factory=lambda h, p: FakeSMTP(h, p, fail=True))
    ok, error = failing.send("s", "b")
    assert not ok and "SMTPAuthenticationError" in error


def test_email_unconfigured(tmp_path):
    ok, error = EmailNotifier(load_settings(env={}, base_dir=tmp_path)).send("s", "b")
    assert not ok and "not configured" in error
