"""Turkish-aware text helpers used for keyword matching and number parsing."""
import re
from typing import Iterable, Optional

_TR_ASCII = str.maketrans({
    "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
    "â": "a", "î": "i", "û": "u", "̇": "",
})


def fold(text: Optional[str]) -> str:
    """Lowercase Turkish text correctly and strip diacritics for keyword matching.

    Plain str.lower() turns "İ" into "i̇" (i + combining dot), so "SADECE AİLE"
    would never match "sadece aile".
    """
    if not text:
        return ""
    text = text.replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", text.translate(_TR_ASCII)).strip()


def contains_any(folded_text: str, phrases: Iterable[str]) -> bool:
    """True if any phrase (folded first) occurs in already-folded text."""
    return any(fold(p) in folded_text for p in phrases)


def parse_number(text) -> Optional[float]:
    """Parse '35.000 TL', '1,200 TL', '75 m²', 30000 into a float. Returns None if absent."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    match = re.search(r"\d[\d.,]*", str(text))
    if not match:
        return None
    digits = re.sub(r"[.,](?=\d{3}\b)", "", match.group())  # thousands separators
    digits = digits.replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return None


def normalize_rooms(text: Optional[str]) -> Optional[str]:
    """Extract a room layout like '1+1' from free text; studios map to '1+0'."""
    folded = fold(text)
    if not folded:
        return None
    match = re.search(r"(?<!\d)(\d)\s*\+\s*(\d)(?!\d)", folded)  # also matches "2+1esyali"
    if match:
        return f"{match.group(1)}+{match.group(2)}"
    if "studyo" in folded or "studio" in folded:
        return "1+0"
    return None
