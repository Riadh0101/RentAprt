import sqlite3
from datetime import datetime, timedelta, timezone

from src.database import (ACTIVE, NEW, PRICE_DROP, PRICE_INCREASE, REACTIVATED, REMOVED, UNCHANGED,
                          Database)
from src.models import Listing

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def listing(source_id="1", price=25000.0, **kw) -> Listing:
    return Listing(source="Emlakjet", source_id=source_id, url=f"https://x/ilan/a-{source_id}",
                   title=kw.pop("title", "Daire"), price=price, effective_cost=price,
                   neighborhood="Beşyol Mahallesi", photos=["a.jpg"], score=kw.pop("score", 80),
                   score_breakdown={"price_budget": 15}, **kw)


def test_creates_data_directory(tmp_path):
    db = Database(tmp_path / "nested" / "dir" / "rentals.db")
    assert db.path.exists()


def test_upsert_lifecycle_and_price_history(db):
    assert db.upsert(listing(price=26000), NOW) == (NEW, None)
    assert db.upsert(listing(price=26000), NOW) == (UNCHANGED, 26000)
    assert db.upsert(listing(price=22000), NOW) == (PRICE_DROP, 26000)
    drop = db.price_drop(1)
    assert drop["change_pct"] == -15.38
    assert db.upsert(listing(price=23000), NOW) == (PRICE_INCREASE, 22000)
    assert db.price_drop(1) is None
    db.set_status(1, REMOVED, "gone", NOW)
    assert db.upsert(listing(price=23000), NOW) == (REACTIVATED, 23000)
    stored = db.get_listing(1)
    assert stored.price == 23000 and stored.photos == ["a.jpg"]
    assert stored.score_breakdown == {"price_budget": 15}


def test_distinct_listings_with_same_attributes_are_not_merged(db):
    """Regression: the old fingerprint merged different flats in the same neighbourhood."""
    assert db.upsert(listing("1", 30000), NOW)[0] == NEW
    assert db.upsert(listing("2", 25000), NOW)[0] == NEW
    assert len(db.active_listings()) == 2


def test_stale_active_respects_cutoff_seen_and_limit(db):
    for i in range(3):
        db.upsert(listing(str(i)), NOW - timedelta(hours=10))
    db.upsert(listing("fresh"), NOW)
    stale = db.stale_active(seen_ids={1}, older_than_hours=6, limit=5, now=NOW)
    assert [r["source_id"] for r in stale] == ["1", "2"]
    assert len(db.stale_active(set(), 6, limit=1, now=NOW)) == 1


def test_alert_dedup_by_type_channel_and_price(db):
    db.upsert(listing(), NOW)
    assert not db.was_alerted(1, "NEW_MATCH", "telegram")
    db.log_alert(1, "NEW_MATCH", "telegram", ok=False, error="boom")
    assert not db.was_alerted(1, "NEW_MATCH", "telegram")  # failed sends don't count
    db.log_alert(1, "NEW_MATCH", "telegram", ok=True)
    assert db.was_alerted(1, "NEW_MATCH", "telegram")
    assert not db.was_alerted(1, "NEW_MATCH", "email")
    db.log_alert(1, "PRICE_DROP", "telegram", ok=True, price=22000)
    assert db.was_alerted(1, "PRICE_DROP", "telegram", 22000)
    assert not db.was_alerted(1, "PRICE_DROP", "telegram", 20000)


def test_coexists_with_legacy_schema(tmp_path):
    """An old rentals.db with the previous 'properties' table must not break startup."""
    path = tmp_path / "rentals.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE properties (id INTEGER PRIMARY KEY, fingerprint TEXT, price_tl REAL)")
    conn.execute("CREATE TABLE notifications (id INTEGER PRIMARY KEY, channel TEXT)")
    conn.commit()
    conn.close()
    db = Database(path)
    assert db.upsert(listing(), NOW)[0] == NEW


def test_statistics(db):
    db.upsert(listing("1", 20000), NOW)
    db.upsert(listing("2", 30000), NOW)
    db.set_status(2, REMOVED, "gone", NOW)
    stats = db.statistics()
    assert stats["active"] == 1 and stats["removed"] == 1 and stats["lowest_cost"] == 20000
    assert db.active_listings()[0].source_id == "1"
    assert db.get_row("Emlakjet", "1")["status"] == ACTIVE
