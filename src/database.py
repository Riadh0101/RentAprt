"""SQLite persistence: listings, price history, notifications and cycle runs."""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .models import CycleReport, Listing

SCHEMA_VERSION = 1

ACTIVE, REMOVED, REJECTED = "ACTIVE", "REMOVED", "REJECTED"
NEW, PRICE_DROP, PRICE_INCREASE, UNCHANGED, REACTIVATED = (
    "NEW", "PRICE_DROP", "PRICE_INCREASE", "UNCHANGED", "REACTIVATED",
)

# Tables use new names so an old rentals.db from earlier versions never conflicts
_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    effective_cost REAL NOT NULL,
    rooms TEXT,
    area_m2 REAL,
    furnished INTEGER,
    elevator INTEGER,
    balcony INTEGER,
    heating TEXT,
    aidat REAL,
    deposit REAL,
    building_age INTEGER,
    bills_included INTEGER DEFAULT 0,
    floor TEXT,
    neighborhood TEXT,
    district TEXT,
    description TEXT,
    photos TEXT,
    listing_date TEXT,
    updated_date TEXT,
    univ_walk_min INTEGER,
    metrobus_station TEXT,
    metrobus_walk_min INTEGER,
    score INTEGER DEFAULT 0,
    score_breakdown TEXT,
    classification TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    status_reason TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    last_verified TEXT NOT NULL,
    last_price_change TEXT,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS listing_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    old_price REAL NOT NULL,
    new_price REAL NOT NULL,
    change_pct REAL NOT NULL,
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER REFERENCES listings(id),
    alert_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    price REAL,
    status TEXT NOT NULL,
    error TEXT,
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cycle_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    report TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_listings_status_score ON listings(status, score);
CREATE INDEX IF NOT EXISTS idx_alert_log_listing ON alert_log(listing_id, alert_type, channel);
"""

_JSON_FIELDS = {"photos", "score_breakdown"}
_BOOL_FIELDS = {"elevator", "balcony", "bills_included"}
_LISTING_FIELDS = [f.name for f in fields(Listing) if f.name != "id"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- listings -------------------------------------------------------

    @staticmethod
    def _to_row(listing: Listing) -> Dict[str, Any]:
        row = {}
        for name in _LISTING_FIELDS:
            value = getattr(listing, name)
            if name in _JSON_FIELDS:
                value = json.dumps(value, ensure_ascii=False)
            elif name in _BOOL_FIELDS and value is not None:
                value = int(value)
            row[name] = value
        return row

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Listing:
        kwargs = {}
        for name in _LISTING_FIELDS:
            value = row[name]
            if name in _JSON_FIELDS:
                value = json.loads(value) if value else ({} if name == "score_breakdown" else [])
            elif name in _BOOL_FIELDS and value is not None:
                value = bool(value)
            kwargs[name] = value
        return Listing(id=row["id"], **kwargs)

    def get_row(self, source: str, source_id: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM listings WHERE source = ? AND source_id = ?", (source, source_id)
            ).fetchone()

    def get_listing(self, listing_id: int) -> Optional[Listing]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return self._from_row(row) if row else None

    def upsert(self, listing: Listing, now: Optional[datetime] = None) -> Tuple[str, Optional[float]]:
        """Insert or refresh a verified listing. Returns (change, previous_price)."""
        now_s = _iso(now or utcnow())
        data = self._to_row(listing)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, price, status FROM listings WHERE source = ? AND source_id = ?",
                (listing.source, listing.source_id),
            ).fetchone()
            if row is None:
                data.update(status=ACTIVE, status_reason=None, first_seen=now_s,
                            last_seen=now_s, last_verified=now_s)
                cols = ", ".join(data)
                cur = conn.execute(
                    f"INSERT INTO listings ({cols}) VALUES ({', '.join('?' * len(data))})",
                    list(data.values()),
                )
                listing.id = cur.lastrowid
                return NEW, None

            listing.id = row["id"]
            old_price = row["price"]
            if listing.price < old_price:
                change = PRICE_DROP
            elif listing.price > old_price:
                change = PRICE_INCREASE
            elif row["status"] != ACTIVE:
                change = REACTIVATED
            else:
                change = UNCHANGED
            if change in (PRICE_DROP, PRICE_INCREASE):
                pct = round((listing.price - old_price) / old_price * 100, 2)
                conn.execute(
                    "INSERT INTO listing_price_history (listing_id, old_price, new_price, change_pct, changed_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (listing.id, old_price, listing.price, pct, now_s),
                )
                data["last_price_change"] = now_s
            data.update(status=ACTIVE, status_reason=None, last_seen=now_s, last_verified=now_s)
            assignments = ", ".join(f"{k} = ?" for k in data)
            conn.execute(f"UPDATE listings SET {assignments} WHERE id = ?", [*data.values(), listing.id])
            return change, old_price

    def touch_seen(self, listing_id: int, now: Optional[datetime] = None):
        with self.connect() as conn:
            conn.execute("UPDATE listings SET last_seen = ? WHERE id = ?", (_iso(now or utcnow()), listing_id))

    def set_status(self, listing_id: int, status: str, reason: str, now: Optional[datetime] = None):
        now_s = _iso(now or utcnow())
        with self.connect() as conn:
            conn.execute(
                "UPDATE listings SET status = ?, status_reason = ?, last_verified = ? WHERE id = ?",
                (status, reason, now_s, listing_id),
            )

    def stale_active(self, seen_ids: set, older_than_hours: float, limit: int,
                     now: Optional[datetime] = None) -> List[sqlite3.Row]:
        """Active listings not seen this cycle whose last verification is older than the cutoff."""
        cutoff = _iso((now or utcnow()) - timedelta(hours=older_than_hours))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM listings WHERE status = ? AND last_verified < ? ORDER BY last_verified",
                (ACTIVE, cutoff),
            ).fetchall()
        return [r for r in rows if r["id"] not in seen_ids][:limit]

    def active_listings(self, min_score: int = 0, limit: Optional[int] = None) -> List[Listing]:
        sql = "SELECT * FROM listings WHERE status = ? AND score >= ? ORDER BY score DESC, effective_cost ASC"
        params: List[Any] = [ACTIVE, min_score]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as conn:
            return [self._from_row(r) for r in conn.execute(sql, params).fetchall()]

    def price_drop(self, listing_id: int) -> Optional[sqlite3.Row]:
        """Most recent price change of a listing, if it was a reduction."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM listing_price_history WHERE listing_id = ? ORDER BY id DESC LIMIT 1",
                (listing_id,),
            ).fetchone()
        return row if row and row["new_price"] < row["old_price"] else None

    # ---- alerts ---------------------------------------------------------

    def was_alerted(self, listing_id: int, alert_type: str, channel: str,
                    price: Optional[float] = None) -> bool:
        """True if this alert was already delivered (for price drops: at this price)."""
        sql = "SELECT 1 FROM alert_log WHERE listing_id = ? AND alert_type = ? AND channel = ? AND status = 'SENT'"
        params: List[Any] = [listing_id, alert_type, channel]
        if price is not None:
            sql += " AND price = ?"
            params.append(price)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone() is not None

    def log_alert(self, listing_id: Optional[int], alert_type: str, channel: str,
                  ok: bool, price: Optional[float] = None, error: str = ""):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO alert_log (listing_id, alert_type, channel, price, status, error, sent_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (listing_id, alert_type, channel, price, "SENT" if ok else "FAILED", error, _iso(utcnow())),
            )

    def last_digest_date(self) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT MAX(sent_at) FROM alert_log WHERE alert_type = 'DAILY_DIGEST' AND status = 'SENT'"
            ).fetchone()
        return row[0][:10] if row and row[0] else None

    # ---- runs & stats ---------------------------------------------------

    def record_run(self, report: CycleReport):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO cycle_runs (started_at, finished_at, report) VALUES (?, ?, ?)",
                (report.started_at, report.finished_at, json.dumps(report.__dict__)),
            )

    def statistics(self, since_hours: float = 24) -> Dict[str, Any]:
        since = _iso(utcnow() - timedelta(hours=since_hours))
        with self.connect() as conn:
            one = lambda sql, *p: conn.execute(sql, p).fetchone()[0]
            return {
                "total_tracked": one("SELECT COUNT(*) FROM listings"),
                "active": one("SELECT COUNT(*) FROM listings WHERE status = ?", ACTIVE),
                "removed": one("SELECT COUNT(*) FROM listings WHERE status = ?", REMOVED),
                "new_recent": one("SELECT COUNT(*) FROM listings WHERE first_seen >= ?", since),
                "price_drops_recent": one(
                    "SELECT COUNT(*) FROM listing_price_history WHERE new_price < old_price AND changed_at >= ?", since),
                "top_score": one("SELECT COALESCE(MAX(score), 0) FROM listings WHERE status = ?", ACTIVE),
                "average_cost": round(one(
                    "SELECT COALESCE(AVG(effective_cost), 0) FROM listings WHERE status = ?", ACTIVE)),
                "lowest_cost": round(one(
                    "SELECT COALESCE(MIN(effective_cost), 0) FROM listings WHERE status = ?", ACTIVE)),
                "runs_recent": one("SELECT COUNT(*) FROM cycle_runs WHERE started_at >= ?", since),
            }
