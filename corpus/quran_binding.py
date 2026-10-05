"""Keep a Quran record's matching spelling and original display bytes together."""

import hashlib

from corpus.normalize import normalize_arabic

PAIR_FIELDS = {"aya_text_emlaey", "aya_text_unicode", "checksum_unicode_sha256"}


def validate_pair(record: dict) -> None:
    if not PAIR_FIELDS.intersection(record):
        return  # Older validated artifacts retain their original single text field.
    matching = record.get("aya_text_emlaey")
    display = record.get("aya_text_unicode")
    surah, ayah = record.get("sura_no"), record.get("aya_no")
    if (
        record.get("domain") != "quran"
        or record.get("source_id") != "kfc-mushaf"
        or not isinstance(matching, str)
        or not matching.strip()
        or not isinstance(display, str)
        or not display.strip()
        or matching != record.get("text_ar")
        or record.get("text_normalized") != normalize_arabic(matching)
        or type(surah) is not int
        or not 1 <= surah <= 114
        or type(ayah) is not int
        or ayah < 1
        or record.get("ref") != {"surah": surah, "ayah": ayah}
        or record.get("corpus_id") != f"quran:{surah}:{ayah}"
        or record.get("checksum_sha256") != hashlib.sha256(matching.encode("utf-8")).hexdigest()
        or record.get("checksum_unicode_sha256")
        != hashlib.sha256(display.encode("utf-8")).hexdigest()
    ):
        raise ValueError("Invalid Quran field binding")


def matching_text(record: dict) -> str:
    validate_pair(record)
    return record.get("aya_text_emlaey", record["text_ar"])


def display_text(record: dict) -> str:
    validate_pair(record)
    return record.get("aya_text_unicode", record["text_ar"])
