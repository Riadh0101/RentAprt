"""Runtime configuration, loaded from environment variables and the project's .env file."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Istanbul Aydın University — Florya campus, Beşyol Mah. (approximate)
DEFAULT_CAMPUS = (40.9936, 28.7972)

# Metrobüs stations closest to the campus (approximate coordinates)
METROBUS_STATIONS: Dict[str, Tuple[float, float]] = {
    "Sefaköy": (41.0005, 28.8030),
    "Beşyol": (40.9928, 28.7958),
    "Florya": (40.9880, 28.7885),
    "Cennet Mahallesi": (40.9895, 28.7812),
    "Küçükçekmece": (40.9902, 28.7715),
}

# Emlakjet neighbourhood feeds (slug, label), ordered by proximity to the campus
EMLAKJET_FEEDS: List[Tuple[str, str]] = [
    ("istanbul-kucukcekmece-besyol-mahallesi", "Beşyol"),
    ("istanbul-kucukcekmece-kartaltepe-mahallesi", "Sefaköy / Kartaltepe"),
    ("istanbul-bakirkoy-senlikkoy-mahallesi", "Florya / Şenlikköy"),
    ("istanbul-kucukcekmece-cennet-mahallesi", "Cennet"),
    ("istanbul-kucukcekmece-inonu-mahallesi", "Sefaköy / İnönü"),
    ("istanbul-kucukcekmece", "Küçükçekmece"),
]


def _first(env: Mapping[str, str], *names: str, default: str = "") -> str:
    """Return the first non-empty variable among `names` (later names are legacy aliases)."""
    for name in names:
        value = env.get(name)
        if value not in (None, ""):
            return value.strip()
    return default


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    db_path: Path
    cycle_interval_minutes: int = 20
    log_level: str = "INFO"

    campus: Tuple[float, float] = DEFAULT_CAMPUS
    max_budget_tl: float = 36000.0
    exceptional_budget_limit_tl: float = 42000.0
    allowed_rooms: Tuple[str, ...] = ("1+0", "1+1", "2+1")

    score_instant_alert: int = 75
    score_multi_channel_alert: int = 85
    score_daily_digest: int = 65
    max_alerts_per_cycle: int = 10
    daily_digest_hour: int = 20

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    alert_recipient_email: str = ""
    email_enabled: bool = False

    request_timeout_seconds: float = 20.0
    request_delay_seconds: float = 1.0
    reverify_hours: float = 6.0
    max_reverify_per_cycle: int = 10
    watchlist_path: Optional[Path] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    feeds: List[Tuple[str, str]] = field(default_factory=lambda: list(EMLAKJET_FEEDS))

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def feed_urls(self) -> List[Tuple[str, str]]:
        """(label, url) for every feed, with the portal-side price cap applied."""
        cap = int(self.exceptional_budget_limit_tl)
        return [
            (label, f"https://www.emlakjet.com/kiralik-daire/{slug}/?fiyat=0-{cap}")
            for slug, label in self.feeds
        ]


def load_settings(env: Optional[Mapping[str, str]] = None, base_dir: Path = BASE_DIR) -> Settings:
    """Build Settings from `env` (defaults to os.environ after loading .env)."""
    if env is None:
        load_dotenv(base_dir / ".env")
        env = os.environ

    smtp_username = _first(env, "SMTP_USERNAME")
    smtp_password = _first(env, "SMTP_PASSWORD")
    recipient = _first(env, "ALERT_RECIPIENT_EMAIL", "EMAIL_TO")
    email_flag = _first(env, "EMAIL_ENABLED")
    email_enabled = (
        _bool(email_flag) if email_flag else bool(smtp_username and smtp_password and recipient)
    )

    rooms = _first(env, "ALLOWED_ROOMS", default="1+0,1+1,2+1")
    watchlist = _first(env, "WATCHLIST_PATH", default="watchlist.txt")

    return Settings(
        db_path=base_dir / _first(env, "DATABASE_PATH", default="data/rentals.db"),
        cycle_interval_minutes=int(_first(env, "CYCLE_INTERVAL_MINUTES", default="20")),
        log_level=_first(env, "LOG_LEVEL", default="INFO"),
        campus=(
            float(_first(env, "TARGET_CAMPUS_LAT", default=str(DEFAULT_CAMPUS[0]))),
            float(_first(env, "TARGET_CAMPUS_LON", default=str(DEFAULT_CAMPUS[1]))),
        ),
        max_budget_tl=float(_first(env, "TARGET_MAX_BUDGET_TL", "MAX_BUDGET_TL", default="36000")),
        exceptional_budget_limit_tl=float(_first(env, "EXCEPTIONAL_BUDGET_LIMIT_TL", default="42000")),
        allowed_rooms=tuple(r.strip() for r in rooms.split(",") if r.strip()),
        score_instant_alert=int(_first(env, "SCORE_INSTANT_ALERT", default="75")),
        score_multi_channel_alert=int(_first(env, "SCORE_MULTI_CHANNEL_ALERT", default="85")),
        score_daily_digest=int(_first(env, "SCORE_DAILY_DIGEST", default="65")),
        max_alerts_per_cycle=int(_first(env, "MAX_ALERTS_PER_CYCLE", default="10")),
        daily_digest_hour=int(_first(env, "DAILY_DIGEST_HOUR", default="20")),
        telegram_bot_token=_first(env, "TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_first(env, "TELEGRAM_CHAT_ID"),
        smtp_server=_first(env, "SMTP_SERVER", "SMTP_HOST", default="smtp.gmail.com"),
        smtp_port=int(_first(env, "SMTP_PORT", default="587")),
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        email_from=_first(env, "EMAIL_FROM", default=smtp_username),
        alert_recipient_email=recipient,
        email_enabled=email_enabled,
        request_timeout_seconds=float(_first(env, "REQUEST_TIMEOUT_SECONDS", default="20")),
        request_delay_seconds=float(_first(env, "REQUEST_DELAY_SECONDS", default="1.0")),
        reverify_hours=float(_first(env, "REVERIFY_HOURS", default="6")),
        max_reverify_per_cycle=int(_first(env, "MAX_REVERIFY_PER_CYCLE", default="10")),
        watchlist_path=base_dir / watchlist,
    )
