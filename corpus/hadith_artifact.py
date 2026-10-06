"""Owner-collected HadeethEnc artifact: pinned bytes, verbatim fields, no fetches."""

import hashlib
import re
from pathlib import Path

from api.hadeethenc import SOURCE_NAME_AR
from corpus.normalize import normalize_arabic
from corpus.private_artifact import _read_bounded
from corpus.validate import CorpusValidationError, _decode, parse_records

SHA256 = "1e0a79c49b0287a6ea33826dde1996bd465c81490f59c0050444b6241f9b2ae6"
VERSION = "2026-10-06"
COUNT = 3574
BYTES = 10302934
MAX_BYTES = 16 * 1024 * 1024


def authentic_grade(value: object) -> bool:
    """Only the publisher's unambiguous sahih/hasan labels qualify for D7."""
    return isinstance(value, str) and value in {"صحيح", "حسن", "[صحيح]", "[حسن]"}


def _record(row: dict) -> dict | None:
    item_id = row.get("id")
    if not isinstance(item_id, str) or not re.fullmatch(r"[1-9][0-9]{0,7}", item_id):
        raise CorpusValidationError("Invalid hadith id")
    url = f"https://hadeethenc.com/ar/browse/hadith/{item_id}"
    if row.get("url") != url:
        raise CorpusValidationError("Invalid hadith source URL")
    for field in ("title", "hadeeth", "attribution", "grade", "reference", "explanation"):
        if not isinstance(row.get(field), str):
            raise CorpusValidationError("Invalid hadith text field")
    if not row["hadeeth"].strip() or not normalize_arabic(row["hadeeth"]):
        raise CorpusValidationError("Empty hadith text")
    # Incomplete/oversize rows cannot authorize display. Never fill missing metadata.
    if any(not row[k].strip() for k in ("attribution", "grade", "reference")):
        return None
    if len(row["hadeeth"]) > 12000 or not authentic_grade(row["grade"]):
        return None
    return {
        "corpus_id": "hadeethenc:" + item_id,
        "domain": "hadith",
        "source_id": "hadeethenc",
        "source_name_ar": "HadeethEnc.com",
        "source_url": url,
        "text_ar": row["hadeeth"],
        "text_normalized": normalize_arabic(row["hadeeth"]),
        "ref": {
            "collection": SOURCE_NAME_AR,
            "number": item_id,
            "attribution": row["attribution"],
            "reference": row["reference"],
        },
        "grading": {
            "grading_source_id": "hadeethenc",
            "grade_ar": row["grade"],
            "grader_ar": SOURCE_NAME_AR,
            "grading_source_url": url,
        },
    }


def load_hadith_artifact(path: Path) -> list[dict]:
    """Read once and bind the exact bytes to the owner's approved hash and manifest."""
    try:
        data = _read_bounded(path, MAX_BYTES)
        if hashlib.sha256(data).hexdigest() != SHA256 or len(data) != BYTES:
            raise CorpusValidationError("Hadith checksum mismatch")
        manifest = _decode(_read_bounded(path.with_name("manifest.json"), 65536).decode("utf-8"))
        expected = {
            "sha256": SHA256,
            "count": COUNT,
            "bytes": BYTES,
            "categories": 493,
            "failures": 0,
            "complete": True,
            "status": "complete",
            "source_host": "hadeethenc.com",
            "file": "hadeethenc.jsonl",
        }
        if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in expected.items()):
            raise CorpusValidationError("Invalid hadith manifest")
        rows = parse_records(data)
        if len(rows) != COUNT:
            raise CorpusValidationError("Invalid hadith count")
        records, seen = [], set()
        for row in rows:
            record = _record(row)
            if row["id"] in seen:
                raise CorpusValidationError("Duplicate hadith id")
            seen.add(row["id"])
            if record is not None:
                records.append(record)
        return records
    except CorpusValidationError:
        raise
    except (ValueError, UnicodeError, TypeError, KeyError, RecursionError):
        raise CorpusValidationError("Invalid hadith artifact") from None
