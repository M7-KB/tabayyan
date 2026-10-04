"""Structural live-source contract; fixtures do not prove source provenance."""

import copy

import pytest

from tests.test_card_schema import VALIDATOR, card


def live_card():
    value = card("supported-confirms")
    value["misquote_notice"] = None
    evidence = value["evidence"][0]
    del evidence["corpus_id"]
    evidence["source_ref"] = {
        "source_id": evidence["source_id"],
        "record_ref": "synthetic:record",
        "url": evidence["source_url"],
    }
    value["published_answer"] = {
        "source_id": evidence["source_id"],
        "title_ar": "عنوان تجريبي",
        "excerpt_ar": evidence["quote_ar"],
        "url": evidence["source_url"],
    }
    return value


def test_legacy_cards_and_live_reference_shape_both_validate():
    VALIDATOR.validate(card("supported-confirms"))
    VALIDATOR.validate(live_card())


@pytest.mark.parametrize("field", ["source_id", "record_ref", "url"])
def test_live_ref_requires_every_provenance_field(field):
    value = live_card()
    del value["evidence"][0]["source_ref"][field]
    assert not VALIDATOR.is_valid(value)


@pytest.mark.parametrize("field", ["source_id", "title_ar", "excerpt_ar", "url"])
def test_published_answer_requires_every_field(field):
    value = live_card()
    del value["published_answer"][field]
    assert not VALIDATOR.is_valid(value)


@pytest.mark.parametrize("url", ["http://example.invalid/source", "not-a-url", "https:// "])
def test_live_urls_must_be_https(url):
    value = live_card()
    value["published_answer"]["url"] = url
    value["evidence"][0]["source_ref"]["url"] = url
    assert not VALIDATOR.is_valid(value)


def test_both_or_neither_reference_forms_are_invalid():
    value = live_card()
    value["evidence"][0]["corpus_id"] = "synthetic:duplicate"
    assert not VALIDATOR.is_valid(value)
    del value["evidence"][0]["source_ref"]
    del value["evidence"][0]["corpus_id"]
    assert not VALIDATOR.is_valid(value)


def test_live_hadith_still_requires_source_grading():
    value = live_card()
    value["evidence"][0]["grading"] = None
    assert not VALIDATOR.is_valid(value)


def test_published_answer_requires_evidence_and_rejects_extra_generated_fields():
    value = live_card()
    value["published_answer"]["explanation_ar"] = "Generated"
    assert not VALIDATOR.is_valid(value)
    del value["published_answer"]["explanation_ar"]
    value.update(
        state="CANNOT_CONFIRM",
        alignment=None,
        state_label_key="cannot_confirm",
        abstained_reason="NO_MATCHING_EVIDENCE",
        evidence=[],
        referral=card("cannot-confirm")["referral"],
    )
    assert not VALIDATOR.is_valid(value)


def test_live_notice_uses_same_source_ref_and_grading_contract():
    value = live_card()
    value["misquote_notice"] = {
        "evidence": copy.deepcopy(value["evidence"][0]),
        "note_ar": "تنبيه تجريبي",
    }
    VALIDATOR.validate(value)


def test_missing_term_can_abstain_without_inventing_translation():
    value = card("cannot-confirm")
    value["input_kind"] = "term"
    value["claim"]["origin"] = "term_lookup"
    value["term"] = None
    VALIDATOR.validate(value)


def test_live_term_reference_replaces_glossary_corpus_id():
    value = live_card()
    value["input_kind"] = "term"
    value["claim"]["origin"] = "term_lookup"
    value["term"] = {
        "term_ar": "اسم تجريبي",
        "term_en": "Synthetic name",
        "source_ref": value["evidence"][0]["source_ref"],
    }
    VALIDATOR.validate(value)
    value["term"]["glossary_corpus_id"] = "duplicate"
    assert not VALIDATOR.is_valid(value)
