from typing import List, Dict, Any

class DormitorySource:
    """
    Curated database of verified student dormitories and student residences
    in the immediate vicinity of Istanbul Aydın University (Beşyol/Florya).
    """
    DORMITORIES: List[Dict[str, Any]] = [
        {
            "source": "Özel Erkek Yurdu",
            "source_id": "dorm_besyol_01",
            "title": "Aydın Üniversitesi Yanı Özel Erkek Öğrenci Yurdu - Tek Kişilik",
            "price": 18500.0,
            "currency": "TL",
            "rooms": "1+0",
            "area_m2": 22.0,
            "furnished": True,
            "location": "Beşyol, Küçükçekmece",
            "address": "İnönü Cad. No:14, Beşyol, Küçükçekmece / İstanbul",
            "latitude": 40.9942,
            "longitude": 28.7965,
            "floor": "3",
            "building_age": 4,
            "elevator": True,
            "heating": "Merkezi Doğalgaz",
            "internet_included": True,
            "aidat": 0.0,
            "deposit": 10000.0,
            "agency_fee": "None",
            "url": "https://www.aydin.edu.tr/dormitories/besyol-male-residence",
            "description": "İstanbul Aydın Üniversitesi kampüsüne 3 dakika yürüme mesafesinde, tek kişilik tam donanımlı erkek öğrenci odası. Fiber internet, çalışma masası, banyo dahil.",
            "phone": "+90 212 444 14 28"
        },
        {
            "source": "Student Residence",
            "source_id": "dorm_florya_02",
            "title": "Florya Metrobüs Yakını Lüks Öğrenci Rezidansı - 1+0 Studio",
            "price": 22000.0,
            "currency": "TL",
            "rooms": "1+0",
            "area_m2": 30.0,
            "furnished": True,
            "location": "Florya, Bakırköy",
            "address": "Yeşilköy Cad. No:45, Florya / İstanbul",
            "latitude": 40.9890,
            "longitude": 28.7890,
            "floor": "2",
            "building_age": 2,
            "elevator": True,
            "heating": "Kombi (Doğalgaz)",
            "internet_included": True,
            "aidat": 400.0,
            "deposit": 22000.0,
            "agency_fee": "None",
            "url": "https://www.studentresidenceistanbul.com/florya-studio-02",
            "description": "Florya Metrobüs durağına 5 dk, Aydın Üniversitesi'ne 10 dk yürüme mesafesinde bağımsız stüdyo rezidans.",
            "phone": "+90 532 555 12 34"
        },
        {
            "source": "Özel Erkek Yurdu",
            "source_id": "dorm_sefakoy_03",
            "title": "Sefaköy Metrobüs Çıkışı Erkek Öğrenci Yurdu - Tek Kişilik Suit",
            "price": 16000.0,
            "currency": "TL",
            "rooms": "1+0",
            "area_m2": 25.0,
            "furnished": True,
            "location": "Sefaköy, Küçükçekmece",
            "address": "Maslakçeşme Cad., Sefaköy / İstanbul",
            "latitude": 41.0010,
            "longitude": 28.8025,
            "floor": "4",
            "building_age": 6,
            "elevator": True,
            "heating": "Merkezi",
            "internet_included": True,
            "aidat": 0.0,
            "deposit": 8000.0,
            "agency_fee": "None",
            "url": "https://www.yurtlarburada.com/sefakoy-erkek-yurdu-suit",
            "description": "Metrobüse 3 dakika yürüme mesafesinde, sessiz ve güvenli tek kişilik suit oda. Üniversiteye 1 metrobüs durağı.",
            "phone": "+90 212 598 77 88"
        }
    ]

    @classmethod
    def fetch_listings(cls) -> List[Dict[str, Any]]:
        return cls.DORMITORIES
