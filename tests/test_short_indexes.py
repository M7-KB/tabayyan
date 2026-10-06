"""Synthetic non-religious private-index handoffs and corruption probes."""

import hashlib
import json

import pytest

from corpus.short_indexes import AUTHORITY_EVENT, load_short_index, short_index_status
from corpus.validate import CorpusValidationError


def handoff(tmp_path, source="bayyinat", rows=None, version=1):
    name, host = (
        ("bayyinat.jsonl", "bayenat.net")
        if source == "bayyinat"
        else ("glossary.jsonl", "islamic-content.com")
    )
    if rows is None:
        rows = (
            [
                {
                    "id": "/question/1",
                    "url": "https://bayenat.net/question/1",
                    "title": "Sample question",
                    "similar_phrasings": ["Alternate"],
                    "short_answer": "Short & exact.",
                    "keywords": [],
                    "category": "",
                }
            ]
            if (source == "bayyinat")
            else [
                {
                    "id": "/dictionary/word/1",
                    "url": "https://islamic-content.com/dictionary/word/1",
                    "term_ar": "Sample",
                    "definition_short": "Brief & exact.",
                    "translations": {"English": "Supplied"},
                }
            ]
        )
    data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
    digest = hashlib.sha256(data).hexdigest()
    (tmp_path / name).write_bytes(data)
    manifest = {
        "format_version": version,
        "complete": True,
        "authority_event": AUTHORITY_EVENT,
        "files": [
            {
                "file": name,
                "source_host": host,
                "sha256": digest,
                "bytes": len(data),
                "records": len(rows),
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    sources = {
        "sources": [
            {
                "source_id": source,
                "domains": ["faq" if source == "bayyinat" else "glossary"],
                "license_status": "confirmed",
                "ingestion_allowed": True,
                "public_display_allowed": True,
                "redistribution_allowed": False,
                "owner_authority_event": AUTHORITY_EVENT,
            }
        ]
    }
    registry = tmp_path / "sources.json"
    registry.write_text(json.dumps(sources), encoding="utf-8")
    return digest, registry, rows


@pytest.mark.parametrize("source", ["bayyinat", "jamhara-glossary"])
def test_valid_handoff_keeps_exact_short_text(tmp_path, source):
    digest, registry, rows = handoff(tmp_path, source)
    assert load_short_index(
        tmp_path, source, digest, sources_path=registry, allow_pending_review=True
    ) == tuple(rows)
    with pytest.raises(CorpusValidationError, match="review"):
        load_short_index(tmp_path, source, digest, sources_path=registry)


@pytest.mark.parametrize(
    "field,value", [("complete", False), ("authority_event", "0" * 64), ("format_version", 2)]
)
def test_manifest_authority_and_completeness(tmp_path, field, value):
    digest, registry, _ = handoff(tmp_path)
    file = tmp_path / "manifest.json"
    manifest = json.loads(file.read_text())
    manifest[field] = value
    file.write_text(json.dumps(manifest))
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path, "bayyinat", digest, sources_path=registry, allow_pending_review=True
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("license_status", "pending"),
        ("ingestion_allowed", False),
        ("public_display_allowed", False),
        ("redistribution_allowed", True),
        ("owner_authority_event", "0" * 64),
    ],
)
def test_source_permission_boundaries(tmp_path, field, value):
    digest, registry, _ = handoff(tmp_path)
    sources = json.loads(registry.read_text())
    sources["sources"][0][field] = value
    registry.write_text(json.dumps(sources))
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path, "bayyinat", digest, sources_path=registry, allow_pending_review=True
        )


@pytest.mark.parametrize(
    "mutation", ["hash", "foreign_url", "duplicate", "extra", "empty", "invalid_translations"]
)
def test_corrupt_file_never_returns_partial_records(tmp_path, mutation):
    digest, registry, rows = handoff(tmp_path)
    if mutation == "hash":
        (tmp_path / "bayyinat.jsonl").write_text("private text must not appear in errors")
    else:
        if mutation == "foreign_url":
            rows[0]["url"] = "https://evil.example/question/1"
        if mutation == "duplicate":
            rows.append(rows[0].copy())
        if mutation == "extra":
            rows[0]["full_answer"] = "Detailed"
        if mutation == "empty":
            rows[0]["short_answer"] = ""
        if mutation == "invalid_translations":
            rows[0]["translations"] = ["Bad"]
        digest, registry, _ = handoff(tmp_path, rows=rows)
    with pytest.raises(CorpusValidationError) as error:
        load_short_index(
            tmp_path, "bayyinat", digest, sources_path=registry, allow_pending_review=True
        )
    assert "private text" not in str(error.value)


@pytest.mark.parametrize("query", ["?lang=ar", "?language=en", "?page=2&lang=ar"])
def test_publisher_selectors_preserve_full_identity(tmp_path, query):
    _, _, rows = handoff(tmp_path)
    rows[0]["url"] += query
    rows[0]["id"] += query
    digest, registry, _ = handoff(tmp_path, rows=rows)
    assert load_short_index(
        tmp_path, "bayyinat", digest, sources_path=registry, allow_pending_review=True
    )[0]["url"].endswith(query)


@pytest.mark.parametrize(
    "source,path",
    [
        ("bayyinat", "/news/1"),
        ("bayyinat", "/question/%2e%2e"),
        ("bayyinat", "/question/one%2ftwo"),
        ("jamhara-glossary", "/dictionary/word/%2e%2e"),
        ("jamhara-glossary", "/dictionary/word/%252e%252e"),
        ("jamhara-glossary", "/dictionary/word/one%5ctwo"),
    ],
)
def test_unrelated_encoded_parent_and_separator_paths_rejected(tmp_path, source, path):
    _, _, rows = handoff(tmp_path, source)
    host = "bayenat.net" if source == "bayyinat" else "islamic-content.com"
    rows[0]["id"] = path
    rows[0]["url"] = "https://" + host + path
    digest, registry, _ = handoff(tmp_path, source, rows)
    with pytest.raises(CorpusValidationError):
        load_short_index(tmp_path, source, digest, sources_path=registry, allow_pending_review=True)


def v2_row(source):
    if source == "bayyinat":
        return {
            "id": "/ar/category/sample/1?lang=ar",
            "url": "https://bayenat.net/ar/category/sample/1?lang=ar",
            "title": "سؤال عينة",
            "question_text": "نص سؤال عينة.",
            "summary": "",
            "keywords": [],
            "detailed_answer": "جواب عينة & دقيق.",
        }
    return {
        "id": "/dictionary/word/1?lang=ar",
        "url": "https://islamic-content.com/dictionary/word/1?lang=ar",
        "term_ar": "مصطلح عينة",
        "terminological_meaning": "معنى عينة.",
        "short_explanation": "",
        "linguistic_definition": "",
        "definition": "",
        "translations": ["English: Sample equivalent"],
    }


@pytest.mark.parametrize("source", ["bayyinat", "jamhara-glossary"])
def test_v2_handoff_preserves_owner_fields_and_requires_explicit_version(tmp_path, source):
    digest, registry, rows = handoff(tmp_path, source, [v2_row(source)], version=2)
    assert load_short_index(
        tmp_path,
        source,
        digest,
        sources_path=registry,
        allow_pending_review=True,
        expected_format_version=2,
    ) == tuple(rows)
    with pytest.raises(CorpusValidationError):
        load_short_index(tmp_path, source, digest, sources_path=registry, allow_pending_review=True)


@pytest.mark.parametrize(
    "source,field,value",
    [
        ("bayyinat", "detailed_answer", ""),
        ("bayyinat", "question_text", "English text with ع"),
        ("bayyinat", "summary", 7),
        ("bayyinat", "keywords", "sample"),
        ("jamhara-glossary", "translations", {"English": "Sample"}),
        ("jamhara-glossary", "translations", [7]),
        ("jamhara-glossary", "terminological_meaning", "English text"),
    ],
)
def test_v2_invalid_record_is_refused(tmp_path, source, field, value):
    row = v2_row(source)
    row[field] = value
    digest, registry, _ = handoff(tmp_path, source, [row], version=2)
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path,
            source,
            digest,
            sources_path=registry,
            allow_pending_review=True,
            expected_format_version=2,
        )


@pytest.mark.parametrize(
    "path",
    ["/question/1?lang=ar", "/ar/categories/sample?lang=ar", "/ar/category/sample/1?lang=en"],
)
def test_v2_unapproved_route_or_language_is_refused(tmp_path, path):
    row = v2_row("bayyinat")
    row.update(id=path, url="https://bayenat.net" + path)
    digest, registry, _ = handoff(tmp_path, rows=[row], version=2)
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path,
            "bayyinat",
            digest,
            sources_path=registry,
            allow_pending_review=True,
            expected_format_version=2,
        )


def with_status(tmp_path, status, *, run_complete=None):
    """Rewrite the handoff manifest with a per-entry status (owner build-tool format)."""
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][0]["status"] = status
    if run_complete is not None:
        manifest["complete"] = run_complete
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize("source", ["bayyinat", "jamhara-glossary"])
def test_partial_source_loads_only_with_owner_opt_in(tmp_path, source):
    digest, registry, rows = handoff(tmp_path, source)
    with_status(tmp_path, "partial", run_complete=False)
    assert short_index_status(tmp_path, source, expected_format_version=1) == "partial"
    with pytest.raises(CorpusValidationError, match="partial"):
        load_short_index(tmp_path, source, digest, sources_path=registry, allow_pending_review=True)
    loaded = load_short_index(
        tmp_path,
        source,
        digest,
        sources_path=registry,
        allow_pending_review=True,
        allow_partial=True,
    )
    assert list(loaded) == rows


def test_complete_entry_in_an_incomplete_run_manifest_loads(tmp_path):
    digest, registry, rows = handoff(tmp_path, "jamhara-glossary")
    with_status(tmp_path, "complete", run_complete=False)
    assert short_index_status(tmp_path, "jamhara-glossary", expected_format_version=1) == "complete"
    assert (
        list(
            load_short_index(
                tmp_path,
                "jamhara-glossary",
                digest,
                sources_path=registry,
                allow_pending_review=True,
            )
        )
        == rows
    )


def test_manifest_without_entry_status_falls_back_to_run_flag(tmp_path):
    digest, registry, rows = handoff(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["complete"] = False
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert short_index_status(tmp_path, "bayyinat", expected_format_version=1) == "partial"
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path, "bayyinat", digest, sources_path=registry, allow_pending_review=True
        )


def test_partial_opt_in_never_relaxes_hash_pinning(tmp_path):
    digest, registry, rows = handoff(tmp_path)
    with_status(tmp_path, "partial", run_complete=False)
    with pytest.raises(CorpusValidationError):
        load_short_index(
            tmp_path,
            "bayyinat",
            "0" * 64,
            sources_path=registry,
            allow_pending_review=True,
            allow_partial=True,
        )
    with pytest.raises(CorpusValidationError):
        with_status(tmp_path, "unknown")
        load_short_index(
            tmp_path,
            "bayyinat",
            digest,
            sources_path=registry,
            allow_pending_review=True,
            allow_partial=True,
        )
