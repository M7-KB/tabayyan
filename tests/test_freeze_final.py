"""Final fixes before the code freeze: a nominated verse needs a content word of the
question, the glossary's English equivalent is shown as source text, and «ما» opens a
question rather than a remark.

Record texts are synthetic placeholder words; only the brief's public inputs are real.
"""

import pytest

from api.composer import _content_overlap
from api.router import QuranRef
from tests.test_composer import claim, engine, proposal
from tests.test_freeze_live_cards import faq_titled, model_knobs, received
from tests.test_gatekeeper import local
from tests.test_twelve_cases import (
    GLOSSARY_RULE,
    Indexes,
    check,
    glossary_received,
    harness_client,
    route,
)

SWORD = "هل الإسلام انتشر بالسيف؟"
SEAL = "من هو خاتم الأنبياء؟"
TRANSLATE = "ترجم كلمة التوحيد إلى الإنجليزية"


@pytest.fixture(scope="module")
def harness():
    yield from harness_client()


def verse(cid, surah, ayah, text):
    record = local(text, cid)
    record["ref"] = {"surah": surah, "ayah": ayah}
    return record


# 1. A nominated verse is shown only when a content word of the question occurs in it.


@pytest.mark.parametrize(
    "question,record_text,expected",
    [
        (SWORD, "الم", False),  # «ألم» in a title or question never meets the one-word verse
        ("ألم ينتشر الإسلام بالسيف؟", "الم", False),
        (SEAL, "من كلمة", False),  # a function word is not overlap
        (SEAL, "خاتم كلمة", True),
        ("هل الإسلام انتشر بالسيف؟", "كلمة السيف كلمة", True),  # «بالسيف» meets «السيف»
        ("هل هو في البيت؟", "كلمة كلمة", False),  # no content word at all
    ],
)
def test_content_overlap_ignores_function_words_and_short_tokens(question, record_text, expected):
    assert _content_overlap((question,), record_text) is expected


def test_sword_question_shows_no_nominated_verse_that_only_matches_a_function_word():
    # The live case in synthetic form: the one-word nominated record equals a function
    # word of the question («من»); the record that shares a content word is shown.
    short = verse("quran:2:1", 2, 1, "من")
    seal = verse("quran:33:40", 33, 40, "خاتم كلمة")
    for cited, shown in (("quran:2:1", False), ("quran:33:40", True)):
        composer = engine(
            records=[short, seal], value=proposal(state="SUPPORTED", corpus_ids=[cited])
        )
        card = composer.compose(
            claim(SEAL, origin="question_subject"),
            original=SEAL,
            lang="ar",
            input_kind="question",
            no_checkable_claim=False,
            propose_state=True,
            quran_refs=[QuranRef(surah=2, ayah=1), QuranRef(surah=33, ayah=40)],
        )
        if shown:
            assert card["state"] == "SUPPORTED"
            assert [e["evidence_id"] for e in card["evidence"]] == ["quran:33:40"]
        else:
            assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []


def test_sword_question_over_http_shows_only_the_publisher_answer(harness):
    answer = faq_titled("ألم ينتشر الإسلام بالسيف؟")
    with received(answer), model_knobs(harness, cite=("faq", "quran")):
        card = check(
            harness,
            SWORD,
            route(SWORD, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    assert card["state"] == "SUPPORTED"
    assert [e["domain"] for e in card["evidence"]] == ["faq"]


# 2. The glossary's English equivalent is shown verbatim and validated as source text.


def test_tawhid_translation_shows_the_english_equivalent_five_times_in_a_row(harness):
    for _ in range(5):
        card = check(
            harness,
            TRANSLATE,
            route(TRANSLATE, kind="term", level="A", origin="term_lookup", no_claim=True),
            term_label="التوحيد",
        )
        assert card["state"] == "SUPPORTED" and card["gate_report"]["verbatim"] == "pass"
        assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
        assert card["term"]["term_ar"] == "التوحيد"
        assert card["term"]["term_en"] == "Synthetic equivalent"


def test_quoted_translation_item_is_shown_as_the_equivalent(harness):
    record = glossary_received("التوحيد", "", 808)
    del record["text_en"]
    record["translations"] = ['English: "Monotheism" (Tawhid)']
    original = Indexes.discover
    Indexes.discover = lambda self, text, request, *, kind, level, timeout: request.receive(record)
    try:
        card = check(
            harness,
            TRANSLATE,
            route(TRANSLATE, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    finally:
        Indexes.discover = original
    assert card["state"] == "SUPPORTED"
    assert card["term"]["term_en"] == 'English: "Monotheism" (Tawhid)'


def test_unattested_proposed_label_falls_back_to_the_publisher_term(harness):
    card = check(
        harness,
        TRANSLATE,
        route(TRANSLATE, kind="term", level="A", origin="term_lookup", no_claim=True),
        term_label="التَّوحيدُ الخالص",  # not the record's term and not in its definition
    )
    assert card["state"] == "SUPPORTED"
    assert card["term"]["term_ar"] == "التوحيد"
    assert card["term"]["term_en"] == "Synthetic equivalent"


def test_equivalent_carrying_record_text_still_fails_closed(harness):
    # Source text shown outside a quote block still passes the scripture scan: an
    # equivalent that quotes part of a loaded record is rejected (an excerpt is not an
    # authorized quote with its own reference).
    from tests.test_twelve_cases import VERSE_WORDS

    record = glossary_received("التوحيد", "English: «" + " ".join(VERSE_WORDS[2:9]) + "»", 909)
    original = Indexes.discover
    Indexes.discover = lambda self, text, request, *, kind, level, timeout: request.receive(record)
    try:
        card = check(
            harness,
            TRANSLATE,
            route(TRANSLATE, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    finally:
        Indexes.discover = original
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "VERBATIM_GATE_FAILED" and card["evidence"] == []


# Priority 2: an English term question reaches the glossary's publisher answer.


def test_english_term_question_matches_the_glossary_record_by_its_translation_item(harness):
    text = "What does Tawhid mean in Islam?"
    record = glossary_received("التوحيد", "", 1001)
    del record["text_en"]
    record["translations"] = ["English: Tawhid (monotheism)", "Français: Tawhid"]
    original = Indexes.discover
    Indexes.discover = lambda self, text, request, *, kind, level, timeout: request.receive(record)
    try:
        # Low model confidence: only a record that answers the question by itself survives.
        with model_knobs(harness, confidence=0.2):
            card = check(
                harness,
                text,
                route(text, kind="term", level="A", origin="term_lookup", lang="en", no_claim=True),
            )
    finally:
        Indexes.discover = original
    assert card["claim"]["lang"] == "en"
    assert card["state"] == "SUPPORTED"
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    assert card["explanation_en"]
