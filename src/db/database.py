import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from .models import PropertyRecord, PriceHistoryRecord, SearchRunRecord, NotificationRecord

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Properties table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_id TEXT UNIQUE,
                source TEXT,
                source_property_id TEXT,
                url TEXT,
                title TEXT,
                property_type TEXT,
                rooms TEXT,
                price REAL,
                currency TEXT DEFAULT 'TL',
                effective_monthly_price REAL,
                area_m2 REAL,
                furnished INTEGER DEFAULT 1,
                location TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL,
                metrobus_station TEXT,
                metrobus_distance_min INTEGER,
                university_distance_min INTEGER,
                university_travel_mode TEXT,
                floor TEXT,
                building_age INTEGER,
                elevator INTEGER,
                heating TEXT,
                internet_included INTEGER,
                aidat REAL,
                deposit REAL,
                agency_fee TEXT,
                student_allowed INTEGER DEFAULT 1,
                foreigner_allowed INTEGER DEFAULT 1,
                landlord_name TEXT,
                phone_if_public TEXT,
                listing_date TEXT,
                first_seen TEXT,
                last_seen TEXT,
                last_price_change TEXT,
                status TEXT DEFAULT 'active',
                score INTEGER DEFAULT 0,
                verification_status TEXT DEFAULT 'LIKELY',
                description TEXT,
                source_urls TEXT
            )
            """)

            # Price History table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER,
                old_price REAL,
                new_price REAL,
                changed_at TEXT,
                FOREIGN KEY(property_id) REFERENCES properties(id)
            )
            """)

            # Search Runs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                finished_at TEXT,
                sources_checked INTEGER,
                listings_found INTEGER,
                new_listings INTEGER,
                price_changes INTEGER,
                errors INTEGER,
                log_summary TEXT
            )
            """)

            # Notifications table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER,
                notification_type TEXT,
                sent_at TEXT,
                channel TEXT,
                status TEXT,
                FOREIGN KEY(property_id) REFERENCES properties(id)
            )
            """)
            conn.commit()

    def find_existing_property(self, canonical_id: str, url: str, source_property_id: str) -> Optional[PropertyRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT * FROM properties 
            WHERE canonical_id = ? 
               OR (source_property_id = ? AND source_property_id != '') 
               OR url = ?
            LIMIT 1
            """
            cursor.execute(query, (canonical_id, source_property_id, url))
            row = cursor.fetchone()
            if row:
                return self._row_to_property(row)
        return None

    def upsert_property(self, prop: PropertyRecord) -> Tuple[int, str]:
        """
        Returns (property_id, action_taken)
        action_taken: 'NEW' | 'PRICE_REDUCED' | 'PRICE_INCREASED' | 'UPDATED' | 'NO_CHANGE'
        """
        existing = self.find_existing_property(
            prop.canonical_id or "", prop.url, prop.source_property_id
        )
        now_str = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if not existing:
                # Insert new property
                cursor.execute("""
                INSERT INTO properties (
                    canonical_id, source, source_property_id, url, title, property_type,
                    rooms, price, currency, effective_monthly_price, area_m2, furnished,
                    location, address, latitude, longitude, metrobus_station,
                    metrobus_distance_min, university_distance_min, university_travel_mode,
                    floor, building_age, elevator, heating, internet_included, aidat,
                    deposit, agency_fee, student_allowed, foreigner_allowed, landlord_name,
                    phone_if_public, listing_date, first_seen, last_seen, last_price_change,
                    status, score, verification_status, description, source_urls
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prop.canonical_id, prop.source, prop.source_property_id, prop.url, prop.title,
                    prop.property_type, prop.rooms, prop.price, prop.currency, prop.effective_monthly_price,
                    prop.area_m2, 1 if prop.furnished else 0, prop.location, prop.address, prop.latitude,
                    prop.longitude, prop.metrobus_station, prop.metrobus_distance_min,
                    prop.university_distance_min, prop.university_travel_mode, prop.floor, prop.building_age,
                    1 if prop.elevator else 0 if prop.elevator is not None else None, prop.heating,
                    1 if prop.internet_included else 0 if prop.internet_included is not None else None,
                    prop.aidat, prop.deposit, prop.agency_fee, 1 if prop.student_allowed else 0,
                    1 if prop.foreigner_allowed else 0, prop.landlord_name, prop.phone_if_public,
                    prop.listing_date, now_str, now_str, None, prop.status, prop.score,
                    prop.verification_status, prop.description, json.dumps(prop.source_urls)
                ))
                prop_id = cursor.lastrowid
                conn.commit()
                return prop_id, "NEW"
            else:
                prop_id = existing.id
                action = "NO_CHANGE"
                
                # Check price change
                old_price = existing.effective_monthly_price or existing.price
                new_price = prop.effective_monthly_price or prop.price
                
                last_price_change = existing.last_price_change
                if new_price < old_price and old_price > 0:
                    action = "PRICE_REDUCED"
                    last_price_change = now_str
                    cursor.execute("""
                    INSERT INTO price_history (property_id, old_price, new_price, changed_at)
                    VALUES (?, ?, ?, ?)
                    """, (prop_id, old_price, new_price, now_str))
                elif new_price > old_price and old_price > 0:
                    action = "PRICE_INCREASED"
                    last_price_change = now_str
                    cursor.execute("""
                    INSERT INTO price_history (property_id, old_price, new_price, changed_at)
                    VALUES (?, ?, ?, ?)
                    """, (prop_id, old_price, new_price, now_str))
                else:
                    action = "UPDATED"

                # Merge source URLs
                existing_urls = existing.source_urls or []
                for u in prop.source_urls:
                    if u not in existing_urls:
                        existing_urls.append(u)
                if prop.url not in existing_urls:
                    existing_urls.append(prop.url)

                cursor.execute("""
                UPDATE properties SET
                    title = ?, price = ?, effective_monthly_price = ?, score = ?,
                    last_seen = ?, last_price_change = ?, status = 'active',
                    source_urls = ?, verification_status = ?, description = ?
                WHERE id = ?
                """, (
                    prop.title or existing.title, prop.price, prop.effective_monthly_price,
                    prop.score, now_str, last_price_change, json.dumps(existing_urls),
                    prop.verification_status, prop.description or existing.description, prop_id
                ))
                conn.commit()
                return prop_id, action

    def get_top_properties(self, limit: int = 10, min_score: int = 65) -> List[PropertyRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM properties
            WHERE status = 'active' AND score >= ?
            ORDER BY score DESC, effective_monthly_price ASC
            LIMIT ?
            """, (min_score, limit))
            return [self._row_to_property(row) for row in cursor.fetchall()]

    def get_all_active(self) -> List[PropertyRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM properties WHERE status = 'active' ORDER BY score DESC")
            return [self._row_to_property(row) for row in cursor.fetchall()]

    def record_run(self, run: SearchRunRecord) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO search_runs (
                started_at, finished_at, sources_checked, listings_found,
                new_listings, price_changes, errors, log_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.started_at, run.finished_at, run.sources_checked,
                run.listings_found, run.new_listings, run.price_changes,
                run.errors, run.log_summary
            ))
            conn.commit()
            return cursor.lastrowid

    def record_notification(self, notif: NotificationRecord):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO notifications (property_id, notification_type, sent_at, channel, status)
            VALUES (?, ?, ?, ?, ?)
            """, (notif.property_id, notif.notification_type, notif.sent_at, notif.channel, notif.status))
            conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
            active = cursor.execute("SELECT COUNT(*) FROM properties WHERE status = 'active'").fetchone()[0]
            price_drops = cursor.execute("SELECT COUNT(*) FROM price_history WHERE new_price < old_price").fetchone()[0]
            top_score = cursor.execute("SELECT MAX(score) FROM properties WHERE status = 'active'").fetchone()[0] or 0
            avg_price = cursor.execute("SELECT AVG(effective_monthly_price) FROM properties WHERE status = 'active' AND effective_monthly_price > 0").fetchone()[0] or 0.0
            min_price = cursor.execute("SELECT MIN(effective_monthly_price) FROM properties WHERE status = 'active' AND effective_monthly_price > 0").fetchone()[0] or 0.0
            
            return {
                "total_tracked": total,
                "active_properties": active,
                "price_reductions_total": price_drops,
                "top_score": top_score,
                "average_price": round(avg_price, 2),
                "lowest_price": round(min_price, 2)
            }

    def _row_to_property(self, row: sqlite3.Row) -> PropertyRecord:
        source_urls = []
        if row["source_urls"]:
            try:
                source_urls = json.loads(row["source_urls"])
            except Exception:
                source_urls = [row["url"]]

        return PropertyRecord(
            id=row["id"],
            canonical_id=row["canonical_id"],
            source=row["source"],
            source_property_id=row["source_property_id"],
            url=row["url"],
            title=row["title"],
            property_type=row["property_type"],
            rooms=row["rooms"],
            price=row["price"],
            currency=row["currency"],
            effective_monthly_price=row["effective_monthly_price"],
            area_m2=row["area_m2"],
            furnished=bool(row["furnished"]),
            location=row["location"],
            address=row["address"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            metrobus_station=row["metrobus_station"],
            metrobus_distance_min=row["metrobus_distance_min"],
            university_distance_min=row["university_distance_min"],
            university_travel_mode=row["university_travel_mode"],
            floor=row["floor"],
            building_age=row["building_age"],
            elevator=bool(row["elevator"]) if row["elevator"] is not None else None,
            heating=row["heating"],
            internet_included=bool(row["internet_included"]) if row["internet_included"] is not None else None,
            aidat=row["aidat"],
            deposit=row["deposit"],
            agency_fee=row["agency_fee"],
            student_allowed=bool(row["student_allowed"]),
            foreigner_allowed=bool(row["foreigner_allowed"]),
            landlord_name=row["landlord_name"],
            phone_if_public=row["phone_if_public"],
            listing_date=row["listing_date"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            last_price_change=row["last_price_change"],
            status=row["status"],
            score=row["score"],
            verification_status=row["verification_status"],
            description=row["description"],
            source_urls=source_urls
        )
