"""Load owner-collected private short fields; no fetching, repairs or AI calls."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from corpus.validate import ROOT, CorpusValidationError, read_sources

AUTHORITY_EVENT = "d3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f"
_HEX = re.compile(r"[0-9a-f]{64}")
_CONFIG = {
    "bayyinat": ("bayyinat.jsonl", "bayenat.net", "short_answer"),
    "jamhara-glossary": ("glossary.jsonl", "islamic-content.com", "definition_short"),
}
_FIELDS = {
    "bayyinat": {"id", "url", "title", "similar_phrasings", "short_answer", "keywords", "category"},
    "jamhara-glossary": {"id", "url", "term_ar", "definition_short", "translations"},
}
_V2_FIELDS = {
    "bayyinat": {"id", "url", "title", "question_text", "summary", "keywords", "detailed_answer"},
    "jamhara-glossary": {
        "id",
        "url",
        "term_ar",
        "terminological_meaning",
        "short_explanation",
        "linguistic_definition",
        "definition",
        "translations",
    },
}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise CorpusValidationError(reason)


def _object(pairs: list) -> dict:
    value = {}
    for key, item in pairs:
        _require(key not in value, "Private index duplicate JSON key")
        value[key] = item
    return value


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        value = stream.read(limit + 1)
    _require(len(value) <= limit, "Private index size limit exceeded")
    return value


# Displayed fields are bounded like every other displayed text. Bayyinat's detailed
# answer is indexing input only (display shows the summary or a 400-character first
# paragraph) and real answers run past 12,000 characters, so it has its own bound.
DISPLAY_FIELD_LIMIT = 12000
INDEX_ONLY_FIELD_LIMIT = 200000


def _string(value: object, *, optional: bool = False, limit: int = DISPLAY_FIELD_LIMIT) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= limit
        and (optional or bool(value.strip()))
        and not any(0xD800 <= ord(char) <= 0xDFFF or char == "\x00" for char in value)
    )


def _manifest_entry(directory: Path, source_id: str, expected_format_version: int) -> dict:
    """The validated manifest entry for one source file, with its traversal status.

    Completeness is per source: an entry carries ``status`` ``complete`` or
    ``partial`` (written by the owner's build-short-index tool). A manifest without
    per-entry status falls back to the run-level ``complete`` flag.
    """
    name, host, _ = _CONFIG[source_id]
    manifest = json.loads(
        _read(directory / "manifest.json", 4 * 1024 * 1024), object_pairs_hook=_object
    )
    _require(
        isinstance(manifest, dict)
        and type(manifest.get("format_version")) is int
        and manifest.get("format_version") == expected_format_version
        and isinstance(manifest.get("complete"), bool)
        and manifest.get("authority_event") == AUTHORITY_EVENT,
        "Private index owner manifest required",
    )
    files = manifest.get("files")
    _require(isinstance(files, list), "Private index manifest files required")
    matching = [item for item in files if isinstance(item, dict) and item.get("file") == name]
    _require(len(matching) == 1, "Private index manifest entry must be unique")
    entry = dict(matching[0])
    status = entry.get("status", "complete" if manifest["complete"] else "partial")
    _require(status in {"complete", "partial"}, "Private index source status invalid")
    _require(entry.get("source_host") == host, "Private index checksum or source mismatch")
    entry["status"] = status
    return entry


def short_index_status(directory: Path, source_id: str, *, expected_format_version: int = 2) -> str:
    """``complete`` or ``partial`` for one source, read from the owner manifest only."""
    _require(source_id in _CONFIG, "Unknown private short-index source")
    try:
        return _manifest_entry(directory, source_id, expected_format_version)["status"]
    except CorpusValidationError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError, AttributeError):
        raise CorpusValidationError("Private short-index validation failed") from None


def load_short_index(
    directory: Path,
    source_id: str,
    expected_sha256: str,
    *,
    sources_path: Path = ROOT / "corpus/approved_sources.json",
    allow_pending_review: bool = False,
    owner_review_event: str | None = None,
    expected_format_version: int = 1,
    allow_partial: bool = False,
) -> tuple[dict, ...]:
    """Validate the whole file or return nothing; source text is copied unchanged.

    expected_sha256 must come from the owner's trusted handoff, not computed by
    the caller from the file being loaded. The source's manifest entry must be
    complete unless the owner opted into a partial source with allow_partial.
    Scoped display permission is distinct from unrestricted redistribution.
    Returned records are candidates, not quote/embedded-scripture authorization.
    """
    _require(source_id in _CONFIG, "Unknown private short-index source")
    _require(
        type(expected_format_version) is int and expected_format_version in {1, 2},
        "Private index unsupported format version",
    )
    _require(
        isinstance(expected_sha256, str) and bool(_HEX.fullmatch(expected_sha256)),
        "Private index trusted checksum required",
    )
    _require(
        allow_pending_review
        or (isinstance(owner_review_event, str) and bool(_HEX.fullmatch(owner_review_event))),
        "Private index owner review required",
    )
    name, host, short_field = _CONFIG[source_id]
    if expected_format_version == 2:
        short_field = "question_text" if source_id == "bayyinat" else "terminological_meaning"
    fields = _V2_FIELDS if expected_format_version == 2 else _FIELDS
    try:
        source = read_sources(sources_path).get(source_id, {})
        _require(
            source.get("license_status") == "confirmed"
            and source.get("ingestion_allowed") is True
            and source.get("public_display_allowed") is True
            and source.get("redistribution_allowed") is False
            and source.get("owner_authority_event") == AUTHORITY_EVENT,
            "Private index scoped source permission required",
        )
        entry = _manifest_entry(directory, source_id, expected_format_version)
        _require(
            entry["status"] == "complete" or allow_partial is True,
            "Private index source is partial; owner opt-in required",
        )
        data = _read(directory / name, 32 * 1024 * 1024)
        _require(
            hashlib.sha256(data).hexdigest() == expected_sha256
            and entry.get("sha256") == expected_sha256
            and entry.get("source_host") == host
            and type(entry.get("bytes")) is int
            and entry["bytes"] == len(data),
            "Private index checksum or source mismatch",
        )
        records = []
        identities = set()
        for line in data.decode("utf-8").splitlines():
            _require(bool(line.strip()), "Private index blank row")
            row = json.loads(line, object_pairs_hook=_object)
            _require(
                isinstance(row, dict) and row.keys() == fields[source_id],
                "Private index fields mismatch",
            )
            _require(
                all(_string(row[field]) for field in ("id", "url", short_field)),
                "Private index required text invalid",
            )
            url = urlsplit(row["url"])
            decoded_path = unquote(url.path)
            identity = url.path + ("?" + url.query if url.query else "")
            _require(
                url.scheme == "https"
                and url.hostname == host
                and url.port in {None, 443}
                and not url.username
                and not url.password
                and not url.fragment
                and all(
                    key in {"page", "lang", "language"}
                    for key, _ in parse_qsl(url.query, keep_blank_values=True)
                )
                and not any(char.isspace() for char in row["url"])
                and identity == row["id"]
                and "\\" not in decoded_path
                and "%" not in decoded_path
                and not re.search(r"%2f|%5c", url.path, re.IGNORECASE)
                and not any(part in {".", ".."} for part in decoded_path.split("/")),
                "Private index source URL invalid",
            )
            _require(row["id"] not in identities, "Private index duplicate identity")
            identities.add(row["id"])
            if expected_format_version == 2:
                _require(
                    all(
                        value == "ar" or key == "page"
                        for key, value in parse_qsl(url.query, keep_blank_values=True)
                    ),
                    "Private index non-Arabic selector",
                )
                title_field = "title" if source_id == "bayyinat" else "term_ar"
                required = [title_field, short_field]
                index_only = []
                if source_id == "bayyinat":
                    index_only = ["detailed_answer"]
                    optional = ["summary"]
                    lists = ["keywords"]
                    path_pattern = r"/ar/category/[^/]+/[^/]+/?"
                else:
                    optional = ["short_explanation", "linguistic_definition", "definition"]
                    lists = ["translations"]
                    path_pattern = r"/dictionary/word/[^/]+/?"
                _require(
                    bool(re.fullmatch(path_pattern, decoded_path)),
                    "Private index v2 source path invalid",
                )
                _require(
                    all(_string(row[field]) for field in required)
                    and all(_string(row[field], optional=True) for field in optional)
                    and all(
                        _string(row[field], limit=INDEX_ONLY_FIELD_LIMIT) for field in index_only
                    ),
                    "Private index v2 text invalid",
                )
                _require(
                    all(
                        len(re.findall(r"[ء-ي]", row[field]))
                        > len(re.findall(r"[A-Za-z]", row[field]))
                        for field in [*required, *index_only]
                    ),
                    "Private index v2 Arabic text required",
                )
                _require(
                    all(
                        isinstance(row[field], list)
                        and len(row[field]) <= 200
                        and all(_string(item) for item in row[field])
                        for field in lists
                    ),
                    "Private index v2 list invalid",
                )
                records.append(row)
                continue
            if source_id == "bayyinat":
                _require(
                    bool(
                        re.fullmatch(
                            r"/(?:[a-z]{2}/)?(?:questions?|answers?|doubts?|shubuhat|categories?|topics?)/[^/]+(?:/[^/]+)*/?",
                            decoded_path,
                            re.IGNORECASE,
                        )
                    ),
                    "Private index Bayyinat path invalid",
                )
                _require(
                    _string(row["title"]) and _string(row["category"], optional=True),
                    "Private index metadata invalid",
                )
                for field in ("similar_phrasings", "keywords"):
                    _require(
                        isinstance(row[field], list)
                        and len(row[field]) <= 200
                        and all(_string(item) for item in row[field]),
                        "Private index phrase list invalid",
                    )
            else:
                _require(
                    bool(re.fullmatch(r"/dictionary/word/[^/]+/?", url.path))
                    and _string(row["term_ar"]),
                    "Private index glossary URL or term invalid",
                )
                translations = row["translations"]
                _require(
                    isinstance(translations, dict)
                    and len(translations) <= 200
                    and all(_string(key) and _string(value) for key, value in translations.items()),
                    "Private index translations invalid",
                )
            records.append(row)
        _require(
            records and type(entry.get("records")) is int and entry["records"] == len(records),
            "Private index record count mismatch",
        )
        return tuple(records)
    except CorpusValidationError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError, AttributeError):
        raise CorpusValidationError("Private short-index validation failed") from None
