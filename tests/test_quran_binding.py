"""Synthetic paired-field fixtures; no scripture or live source content."""

import copy

import pytest

from api.composer import evidence_from
from api.config import load_config
from api.retrieval import BM25Retriever, RetrievalResult
from corpus.quran_binding import display_text, matching_text, validate_pair
from corpus.validate import checksum_text
from tests.test_composer import POLICY, TEXT, TUNING
from tests.test_gatekeeper import gate, local


def paired():
    r = local()
    r.update(
        corpus_id="quran:1:1",
        sura_no=1,
        aya_no=1,
        ref={"surah": 1, "ayah": 1},
        aya_text_emlaey=TEXT,
        aya_text_unicode=TEXT + " synthetic-display-mark",
        checksum_sha256=checksum_text(TEXT),
        checksum_unicode_sha256=checksum_text(TEXT + " synthetic-display-mark"),
    )
    return r


def test_matching_and_display_use_one_original_record():
    r = paired()
    before = copy.deepcopy(r)
    g = gate(locals=[r])
    assert matching_text(r) == TEXT
    assert display_text(r) == r["aya_text_unicode"]
    assert g.verify(r["corpus_id"], TEXT) == r
    assert g.verify(r["corpus_id"], r["aya_text_unicode"]) == r
    assert g.verify(r["corpus_id"], r["aya_text_unicode"] + " edited") is None
    item = evidence_from(RetrievalResult(r, 1, 1))
    assert item["quote_ar"] == r["aya_text_unicode"]
    assert item["ref"] == {"surah": 1, "ayah": 1}
    assert r == before
    _, tuning = load_config(POLICY, TUNING)
    results = BM25Retriever([r], tuning).retrieve(TEXT)
    assert results[0].record == r
    assert g.detector.classify(TEXT).classification == "VERBATIM"
    assert g.scan_scripture(r["aya_text_unicode"]).findings


@pytest.mark.parametrize(
    "field,value",
    [
        ("aya_text_emlaey", "other record"),
        ("aya_text_unicode", "other display"),
        ("checksum_unicode_sha256", "wrong"),
        ("checksum_sha256", "wrong"),
        ("text_normalized", "wrong"),
        ("aya_no", 2),
        ("sura_no", True),
        ("ref", {"surah": 1, "ayah": 2}),
        ("corpus_id", "quran:1:2"),
        ("domain", "hadith"),
    ],
)
def test_mismatched_fields_cannot_project_evidence(field, value):
    r = paired()
    r[field] = value
    with pytest.raises(ValueError):
        validate_pair(r)
    with pytest.raises(ValueError):
        evidence_from(RetrievalResult(r, 1, 1))


@pytest.mark.parametrize(
    "field", ["aya_text_emlaey", "aya_text_unicode", "checksum_unicode_sha256"]
)
def test_incomplete_pairs_fail_closed(field):
    r = paired()
    del r[field]
    with pytest.raises(ValueError):
        display_text(r)
