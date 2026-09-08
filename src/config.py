import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / os.getenv("DATABASE_PATH", "data/rentals.db")
    
    # Execution
    CYCLE_INTERVAL_MINUTES: int = int(os.getenv("CYCLE_INTERVAL_MINUTES", "40"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Target Criteria
    TARGET_UNIVERSITY: str = "Istanbul Aydın University (IAU)"
    TARGET_CAMPUS_LAT: float = float(os.getenv("TARGET_CAMPUS_LAT", "40.9936"))
    TARGET_CAMPUS_LON: float = float(os.getenv("TARGET_CAMPUS_LON", "28.7972"))
    
    MAX_BUDGET_TL: float = float(os.getenv("MAX_BUDGET_TL", "36000"))
    MAX_DISTANCE_KM_TO_UNIVERSITY: float = float(os.getenv("MAX_DISTANCE_KM_TO_UNIVERSITY", "30.0"))
    REQUIRE_ISTANBUL_ONLY: bool = True
    
    PRIORITY_LOCATIONS: List[str] = [
        "Beşyol", "Florya", "Sefaköy", "Cennet", "Küçükçekmece", "Gültepe"
    ]
    
    METROBUS_STATIONS = {
        "Beşyol": (40.9928, 28.7958),
        "Florya": (40.9880, 28.7885),
        "Sefaköy": (41.0005, 28.8030),
        "Cennet Mahallesi": (40.9895, 28.7812),
        "Küçükçekmece": (40.9902, 28.7715)
    }
    
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
    
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

config = Config()

# Module-level aliases for direct imports
DATABASE_PATH = config.DB_PATH
TARGET_MAX_BUDGET_TL = config.MAX_BUDGET_TL
EXCEPTIONAL_BUDGET_LIMIT_TL = 42000.0
AYDIN_UNIV_LAT = config.TARGET_CAMPUS_LAT
AYDIN_UNIV_LON = config.TARGET_CAMPUS_LON
AYDIN_UNIV_NAME = config.TARGET_UNIVERSITY
BESYOL_METROBUS_LAT = 40.9875
BESYOL_METROBUS_LON = 28.8020
BESYOL_METROBUS_NAME = "Beşyol Metrobüs Durağı"
PRIORITY_NEIGHBORHOODS = config.PRIORITY_LOCATIONS
SCORE_INSTANT_ALERT = int(os.getenv("SCORE_INSTANT_ALERT", "75"))
SCORE_MULTI_CHANNEL_ALERT = int(os.getenv("SCORE_MULTI_CHANNEL_ALERT", "85"))
SCORE_DAILY_DIGEST = 65
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
CYCLE_INTERVAL_MINUTES = config.CYCLE_INTERVAL_MINUTES
SMTP_SERVER = config.SMTP_HOST
SMTP_PORT = config.SMTP_PORT
SMTP_USERNAME = config.SMTP_USERNAME
SMTP_PASSWORD = config.SMTP_PASSWORD
ALERT_RECIPIENT_EMAIL = config.EMAIL_TO
