import unittest
import os
from pathlib import Path
from src.filter_scorer import cheap_filter, score_property, estimate_proximity
from src.database import init_db, upsert_property, generate_fingerprint, get_connection
from src.notifier import format_telegram_alert

class TestHermesEngine(unittest.TestCase):

    def setUp(self):
        init_db()
        conn = get_connection()
        conn.execute("DELETE FROM properties WHERE url LIKE '%example.com%'")
        conn.commit()
        conn.close()

    def test_cheap_filtering(self):
        # Good candidate
        valid_prop = {"price_tl": 22000, "rooms": "1+1", "title": "Beşyol eşyalı"}
        passed, _ = cheap_filter(valid_prop)
        self.assertTrue(passed)

        # Over budget
        expensive_prop = {"price_tl": 55000, "rooms": "1+1"}
        passed, reason = cheap_filter(expensive_prop)
        self.assertFalse(passed)

        # 3+1 apartment
        big_prop = {"price_tl": 25000, "rooms": "3+1"}
        passed, reason = cheap_filter(big_prop)
        self.assertFalse(passed)

    def test_scoring_matrix(self):
        # Exceptional apartment right next to Aydin University in Beşyol, cheap, furnished
        prime_prop = {
            "title": "Aydın Üniversitesi yanı 1+1",
            "location": "Beşyol, Küçükçekmece",
            "latitude": 40.9881,
            "longitude": 28.8000,
            "price_tl": 19000,
            "rooms": "1+1",
            "furnished": 1,
            "area_m2": 50,
            "contact_info": "+90 532 000 00 00",
            "photos": ["p1.jpg"],
            "url": "https://example.com/prime"
        }
        score, breakdown, classification = score_property(prime_prop)
        self.assertGreaterEqual(score, 85)
        self.assertIn(classification, ["EXCELLENT", "EXCEPTIONAL"])
        self.assertIn(breakdown["location_transit"], [37, 40]) # <= 10-20 min walk
        self.assertEqual(breakdown["price_budget"], 25)     # <= 20,000 TL
        self.assertEqual(breakdown["furnishing"], 15)       # fully furnished

    def test_database_deduplication_and_price_drop(self):
        prop1 = {
            "source": "TestPortal",
            "url": "https://example.com/apt-drop-test",
            "title": "Sefaköy 1+1 Test",
            "location": "Sefaköy",
            "rooms": "1+1",
            "area_m2": 50,
            "price_tl": 26000,
            "furnished": 1
        }
        status1, saved1 = upsert_property(prop1)
        self.assertEqual(status1, "NEW")

        # Re-scrape with price drop: 26000 -> 22000 (-15.38%)
        prop1_dropped = prop1.copy()
        prop1_dropped["price_tl"] = 22000
        status2, saved2 = upsert_property(prop1_dropped)
        self.assertEqual(status2, "PRICE_DROP")
        self.assertAlmostEqual(saved2["price_drop_pct"], 15.38, delta=0.1)

    def test_telegram_message_formatting(self):
        prop = {
            "title": "Beşyol Kiralık 1+1",
            "location": "Beşyol",
            "rooms": "1+1",
            "price_tl": 21000,
            "furnished": 1,
            "area_m2": 45,
            "score": 88,
            "classification": "EXCELLENT",
            "univ_dist_min": 4,
            "metrobus_dist_min": 3,
            "url": "https://example.com/test",
            "contact_info": "05321112233"
        }
        msg = format_telegram_alert(prop, alert_type="NEW_MATCH")
        self.assertIn("AG Alert", msg)
        self.assertIn("88/100", msg)
        self.assertIn("جامعة أيدن", msg)

if __name__ == "__main__":
    unittest.main()
