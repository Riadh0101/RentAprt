import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from src.config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Properties table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL,
        source_id TEXT,
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        price_tl REAL NOT NULL,
        effective_monthly_cost REAL NOT NULL,
        currency TEXT DEFAULT 'TL',
        property_type TEXT,
        rooms TEXT,
        area_m2 REAL,
        furnished INTEGER DEFAULT 0,
        location TEXT,
        address TEXT,
        latitude REAL,
        longitude REAL,
        univ_dist_min REAL,
        metrobus_dist_min REAL,
        score INTEGER DEFAULT 0,
        score_breakdown TEXT,
        classification TEXT,
        contact_info TEXT,
        photos TEXT,
        status TEXT DEFAULT 'ACTIVE',
        listing_date TEXT,
        first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migration: ensure listing_date column exists if table was already created
    try:
        cursor.execute("ALTER TABLE properties ADD COLUMN listing_date TEXT;")
    except sqlite3.OperationalError:
        pass

    # Price history table for tracking price reductions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        old_price REAL NOT NULL,
        new_price REAL NOT NULL,
        change_pct REAL NOT NULL,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties(id)
    );
    """)

    # Notifications history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        channel TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'SENT',
        FOREIGN KEY(property_id) REFERENCES properties(id)
    );
    """)

    conn.commit()
    conn.close()

def generate_fingerprint(location: str, rooms: str, area_m2: Optional[float], title: str, address: Optional[str] = None) -> str:
    """Generate normalized fingerprint for deduplication across different portals."""
    norm_loc = (location or "").strip().lower()
    norm_rooms = (rooms or "").strip().lower().replace(" ", "")
    norm_area = str(round(area_m2 or 0.0, -1)) # group by ~10m2 buckets to catch minor discrepancies
    norm_addr = (address or "").strip().lower()[:20]
    
    raw = f"{norm_loc}|{norm_rooms}|{norm_area}|{norm_addr}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def upsert_property(prop: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Insert or update a property.
    Returns (status, existing_or_updated_data)
    status can be: 'NEW', 'PRICE_DROP', 'PRICE_INCREASE', or 'UNCHANGED'
    """
    conn = get_connection()
    cursor = conn.cursor()

    fingerprint = prop.get("fingerprint") or generate_fingerprint(
        prop.get("location", ""),
        prop.get("rooms", ""),
        prop.get("area_m2"),
        prop.get("title", ""),
        prop.get("address")
    )
    prop["fingerprint"] = fingerprint

    cursor.execute("SELECT * FROM properties WHERE fingerprint = ? OR url = ?", (fingerprint, prop["url"]))
    row = cursor.fetchone()

    now = datetime.now().isoformat()

    if not row:
        # Brand new property
        cursor.execute("""
        INSERT INTO properties (
            fingerprint, source, source_id, url, title, price_tl, effective_monthly_cost,
            currency, property_type, rooms, area_m2, furnished, location, address,
            latitude, longitude, univ_dist_min, metrobus_dist_min, score,
            score_breakdown, classification, contact_info, photos, listing_date, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fingerprint,
            prop.get("source", "Web"),
            prop.get("source_id", ""),
            prop["url"],
            prop.get("title", "No Title"),
            float(prop.get("price_tl", 0.0)),
            float(prop.get("effective_monthly_cost", prop.get("price_tl", 0.0))),
            prop.get("currency", "TL"),
            prop.get("property_type", "Apartment"),
            prop.get("rooms", "1+1"),
            float(prop.get("area_m2", 0.0)) if prop.get("area_m2") else None,
            int(prop.get("furnished", 0)),
            prop.get("location", ""),
            prop.get("address", ""),
            prop.get("latitude"),
            prop.get("longitude"),
            prop.get("univ_dist_min"),
            prop.get("metrobus_dist_min"),
            prop.get("score", 0),
            json.dumps(prop.get("score_breakdown", {})),
            prop.get("classification", "POTENTIAL"),
            prop.get("contact_info", ""),
            json.dumps(prop.get("photos", [])),
            prop.get("listing_date", ""),
            now,
            now
        ))
        prop["id"] = cursor.lastrowid
        conn.commit()
        conn.close()
        return "NEW", prop

    # Existing property - check for price changes
    existing = dict(row)
    prop_id = existing["id"]
    prop["id"] = prop_id
    old_price = existing["price_tl"]
    new_price = float(prop.get("price_tl", old_price))

    if new_price < old_price:
        # Price Drop!
        drop_pct = round(((old_price - new_price) / old_price) * 100, 2)
        cursor.execute("""
        INSERT INTO price_history (property_id, old_price, new_price, change_pct, changed_at)
        VALUES (?, ?, ?, ?, ?)
        """, (prop_id, old_price, new_price, drop_pct, now))

        cursor.execute("""
        UPDATE properties SET
            price_tl = ?,
            effective_monthly_cost = ?,
            score = ?,
            score_breakdown = ?,
            classification = ?,
            listing_date = COALESCE(?, listing_date),
            last_seen_at = ?
        WHERE id = ?
        """, (
            new_price,
            float(prop.get("effective_monthly_cost", new_price)),
            prop.get("score", existing["score"]),
            json.dumps(prop.get("score_breakdown", {})),
            prop.get("classification", existing["classification"]),
            prop.get("listing_date"),
            now,
            prop_id
        ))
        conn.commit()
        conn.close()
        prop["old_price"] = old_price
        prop["price_drop_pct"] = drop_pct
        return "PRICE_DROP", prop

    elif new_price > old_price:
        cursor.execute("UPDATE properties SET price_tl = ?, listing_date = COALESCE(?, listing_date), last_seen_at = ? WHERE id = ?", (new_price, prop.get("listing_date"), now, prop_id))
        conn.commit()
        conn.close()
        return "PRICE_INCREASE", prop
    else:
        cursor.execute("UPDATE properties SET listing_date = COALESCE(?, listing_date), last_seen_at = ? WHERE id = ?", (prop.get("listing_date"), now, prop_id))
        conn.commit()
        conn.close()
        return "UNCHANGED", prop

def has_been_notified(property_id: int, channel: str = "telegram") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM notifications WHERE property_id = ? AND channel = ?", (property_id, channel))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def record_notification(property_id: int, channel: str, alert_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO notifications (property_id, channel, alert_type, sent_at, status)
    VALUES (?, ?, ?, ?, 'SENT')
    """, (property_id, channel, alert_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()
