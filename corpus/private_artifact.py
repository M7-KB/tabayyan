"""Load an owner-mounted file, bound to a public checksum-only manifest."""

import hashlib
import re
from pathlib import Path

from corpus.validate import (
    ROOT,
    CorpusValidationError,
    _decode,
    parse_records,
    read_register,
    read_sources,
    validate_records,
)

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 4096


def _read_bounded(path: Path, limit: int) -> bytes:
    try:
        if not path.is_file():
            raise OSError("Not a regular artifact file")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError:
        raise CorpusValidationError("Private corpus file unavailable") from None
    if len(data) > limit:
        raise CorpusValidationError("Private corpus file exceeds size limit")
    return data


def load_private_corpus(
    path: Path,
    manifest_path: Path = ROOT / "corpus/manifest.json",
    *,
    allow_pending_review: bool = False,
    require_public_display: bool = True,
    sources_path: Path = ROOT / "corpus/approved_sources.json",
    register_path: Path = ROOT / "SOURCES.md",
) -> tuple[list[dict], str]:
    """Publish nothing until hash, permissions, provenance and every row pass.

    Read bytes once; validation uses exactly the hashed bytes. This never downloads,
    rewrites original text, or changes approved_by. Errors contain no paths or text.
    """
    try:
        manifest = _decode(_read_bounded(manifest_path, MAX_MANIFEST_BYTES).decode("utf-8"))
        if not isinstance(manifest, dict) or set(manifest) != {"sha256", "corpus_version"}:
            raise CorpusValidationError("Invalid private corpus manifest")
        digest, version = manifest["sha256"], manifest["corpus_version"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CorpusValidationError("Invalid private corpus manifest")
        if not isinstance(version, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version
        ):
            raise CorpusValidationError("Invalid private corpus manifest")
        data = _read_bounded(path, MAX_ARTIFACT_BYTES)
        if hashlib.sha256(data).hexdigest() != digest:
            raise CorpusValidationError("Private corpus checksum mismatch")
        records = parse_records(data)
        validate_records(
            records,
            read_sources(sources_path),
            read_register(register_path),
            allow_pending_review=allow_pending_review,
            require_redistribution=False,
            require_public_display=require_public_display,
        )
    except CorpusValidationError:
        # Validator reasons contain only fixed messages and row/field identifiers.
        raise
    except (ValueError, UnicodeError, RecursionError):
        # Do not expose parser exceptions, private filenames or source text.
        raise CorpusValidationError("Private corpus validation failed") from None
    return records, version
