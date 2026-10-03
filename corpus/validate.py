"""Offline corpus checks for SPEC section 4.2; no downloads or source-text repair."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from corpus.normalize import normalize_arabic

DOMAINS = frozenset(
    {
        "quran",
        "hadith",
        "tafsir",
        "aqeeda",
        "fiqh",
        "seerah",
        "glossary",
        "faq",
        "quran_translation",
    }
)
ROOT = Path(__file__).resolve().parents[1]


class CorpusValidationError(ValueError):
    """An invalid artifact; errors name fields and rows, never source text."""


def checksum_text(text: str) -> str:
    """SHA-256 of original UTF-8 bytes, without stripping or normalization."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require(condition, message):
    if not condition:
        raise CorpusValidationError(message)


def _text(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _https(value):
    if not _text(value) or any(char.isspace() for char in value):
        return False
    try:
        url = urlsplit(value)
        return (
            url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
        )
    except ValueError:
        return False


def _source_url(value, source, *, section=False):
    """Bind URLs to registered metadata; grading also stays in its approved section."""
    entry = source.get("entry_url")
    if not _https(entry) or not _https(value):
        return False
    approved, actual = urlsplit(entry), urlsplit(value)
    try:
        correct_origin = actual.hostname == approved.hostname and actual.port in {None, 443}
    except ValueError:
        return False
    # No encoded or relative path segments can bypass the approved section boundary.
    path = actual.path
    safe_path = (
        "\\" not in path
        and "%" not in path
        and all(segment not in {".", ".."} for segment in path.split("/"))
    )
    base = approved.path.rstrip("/")
    return (
        correct_origin
        and safe_path
        and (not section or path == base or path.startswith(base + "/"))
    )


def _grading_provenance(grading, sources, register, *, require_redistribution=True):
    # The brief permits Dorar hadith gradings; collection IDs are not grading authority.
    source_id = grading.get("grading_source_id")
    if source_id != "dorar-hadith" or source_id not in sources or source_id not in register:
        return False
    source = sources[source_id]
    row = register[source_id]
    return (
        _source_url(grading.get("grading_source_url"), source, section=True)
        and "hadith" in source["domains"]
        and row["domain"] == "hadith"
        and source.get("license_status") == "confirmed"
        and source.get("ingestion_allowed") is True
        and (not require_redistribution or source.get("redistribution_allowed") is True)
        and _text(row.get("license"))
        and row["license"].strip().lower() not in {"pending", "unknown"}
        and _https(row.get("license_url"))
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise CorpusValidationError("Non-finite JSON value")


def _decode(text):
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)


def _json(path):
    try:
        return _decode(path.read_text("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise CorpusValidationError(f"Cannot read JSON artifact: {path.name}") from exc


def read_records(path: Path) -> list[dict]:
    """Read JSONL without rewriting any text. Missing/empty artifacts fail closed."""
    try:
        return parse_records(path.read_bytes())
    except OSError as exc:
        raise CorpusValidationError("Cannot read corpus artifact") from exc


def parse_records(data: bytes) -> list[dict]:
    """Parse the same bytes whose artifact checksum was verified."""
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise CorpusValidationError("Invalid corpus encoding") from exc
    records = []
    for line_number, line in enumerate(lines, 1):
        _require(bool(line.strip()), f"row {line_number}: blank JSONL record")
        try:
            record = _decode(line)
        except ValueError as exc:
            raise CorpusValidationError(f"row {line_number}: invalid JSON") from exc
        _require(isinstance(record, dict), f"row {line_number}: record must be an object")
        records.append(record)
    _require(bool(records), "Corpus artifact is empty")
    return records


def read_register(path: Path) -> dict[str, dict]:
    """Read the explicit P-03 table, not arbitrary URL mentions in Markdown."""
    try:
        lines = path.read_text("utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CorpusValidationError("Cannot read source register") from exc
    starts = [i for i, line in enumerate(lines) if line.startswith("| Source id |")]
    _require(len(starts) == 1, "Exactly one source register table required")
    start = starts[0]

    def cells(line):
        _require(line.endswith("|"), "Malformed source register row")
        return [value.strip() for value in line[1:-1].split("|")]

    headers = cells(lines[start])
    _require(len(headers) == len(set(headers)), "Duplicate source register header")
    _require(
        {"Source id", "domain", "license", "license_url"} <= set(headers),
        "Missing source register header",
    )
    _require(
        start + 1 < len(lines) and lines[start + 1].startswith("|---"),
        "Missing source register separator",
    )
    rows = {}
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        values = cells(line)
        _require(len(values) == len(headers), "Source register column count mismatch")
        row = dict(zip(headers, values, strict=True))
        _require(
            all(_text(row[field]) for field in ("Source id", "license", "license_url")),
            "Missing source register value",
        )
        _require(row["domain"] in DOMAINS, "Invalid source register domain")
        _require(row["Source id"] not in rows, "Duplicate source register source_id")
        rows[row["Source id"]] = row
    _require(bool(rows), "Source register is empty")
    return rows


def read_sources(path: Path) -> dict[str, dict]:
    data = _json(path)
    _require(
        isinstance(data, dict) and isinstance(data.get("sources"), list), "Invalid source allowlist"
    )
    sources = {}
    for source in data["sources"]:
        _require(isinstance(source, dict), "Invalid allowlist source")
        source_id = source.get("source_id")
        _require(_text(source_id), "Missing allowlist source_id")
        _require(source_id not in sources, "Duplicate allowlist source_id")
        domains = source.get("domains")
        _require(
            isinstance(domains, list)
            and bool(domains)
            and all(isinstance(domain, str) and domain in DOMAINS for domain in domains),
            "Invalid allowlist domains",
        )
        sources[source_id] = source
    _require(bool(sources), "Source allowlist is empty")
    return sources


def validate_records(
    records: list[dict],
    sources: dict[str, dict],
    register: dict[str, dict],
    *,
    allow_pending_review: bool = False,
    require_redistribution: bool = True,
) -> None:
    """All eight rules, plus fail-closed ingestion permission from P-04.

    Pending review never waives licence clearance. Public distribution is the default.
    Private challenge use requires confirmed ingestion permission for source and grader.
    Metadata approval is an owner-recorded assertion, not independent proof of sign-off.
    """
    _require(bool(records), "Corpus artifact is empty")
    _require(set(sources) == set(register), "Source register / allowlist IDs differ")
    ids = {}
    for number, record in enumerate(records, 1):
        prefix = f"row {number}"
        _require(isinstance(record, dict), f"{prefix}: record must be an object")
        source_id = record.get("source_id")
        _require(_text(source_id) and source_id in sources, f"{prefix}: unknown source_id (rule 1)")
        source = sources[source_id]
        row = register[source_id]
        domain = record.get("domain")
        _require(
            isinstance(domain, str)
            and domain in DOMAINS
            and domain in source["domains"]
            and domain == row["domain"],
            f"{prefix}: source domain mismatch (rule 1)",
        )
        if domain == "hadith":
            grading = record.get("grading")
            _require(
                isinstance(grading, dict)
                and _text(grading.get("grade_ar"))
                and _text(grading.get("grader_ar"))
                and _https(grading.get("grading_source_url")),
                f"{prefix}: complete grading required (rule 2)",
            )
            _require(
                _grading_provenance(
                    grading, sources, register, require_redistribution=require_redistribution
                ),
                f"{prefix}: approved grading provenance required (rule 2)",
            )
        original = record.get("text_ar")
        _require(_text(original), f"{prefix}: text_ar required (rule 3)")
        _require(
            record.get("checksum_sha256") == checksum_text(original),
            f"{prefix}: checksum_sha256 mismatch (rule 3)",
        )
        _require(
            record.get("text_normalized") == normalize_arabic(original),
            f"{prefix}: text_normalized mismatch (rule 4)",
        )
        licence = record.get("license")
        _require(
            _text(licence)
            and licence.strip().lower() not in {"pending", "unknown"}
            and licence == row["license"]
            and _https(record.get("license_url"))
            and record["license_url"] == row["license_url"],
            f"{prefix}: licence must match cleared register (rule 5)",
        )
        _require(
            source.get("license_status") == "confirmed"
            and source.get("ingestion_allowed") is True
            and (not require_redistribution or source.get("redistribution_allowed") is True),
            f"{prefix}: source ingestion/redistribution not cleared (rule 5)",
        )
        corpus_id = record.get("corpus_id")
        _require(
            _text(corpus_id) and corpus_id not in ids,
            f"{prefix}: missing or duplicate corpus_id (rule 6)",
        )
        ids[corpus_id] = record
        allowed_approval = (
            {"sharia-reviewer-1", "pending"} if allow_pending_review else {"sharia-reviewer-1"}
        )
        _require(
            _text(record.get("approved_by")) and record["approved_by"] in allowed_approval,
            f"{prefix}: specialist approval required (rule 7)",
        )
        for field in ("source_name_ar", "source_url", "lang", "retrieved_at"):
            _require(_text(record.get(field)), f"{prefix}: {field} required")
        _require(_https(record["source_url"]), f"{prefix}: source_url must be HTTPS")
        _require(
            _source_url(record["source_url"], source),
            f"{prefix}: source_url must match registered source host (rule 1)",
        )
        _require(record["lang"] in {"ar", "en"}, f"{prefix}: invalid lang")
        _require(
            isinstance(record.get("ref"), dict)
            and bool(record["ref"])
            and all(
                _text(key) and (_text(value) or type(value) is int and value > 0)
                for key, value in record["ref"].items()
            ),
            f"{prefix}: source reference required",
        )
        if domain in {"quran_translation", "glossary"}:
            _require(_text(record.get("text_en")), f"{prefix}: text_en required (rule 8)")
        if "text_en" in record:
            _require(_text(record["text_en"]), f"{prefix}: invalid text_en (rule 3)")
            _require(
                record.get("checksum_en_sha256") == checksum_text(record["text_en"]),
                f"{prefix}: checksum_en_sha256 mismatch (rule 3)",
            )
        else:
            _require(
                "checksum_en_sha256" not in record,
                f"{prefix}: checksum_en_sha256 requires text_en (rule 3)",
            )
    # Resolve after collecting all IDs, so file ordering cannot affect translations.
    for number, record in enumerate(records, 1):
        if record["domain"] == "quran_translation":
            target = record.get("translation_of")
            _require(
                _text(target) and target in ids and ids[target]["domain"] == "quran",
                f"row {number}: translation_of must resolve to quran (rule 8)",
            )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpus/corpus.jsonl")
    parser.add_argument("--sources", type=Path, default=ROOT / "corpus/approved_sources.json")
    parser.add_argument("--register", type=Path, default=ROOT / "SOURCES.md")
    parser.add_argument(
        "--allow-pending-review",
        action="store_true",
        help="Permit literal pending approval; never waives licence clearance",
    )
    parser.add_argument(
        "--private-use",
        action="store_true",
        help="Challenge-app use only; still requires confirmed ingestion permission",
    )
    args = parser.parse_args(argv)
    try:
        records = read_records(args.corpus)
        validate_records(
            records,
            read_sources(args.sources),
            read_register(args.register),
            allow_pending_review=args.allow_pending_review,
            require_redistribution=not args.private_use,
        )
    except CorpusValidationError as exc:
        print(f"Corpus validation failed: {exc}")
        return 1
    print(
        f"Validated {len(records)} records; mode="
        f"{'offline-review' if args.allow_pending_review else 'runtime-approved'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
