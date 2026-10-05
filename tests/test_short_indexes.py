"""Synthetic non-religious private-index handoffs and corruption probes."""

import hashlib
import json

import pytest

from corpus.short_indexes import AUTHORITY_EVENT, load_short_index
from corpus.validate import CorpusValidationError


def handoff(tmp_path, source="bayyinat", rows=None):
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
        "format_version": 1,
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
