import re
import unicodedata

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
ARABIC_COMPARISON_MAP = str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ى":"ي", "ة":"ه"})


def normalize_arabic_digits(value: str) -> str:
    return value.translate(ARABIC_DIGITS)


def normalize_text(value: str, *, arabic: bool = False) -> str:
    result = unicodedata.normalize("NFKC", value or "")
    result = normalize_arabic_digits(result)
    result = re.sub(r"\s+", " ", result).strip()
    if arabic:
        result = result.translate(ARABIC_COMPARISON_MAP)
    return result


def normalize_identifier(value: str) -> str:
    # Identifiers stay strings. Leading zeroes and source spelling are preserved in raw_value.
    return normalize_text(value).replace(" ", "")


def normalize_candidate(value: str, rule: str) -> str:
    if rule in {"IDENTIFIER_EXACT", "PIN_EXACT", "QID_EXACT", "CR_EXACT"}:
        return normalize_identifier(value)
    if rule == "ARABIC_NAME_COMPARISON":
        return normalize_text(value, arabic=True)
    return normalize_text(value)
