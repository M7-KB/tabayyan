"""Synthetic, non-scriptural fixtures for the eight corpus rules and loader boundary."""

import copy
import json

import pytest

from corpus.loader import load_corpus
from corpus.normalize import normalize_arabic
from corpus.validate import (
    CorpusValidationError,
    checksum_text,
    main,
    read_records,
    read_register,
    read_sources,
    validate_records,
)


def record(domain="faq", corpus_id="fixture:one"):
    text = "  Synthetic fixture text: café.\nUnchanged spacing.  "
    return {
        "corpus_id": corpus_id,
        "domain": domain,
        "source_id": domain,
        "source_name_ar": "Synthetic source",
        "source_url": "https://fixture.invalid/item",
        "text_ar": text,
        "text_normalized": normalize_arabic(text),
        "checksum_sha256": checksum_text(text),
        "ref": {"collection": "Synthetic fixture", "number": "fixture"},
        "lang": "ar",
        "license": "Synthetic permission",
        "license_url": "https://fixture.invalid/permission",
        "retrieved_at": "2026-10-03",
        "approved_by": "sharia-reviewer-1",
    }


def metadata(*domains):
    sources = {
        domain: {
            "source_id": domain,
            "domains": [domain],
            "entry_url": "https://fixture.invalid/",
            "license_status": "confirmed",
            "ingestion_allowed": True,
            "redistribution_allowed": True,
        }
        for domain in domains
    }
    register = {
        domain: {
            "Source id": domain,
            "domain": domain,
            "license": "Synthetic permission",
            "license_url": "https://fixture.invalid/permission",
        }
        for domain in domains
    }
    return sources, register


@pytest.mark.parametrize(
    "field,value,rule",
    [
        ("source_id", "unknown", 1),
        ("source_id", [], 1),
        ("domain", "hadith", 1),
        ("text_ar", " ", 3),
        ("text_ar", "\ud800", 3),
        ("checksum_sha256", "wrong", 3),
        ("text_normalized", "edited", 4),
        ("license", "pending", 5),
        ("license", "different", 5),
        ("license_url", "https://fixture.invalid/other", 5),
        ("license_url", "pending", 5),
        ("corpus_id", "", 6),
        ("approved_by", "pending", 7),
        ("approved_by", "unrecorded-person", 7),
        ("approved_by", [], 7),
    ],
)
def test_invalid_record_rejected(field, value, rule):
    item = record()
    item[field] = value
    with pytest.raises(CorpusValidationError, match=f"rule {rule}"):
        validate_records([item], *metadata("faq"))


@pytest.mark.parametrize(
    "grading",
    [
        None,
        {},
        {"grade_ar": "Synthetic grade"},
        {
            "grade_ar": "Synthetic grade",
            "grader_ar": "Synthetic grader",
            "grading_source_url": "http://fixture.invalid/grade",
        },
    ],
)
def test_hadith_requires_complete_grading(grading):
    item = record("hadith")
    item["grading"] = grading
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], *metadata("hadith"))


def graded_hadith():
    item = record("hadith")
    item["grading"] = {
        "grade_ar": "Synthetic grade",
        "grader_ar": "Synthetic grader",
        "grading_source_id": "dorar-hadith",
        "grading_source_url": "https://fixture.invalid/hadith/grade",
    }
    sources, register = metadata("hadith")
    sources["dorar-hadith"] = dict(sources["hadith"], source_id="dorar-hadith")
    sources["dorar-hadith"]["entry_url"] = "https://fixture.invalid/hadith"
    register["dorar-hadith"] = dict(register["hadith"], **{"Source id": "dorar-hadith"})
    return item, sources, register


def test_synthetic_hadith_with_explicit_grading_passes():
    item, sources, register = graded_hadith()
    validate_records([item], sources, register)


@pytest.mark.parametrize("source_id", [None, "unknown", "hadith", [], "dorar-tafsir"])
def test_grading_requires_separate_approved_source_id(source_id):
    item, sources, register = graded_hadith()
    item["grading"]["grading_source_id"] = source_id
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], sources, register)


@pytest.mark.parametrize(
    "url",
    [
        "https://unapproved.invalid/hadith/grade",
        "https://fixture.invalid.evil.invalid/hadith/grade",
        "https://fixture.invalid/tafseer/grade",
        "https://fixture.invalid/hadith-other/grade",
        "https://fixture.invalid/hadith/../tafseer",
        "https://fixture.invalid/hadith/%2e%2e/tafseer",
        "https://fixture.invalid/hadith\\grade",
        "https://fixture.invalid:444/hadith/grade",
        "https://fixture.invalid:bad/hadith/grade",
        "https://user@fixture.invalid/hadith/grade",
        "http://fixture.invalid/hadith/grade",
    ],
)
def test_grading_url_must_match_approved_origin_and_section(url):
    item, sources, register = graded_hadith()
    item["grading"]["grading_source_url"] = url
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], sources, register)


@pytest.mark.parametrize(
    "field,value",
    [
        ("license_status", "pending"),
        ("ingestion_allowed", False),
        ("redistribution_allowed", False),
        ("domains", ["tafsir"]),
        ("entry_url", None),
    ],
)
def test_grading_source_requires_independent_permission(field, value):
    item, sources, register = graded_hadith()
    sources["dorar-hadith"][field] = value
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], sources, register, allow_pending_review=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("license", "pending"),
        ("license_url", "pending"),
        ("domain", "tafsir"),
    ],
)
def test_grading_register_requires_clearance(field, value):
    item, sources, register = graded_hadith()
    register["dorar-hadith"][field] = value
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], sources, register)


@pytest.mark.parametrize(
    "field,value",
    [
        ("license_status", "pending"),
        ("ingestion_allowed", False),
        ("ingestion_allowed", "true"),
        ("redistribution_allowed", False),
    ],
)
def test_permission_flags_fail_closed_even_in_offline_review(field, value):
    sources, register = metadata("faq")
    sources["faq"][field] = value
    item = record()
    item["approved_by"] = "pending"
    with pytest.raises(CorpusValidationError, match="rule 5"):
        validate_records([item], sources, register, allow_pending_review=True)


def test_duplicate_corpus_id_rejected():
    with pytest.raises(CorpusValidationError, match="rule 6"):
        validate_records([record(), record()], *metadata("faq"))


def test_pending_review_requires_explicit_opt_in():
    item = record()
    item["approved_by"] = "pending"
    validate_records([item], *metadata("faq"), allow_pending_review=True)


@pytest.mark.parametrize("target", [None, "missing", "fixture:translation", []])
def test_translation_requires_resolving_quran_target(target):
    item = record("quran_translation", "fixture:translation")
    item["text_en"] = "Synthetic English fixture"
    item["checksum_en_sha256"] = checksum_text(item["text_en"])
    item["translation_of"] = target
    with pytest.raises(CorpusValidationError, match="rule 8"):
        validate_records([item], *metadata("quran_translation"))


@pytest.mark.parametrize("domain", ["quran_translation", "glossary"])
def test_translation_and_glossary_require_english(domain):
    with pytest.raises(CorpusValidationError, match="rule 8"):
        validate_records([record(domain)], *metadata(domain))


def test_translation_resolution_independent_of_file_order():
    original = record("quran", "fixture:original")
    translation = record("quran_translation", "fixture:translation")
    translation.update(text_en="Synthetic English fixture", translation_of="fixture:original")
    translation["checksum_en_sha256"] = checksum_text(translation["text_en"])
    validate_records([translation, original], *metadata("quran", "quran_translation"))


@pytest.mark.parametrize("domain", ["glossary", "quran_translation", "faq"])
@pytest.mark.parametrize("mutation", ["edit", "strip", "normalize", "missing_checksum", "null"])
def test_english_integrity_covers_every_present_display_text(domain, mutation):
    item = record(domain)
    item["text_en"] = "  Synthetic English: caf\u00e9.\n  "
    item["checksum_en_sha256"] = checksum_text(item["text_en"])
    original = record("quran", "fixture:original")
    if domain == "quran_translation":
        item["translation_of"] = original["corpus_id"]
    records = [original, item]
    sources, register = metadata("quran", domain)
    validate_records(records, sources, register)
    if mutation == "missing_checksum":
        del item["checksum_en_sha256"]
    elif mutation == "null":
        item["text_en"] = None
    elif mutation == "normalize":
        item["text_en"] = item["text_en"].replace("\u00e9", "e\u0301")
    elif mutation == "strip":
        item["text_en"] = item["text_en"].strip()
    else:
        item["text_en"] += " edited"
    with pytest.raises(CorpusValidationError, match="rule [38]"):
        validate_records(records, sources, register)


def test_english_checksum_without_text_rejected():
    item = record()
    item["checksum_en_sha256"] = checksum_text("Synthetic English")
    with pytest.raises(CorpusValidationError, match="rule 3"):
        validate_records([item], *metadata("faq"))


@pytest.mark.parametrize(
    "url",
    [
        "https://unapproved.invalid/item",
        "https://fixture.invalid.evil.invalid/item",
        "https://fixture.invalid:444/item",
        "https://fixture.invalid:bad/item",
        "https://fixture.invalid/a/../item",
        "https://fixture.invalid/%2fitem",
        "https://fixture.invalid/a\\item",
        "https://user@fixture.invalid/item",
    ],
)
def test_record_source_url_requires_registered_host(url):
    item = record()
    item["source_url"] = url
    with pytest.raises(CorpusValidationError, match="source_url"):
        validate_records([item], *metadata("faq"))


def test_record_source_url_requires_registered_entry():
    sources, register = metadata("faq")
    del sources["faq"]["entry_url"]
    with pytest.raises(CorpusValidationError, match="source_url"):
        validate_records([record()], sources, register)


@pytest.fixture
def artifacts(tmp_path):
    corpus_path = tmp_path / "corpus.jsonl"
    corpus_path.write_text(json.dumps(record(), ensure_ascii=False) + "\n", encoding="utf-8")
    source_path = tmp_path / "sources.json"
    sources, _ = metadata("faq")
    source_path.write_text(json.dumps({"sources": list(sources.values())}), encoding="utf-8")
    register_path = tmp_path / "SOURCES.md"
    register_path.write_text(
        "| Source id | domain | license | license_url |\n|---|---|---|---|\n"
        "| faq | faq | Synthetic permission | https://fixture.invalid/permission |\n",
        encoding="utf-8",
    )
    return corpus_path, source_path, register_path


def test_loader_preserves_original_and_does_not_mutate_artifact(artifacts):
    path, sources, register = artifacts
    before = path.read_bytes()
    result = load_corpus(path, sources_path=sources, register_path=register)
    assert result == [record()]
    assert path.read_bytes() == before
    assert checksum_text(record()["text_ar"].strip()) != record()["checksum_sha256"]


def test_loader_default_rejects_pending_records(artifacts):
    path, sources, register = artifacts
    item = record()
    item["approved_by"] = "pending"
    path.write_text(json.dumps(item) + "\n", encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="rule 7"):
        load_corpus(path, sources_path=sources, register_path=register)
    assert (
        main(
            [
                "--corpus",
                str(path),
                "--sources",
                str(sources),
                "--register",
                str(register),
                "--allow-pending-review",
            ]
        )
        == 0
    )


@pytest.mark.parametrize("text", ["", "\n", "{bad}", "[]", "null", '{"x":1,"x":2}', '{"x":NaN}'])
def test_bad_jsonl_rejected(tmp_path, text):
    path = tmp_path / "corpus.jsonl"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(CorpusValidationError):
        read_records(path)


def test_missing_artifact_fails_cli_without_echoing_source(tmp_path, capsys):
    assert main(["--corpus", str(tmp_path / "missing.jsonl")]) == 1
    assert "Cannot read corpus artifact" in capsys.readouterr().out


def test_register_and_allowlist_contract_errors(artifacts):
    _, sources_path, register_path = artifacts
    sources = read_sources(sources_path)
    register = read_register(register_path)
    assert set(sources) == set(register) == {"faq"}
    altered = copy.deepcopy(register)
    altered["unknown"] = altered.pop("faq")
    with pytest.raises(CorpusValidationError, match="IDs differ"):
        validate_records([record()], sources, altered)
    register_path.write_text("https://fixture.invalid/permission", encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="table required"):
        read_register(register_path)
    sources_path.write_text(
        '{"sources": [{"source_id": "faq", "domains": ["unknown"]}]}', encoding="utf-8"
    )
    with pytest.raises(CorpusValidationError, match="domains"):
        read_sources(sources_path)
