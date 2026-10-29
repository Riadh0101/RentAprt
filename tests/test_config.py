from src.config import load_settings


def test_defaults(tmp_path):
    s = load_settings(env={}, base_dir=tmp_path)
    assert s.cycle_interval_minutes == 20
    assert s.max_budget_tl == 36000
    assert s.db_path == tmp_path / "data" / "rentals.db"
    assert not s.telegram_enabled and not s.email_enabled


def test_env_example_names_are_honoured(tmp_path):
    s = load_settings(env={
        "TARGET_MAX_BUDGET_TL": "30000", "SMTP_SERVER": "smtp.mail.yahoo.com", "SMTP_PORT": "465",
        "SMTP_USERNAME": "u@example.com", "SMTP_PASSWORD": "app-pass",
        "ALERT_RECIPIENT_EMAIL": "to@example.com", "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1",
    }, base_dir=tmp_path)
    assert s.max_budget_tl == 30000
    assert s.smtp_server == "smtp.mail.yahoo.com" and s.smtp_port == 465
    assert s.alert_recipient_email == "to@example.com"
    assert s.email_enabled and s.telegram_enabled


def test_legacy_names_still_work(tmp_path):
    s = load_settings(env={"MAX_BUDGET_TL": "25000", "SMTP_HOST": "h", "EMAIL_TO": "x@example.com"},
                      base_dir=tmp_path)
    assert (s.max_budget_tl, s.smtp_server, s.alert_recipient_email) == (25000, "h", "x@example.com")


def test_email_can_be_disabled_explicitly(tmp_path):
    s = load_settings(env={"SMTP_USERNAME": "u", "SMTP_PASSWORD": "p", "ALERT_RECIPIENT_EMAIL": "r",
                           "EMAIL_ENABLED": "false"}, base_dir=tmp_path)
    assert not s.email_enabled


def test_feed_urls_use_hard_price_limit(tmp_path):
    s = load_settings(env={"EXCEPTIONAL_BUDGET_LIMIT_TL": "40000"}, base_dir=tmp_path)
    assert all(url.endswith("?fiyat=0-40000") for _, url in s.feed_urls())
