"""Deterministic Arabic matching keys; retain original text separately for display."""

import unicodedata

NORMALIZER_VERSION = "ar-v2"
_VARIANTS = str.maketrans("أإآٱىة", "اااايه")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_MARK_RANGES = (
    (0x0610, 0x061A),
    (0x064B, 0x065F),
    (0x0670, 0x0670),
    (0x06D6, 0x06ED),
    (0x0898, 0x089F),
    (0x08CA, 0x08FF),
)


def normalize_arabic(text: str) -> str:
    """Strip Arabic marks/tatweel, fold variants, and collapse Unicode whitespace.

    Expand Arabic presentation forms with NFKC, compose with NFC, remove format
    characters, and fold Arabic-Indic digits to ASCII. Other scripts retain their
    compatibility forms; hamza letters, punctuation and non-Arabic accents survive.
    This lossy key must never replace source text or itself authorize a quotation.
    """
    if not isinstance(text, str):
        raise TypeError("normalize_arabic expects a string")
    expanded = "".join(
        unicodedata.normalize("NFKC", char)
        if 0xFB50 <= ord(char) <= 0xFDFF or 0xFE70 <= ord(char) <= 0xFEFF
        else char
        for char in text
    )
    composed = unicodedata.normalize("NFC", expanded)
    stripped = "".join(
        char
        for char in composed
        if char != "ـ"
        and unicodedata.category(char) != "Cf"
        and not (
            unicodedata.category(char).startswith("M")
            and any(start <= ord(char) <= end for start, end in _MARK_RANGES)
        )
    )
    # Removing intervening Arabic marks can expose a new Unicode composition.
    canonical = unicodedata.normalize("NFC", stripped)
    return " ".join(canonical.translate(_VARIANTS).translate(_DIGITS).split())
