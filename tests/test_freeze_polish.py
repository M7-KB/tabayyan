"""Last fixes before the freeze: nominated verses need overlap, trailing remarks stay in
their question, and glossary cards pass the verbatim gate repeatably.

Record texts are synthetic placeholder words; only the brief's public inputs are real.
"""

import json
import logging

import pytest

from api.composer import SEPARATION_FALLBACK_TEXT
from api.router import QuranRef, _repair_proposal
from tests.test_freeze_live_cards import faq_titled, model_knobs, received
from tests.test_one_pass import route_proposal, service
from tests.test_twelve_cases import (
    FAQ_ANSWER,
    GLOSSARY_RULE,
    VERSE_WORDS,
    Indexes,
    check,
    glossary_received,
    harness_client,
    quotes_are_copied,
    route,
)


@pytest.fixture(scope="module")
def harness():
    yield from harness_client()


SWORD = "هل الإسلام انتشر بالسيف؟"
AUTHORSHIP = "هل القرآن من تأليف محمد ﷺ؟"
HOSTILE = "لماذا يمنع الإسلام الاجتهاد؟ هذا عبث!"
TERM = "ما معنى التوحيد؟"


# 2. An unrelated nominated verse is never shown.


@pytest.mark.parametrize(
    "item",
    [
        "البقرة:1",
        "2",
        "2:1-5",
        "2:",
        ":1",
        "",
        {"surah": 2},
        {"sura": 2, "aya": 1},
        None,
        2.1,
        [2, 1],
    ],
)
def test_unparseable_quran_refs_are_dropped_never_defaulted(item):
    value = route_proposal(SWORD, proposed_quran_refs=[item])
    assert _repair_proposal(SWORD, value).proposed_quran_refs == []
    value = route_proposal(SWORD, proposed_quran_refs=[item, "33:40"])
    assert _repair_proposal(SWORD, value).proposed_quran_refs == [QuranRef(surah=33, ayah=40)]


@pytest.mark.parametrize("text", [SWORD, AUTHORSHIP])
def test_cited_nomination_without_overlap_is_not_shown(harness, text):
    # The model cites both the Bayyinat answer and the nominated record; the record
    # shares no word with the question or the answer, so only the answer is shown.
    with received(faq_titled(text)), model_knobs(harness, cite=("faq", "quran")):
        card = check(
            harness,
            text,
            route(text, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    assert card["state"] == "SUPPORTED"
    assert [e["domain"] for e in card["evidence"]] == ["faq"]
    assert "quran:1:1" not in {e["evidence_id"] for e in card["evidence"]}
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    quotes_are_copied(card)


def test_cited_nomination_overlapping_the_publisher_answer_is_shown(harness):
    answer = faq_titled(SWORD)
    answer["text_ar"] = FAQ_ANSWER + " " + VERSE_WORDS[5]
    with received(answer), model_knobs(harness, cite=("faq", "quran")):
        card = check(
            harness,
            SWORD,
            route(SWORD, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    assert card["state"] == "SUPPORTED"
    assert {e["domain"] for e in card["evidence"]} == {"faq", "quran"}


def test_only_an_unrelated_nomination_cited_falls_back_to_the_matching_answer(harness):
    with received(faq_titled(SWORD)), model_knobs(harness, prefer=("quran",)):
        card = check(
            harness,
            SWORD,
            route(SWORD, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    assert card["state"] == "SUPPORTED"
    assert [e["domain"] for e in card["evidence"]] == ["faq"]
    assert card["explanation_ar"] == SEPARATION_FALLBACK_TEXT[0]


def test_only_an_unrelated_nomination_cited_abstains_without_a_matching_answer(harness):
    with received(), model_knobs(harness, prefer=("quran",)):
        card = check(
            harness,
            SWORD,
            route(SWORD, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []
    assert card["abstained_reason"] == "NO_MATCHING_EVIDENCE"


# 3. A trailing exclamation or insult stays in the question's claim.


def two_claims(text, first_origin, second_text, second_origin="stated"):
    cut = text.index(second_text)
    first = text[:cut].rstrip()
    return route_proposal(
        text,
        input_kind="doubt",
        claims=[
            {
                "text_ar": first,
                "source_text": first,
                "span": {"start": 0, "end": len(first)},
                "origin": first_origin,
            },
            {
                "text_ar": second_text,
                "source_text": second_text,
                "span": {"start": cut, "end": cut + len(second_text)},
                "origin": second_origin,
            },
        ],
    )


@pytest.mark.parametrize("first_origin", ["question_subject", "presupposition"])
def test_trailing_insult_stays_in_the_question_claim(first_origin):
    checker, _, _ = service(two_claims(HOSTILE, first_origin, "هذا عبث!"))
    routed = checker.router.route(HOSTILE)
    claims = routed.extracted.claims
    assert len(claims) == 1
    assert claims[0].origin == first_origin
    assert (claims[0].span.start, claims[0].span.end) == (0, len(HOSTILE))
    if first_origin == "question_subject":
        assert claims[0].text_ar == HOSTILE
    else:
        assert claims[0].text_ar == "لماذا يمنع الإسلام الاجتهاد؟"  # the premise key is kept


def test_trailing_exclamation_after_a_stated_claim_is_absorbed():
    text = "الاجتهاد ممنوع في الإسلام. هذا عبث!"
    checker, _, _ = service(two_claims(text, "stated", "هذا عبث!"))
    claims = checker.router.route(text).extracted.claims
    assert len(claims) == 1 and claims[0].text_ar == text


def test_a_second_question_or_a_long_remark_is_not_absorbed():
    second = "وهل يجوز الاجتهاد اليوم؟"
    text = "لماذا يمنع الإسلام الاجتهاد؟ " + second
    checker, _, _ = service(two_claims(text, "question_subject", second, "question_subject"))
    assert len(checker.router.route(text).extracted.claims) == 2
    remark = "هذا كلام طويل جداً لا يصح أن يقال في هذا المقام أبداً"
    text = "لماذا يمنع الإسلام الاجتهاد؟ " + remark
    checker, _, _ = service(two_claims(text, "question_subject", remark))
    assert len(checker.router.route(text).extracted.claims) == 2


def test_hostile_question_yields_one_card_over_http(harness):
    client, model = harness
    routed = two_claims(HOSTILE, "presupposition", "هذا عبث!")
    routed.update(level="B", level_d=False, premise=HOSTILE)
    model.route = routed
    response = client.post("/api/v1/check", json={"original_text": HOSTILE})
    assert response.status_code == 200
    cards = response.json()["cards"]
    assert len(cards) == 1
    assert cards[0]["claim"]["text_ar"] == HOSTILE
    assert "عبث" not in cards[0]["explanation_ar"]


# 4. Glossary cards pass the verbatim gate every time.


def test_glossary_question_passes_five_times_in_a_row(harness):
    for _ in range(5):
        card = check(
            harness,
            TERM,
            route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
            term_label="التوحيد",
        )
        assert card["state"] == "SUPPORTED"
        assert card["abstained_reason"] is None
        assert card["gate_report"]["verbatim"] == "pass"
        assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
        assert card["term"]["term_ar"] == "التوحيد"


@pytest.mark.parametrize("alias", ["strip_live", "url"])
def test_an_alias_of_an_offered_record_is_mapped_back_to_it(harness, alias):
    with model_knobs(harness, cite_alias=alias):
        card = check(
            harness,
            TERM,
            route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
            term_label="التوحيد",
        )
    assert card["state"] == "SUPPORTED" and card["gate_report"]["verbatim"] == "pass"
    assert [e["quote_ar"] for e in card["evidence"]] == [GLOSSARY_RULE]


@pytest.mark.parametrize("alias", ["invented", "duplicate"])
def test_an_id_naming_no_offered_record_still_fails_the_gate(harness, caplog, alias):
    with (
        caplog.at_level(logging.INFO, logger="api.diagnostics"),
        model_knobs(harness, cite_alias=alias),
    ):
        card = check(
            harness,
            TERM,
            route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "VERBATIM_GATE_FAILED" and card["evidence"] == []
    assert "verbatim:cited_ids" in caplog.text


def test_quoted_translation_item_is_not_selected_so_the_definition_still_shows(harness, caplog):
    record = glossary_received("التوحيد", "", 606)
    del record["text_en"]
    record["translations"] = ['English: "Monotheism"', "Français: Monothéisme"]
    original = Indexes.discover
    Indexes.discover = lambda self, text, request, *, kind, level, timeout: request.receive(record)
    try:
        with caplog.at_level(logging.INFO, logger="api.diagnostics"):
            card = check(
                harness,
                TERM,
                route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
                term_label="التوحيد",
            )
    finally:
        Indexes.discover = original
    # The quoted item never reaches the ordinary-text gate; the verified definition shows.
    assert card["state"] == "SUPPORTED" and card["gate_report"]["verbatim"] == "pass"
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    assert card["term"] is None
    assert "Monotheism" not in json.dumps(card, ensure_ascii=False)
    assert "term_block:quoted_item_skipped" in caplog.text


def test_quoted_text_en_still_fails_closed_and_is_named_in_the_log(harness, caplog):
    record = glossary_received("التوحيد", 'English: "Monotheism"', 707)
    original = Indexes.discover
    Indexes.discover = lambda self, text, request, *, kind, level, timeout: request.receive(record)
    try:
        with caplog.at_level(logging.INFO, logger="api.diagnostics"):
            card = check(
                harness,
                TERM,
                route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
                term_label="التوحيد",
            )
    finally:
        Indexes.discover = original
    # The gate is unchanged: a marked equivalent field fails the card. The request
    # summary now names the check that fired.
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "VERBATIM_GATE_FAILED" and card["evidence"] == []
    assert "verbatim:term_block" in caplog.text


def test_low_confidence_on_the_named_term_still_shows_its_definition(harness):
    with model_knobs(harness, confidence=0.2):
        card = check(
            harness,
            TERM,
            route(TERM, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    assert card["state"] == "SUPPORTED" and card["abstained_reason"] is None
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    assert card["explanation_ar"] == SEPARATION_FALLBACK_TEXT[0]
    assert card["term"] is None
    other = "ما معنى الزكاة؟"  # no received record names this term: the block stands
    with model_knobs(harness, confidence=0.2):
        card = check(
            harness,
            other,
            route(other, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []
