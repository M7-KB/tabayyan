"""Live-card fixes before the freeze: one state per card, Bayyinat display and labels,
Quran nominations, the publisher-answer fallback, complete questions, and the CPU cost
of long publisher answers.

Every record text here is synthetic placeholder text; the only real strings are the
brief's public test inputs. No scripture, hadith, grading or definition is written.
"""

import copy
import json
import logging
import re
from contextlib import contextmanager

import pytest
from jsonschema import ValidationError

from api.bayyinat_matcher import EXCERPT_LIMIT, BayyinatMatcher, first_paragraph
from api.composer import ABSTENTION_TEXT, SEPARATION_FALLBACK_TEXT, VALIDATOR, _title_matches
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.private_short_discovery import PrivateShortDiscovery
from api.router import QuranRef, _repair_proposal
from api.span_detector import DetectorConfig
from tests.test_composer import POLICY, TUNING
from tests.test_gatekeeper import gate, local, raw
from tests.test_one_pass import route_proposal, service
from tests.test_private_index_matchers import FakeEmbedder, vector
from tests.test_private_v2_wiring import row
from tests.test_twelve_cases import (
    FAQ_ANSWER,
    Indexes,
    check,
    faq_received,
    harness_client,
    quotes_are_copied,
    route,
)


@pytest.fixture(scope="module")
def harness():
    yield from harness_client()


KAABA = "لماذا يعبد المسلمون الكعبة؟"
SEAL = "من هو خاتم الأنبياء؟"
ASR = "حكم ترك صلاة العصر؟"
UNSPECIFIED = "هل كل المسلمين يتفقون في هذه المسألة؟"


@contextmanager
def received(*records):
    """The private index returns exactly these records for a doubt question."""
    original = Indexes.discover

    def discover(self, text, request, *, kind, level, timeout):
        if level != "D" and kind == "doubt":
            for record in records:
                request.receive(copy.deepcopy(record))

    Indexes.discover = discover
    try:
        yield
    finally:
        Indexes.discover = original


@contextmanager
def model_knobs(harness, **knobs):
    _, model = harness
    saved = {name: getattr(model, name) for name in knobs}
    for name, value in knobs.items():
        setattr(model, name, value)
    try:
        yield model
    finally:
        for name, value in saved.items():
            setattr(model, name, value)


def faq_titled(title):
    record = faq_received()
    record["title_ar"] = title
    record["ref"] = {"label": title}
    return record


def abstains_without_evidence(card, reason):
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == reason
    assert card["evidence"] == [] and card["positions"] == []
    assert card.get("published_answer") is None
    assert card["referral"]


# 1. One state per card: an abstaining card displays no evidence block.


def test_model_cannot_confirm_without_publisher_record_shows_no_evidence(harness):
    # Only a nominated scripture record is offered; the model abstains on it.
    with received(), model_knobs(harness, prefer=("quran",)):
        card = check(
            harness,
            KAABA,
            route(KAABA, kind="doubt", level="A", origin="presupposition", refs=[(1, 1)]),
            state="CANNOT_CONFIRM",
            alignment=None,
            alignment_confidence=0.0,
        )
    abstains_without_evidence(card, "NO_MATCHING_EVIDENCE")


def test_low_confidence_without_title_match_shows_no_evidence(harness):
    with received(faq_titled("هل الإسلام انتشر بالسيف؟")), model_knobs(harness, confidence=0.2):
        card = check(harness, KAABA, route(KAABA, kind="doubt", level="A", origin="presupposition"))
    abstains_without_evidence(card, "LOW_CONFIDENCE")
    assert card["explanation_ar"] == ABSTENTION_TEXT["default"][0]


def test_state_rules_abstention_clears_selected_evidence(harness):
    # Level C with scripture alone: the policy's state rules abstain after the model
    # selected a record. The card used to keep that record while CANNOT_CONFIRM.
    text = "هل الإسلام انتشر بالسيف؟"
    with received(), model_knobs(harness, prefer=("quran",)):
        card = check(
            harness,
            text,
            route(text, kind="doubt", level="C", origin="question_subject", refs=[(1, 1)]),
        )
    abstains_without_evidence(card, "CONFLICTING_EVIDENCE")


def test_alignment_undetermined_clears_selected_evidence(harness):
    text = "هل القرآن من تأليف محمد ﷺ؟"
    with received(), model_knobs(harness, prefer=("quran",)):
        card = check(
            harness,
            text,
            route(text, kind="doubt", level="A", origin="presupposition", refs=[(1, 1)]),
            alignment=None,
            alignment_confidence=0.0,
        )
    abstains_without_evidence(card, "ALIGNMENT_UNDETERMINED")


def test_card_contract_rejects_evidence_on_an_abstaining_card(harness):
    text = "هل الإسلام انتشر بالسيف؟"
    card = check(harness, text, route(text, kind="doubt", level="A", origin="question_subject"))
    assert card["state"] == "SUPPORTED" and card["evidence"]
    broken = {
        **card,
        "state": "CANNOT_CONFIRM",
        "alignment": None,
        "state_label_key": "cannot_confirm",
        "abstained_reason": "LOW_CONFIDENCE",
        "positions": [],
        "published_answer": None,
        "referral": {
            "body_name_ar": "جهة تجريبية",
            "body_url": "https://example.invalid/referral",
            "fallback_line_ar": "سطر تجريبي",
            "ready_to_ask_question_ar": "سؤال تجريبي",
        },
    }
    with pytest.raises(ValidationError):
        VALIDATOR.validate(broken)
    with pytest.raises(ValidationError):
        VALIDATOR.validate({**broken, "evidence": [], "published_answer": card["published_answer"]})
    VALIDATOR.validate({**broken, "evidence": []})


# 2. Bayyinat display text: no label line, stops before the references, sentence cap.


def test_first_paragraph_skips_the_section_label_line():
    body = "جملة تجريبية أولى. جملة تجريبية ثانية."
    assert first_paragraph("الجواب التفصيلي\n" + body) == body
    assert first_paragraph("الجواب التفصيلي:\n\n" + body + "\n\nفقرة تالية") == body
    assert first_paragraph("الجواب التفصيلي: " + body) == body
    assert first_paragraph("الخلاصة:\nالجواب\n" + body) == body


def test_first_paragraph_stops_before_references_and_verse_index():
    body = "جملة تجريبية أولى."
    assert first_paragraph(body + "\nالمراجع\n1- مرجع تجريبي") == body
    assert first_paragraph(body + " المراجع (*) مرجع تجريبي") == body
    assert first_paragraph(body + "\nالآيات التي وردت في الجواب\n2:1") == body
    # A word that merely contains the marker is ordinary text.
    review = "هذه المراجعة تجريبية."
    assert first_paragraph(review) == review


def test_first_paragraph_caps_on_a_sentence_boundary():
    sentence = "جملة تجريبية طويلة بعض الشيء تنتهي هنا."
    text = " ".join([sentence] * 20)
    excerpt = first_paragraph(text)
    assert len(excerpt) <= EXCERPT_LIMIT
    assert excerpt.endswith(".") and text.startswith(excerpt)
    assert excerpt == " ".join([sentence] * (EXCERPT_LIMIT // (len(sentence) + 1)))


def test_display_text_prefers_the_summary_and_never_pads():
    record = row()
    record["summary"] = ""
    record["detailed_answer"] = "الجواب التفصيلي\nفقرة تجريبية.\n\nالمراجع\nمرجع"
    assert BayyinatMatcher.display_text(record) == "فقرة تجريبية."
    record["summary"] = "خلاصة تجريبية"
    assert BayyinatMatcher.display_text(record) == "خلاصة تجريبية"
    assert "…" not in first_paragraph("كلمة " * 200)


# 3. Source labels: «source: question title» for Bayyinat, «source: term» for glossary.


def test_received_records_are_labelled_by_title_or_term():
    bayyinat = row()
    glossary = row("jamhara-glossary")
    request = SourceRequest()
    PrivateShortDiscovery(
        bayyinat=BayyinatMatcher((bayyinat,), [vector()], FakeEmbedder())
    ).discover("مكتب", request, kind="doubt", level="B", timeout=1)
    gatekeeper = QuoteGatekeeper(
        local_records=[local()],
        request=request,
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    verified = gatekeeper.verify("live:bayyinat:" + bayyinat["id"], bayyinat["summary"])
    assert verified["ref"] == {"label": bayyinat["title"]}
    assert verified["source_ref"]["url"] == bayyinat["url"]

    from api.glossary_matcher import GlossaryMatcher

    request = SourceRequest()
    PrivateShortDiscovery(
        glossary=GlossaryMatcher((glossary,), [vector()], FakeEmbedder())
    ).discover("مكتب", request, kind="term", level="A", timeout=1)
    gatekeeper = QuoteGatekeeper(
        local_records=[local()],
        request=request,
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    key = "live:jamhara-glossary:" + glossary["id"]
    verified = gatekeeper.verify(key, GlossaryMatcher.display_text(glossary))
    assert verified["ref"] == {"label": glossary["term_ar"]}


# 4. Quran nominations: string refs are repaired and a nominated ayah reaches the card.


def test_string_quran_refs_are_accepted_as_lookup_keys():
    text = SEAL
    value = route_proposal(
        text, proposed_quran_refs=["33:40", " 1 : 1 ", {"surah": 2, "ayah": 255}]
    )
    value["claims"][0]["origin"] = "question_subject"
    repaired = _repair_proposal(text, value)
    assert [(r.surah, r.ayah) for r in repaired.proposed_quran_refs] == [(33, 40), (1, 1), (2, 255)]
    value["proposed_quran_refs"] = ["33-40", "ayah", "33:40"]
    repaired = _repair_proposal(text, value)
    assert repaired.proposed_quran_refs == [QuranRef(surah=33, ayah=40)]


def test_nominated_ayah_reaches_the_card_for_the_seal_question(harness, caplog):
    with (
        caplog.at_level(logging.INFO, logger="api.diagnostics"),
        received(),
        model_knobs(harness, prefer=("quran",)),
    ):
        card = check(
            harness,
            SEAL,
            route(SEAL, kind="doubt", level="A", origin="question_subject", refs=[(1, 1)]),
        )
    _, model = harness
    # The request summary counts the nomination and its resolution (text-free counters).
    counts = re.search(r"counts=(\{[^}]*\})", caplog.text).group(1)
    assert "'proposed_refs': 1" in counts and "'resolved_refs': 1" in counts
    # The nominated record is offered first, without lexical overlap with the question.
    assert model.records_seen[-1][0] == "quran:1:1"
    assert card["state"] == "SUPPORTED"
    assert [e["evidence_id"] for e in card["evidence"]] == ["quran:1:1"]
    quotes_are_copied(card)


# 5. A Bayyinat record whose title matches the question is not blocked by model confidence.


@pytest.mark.parametrize(
    "question,title,expected",
    [
        (KAABA, "هل يعبد المسلمون الكعبة؟", True),
        (KAABA, "شبهة عبادة المسلمين للكعبة", True),
        (KAABA, "هل الإسلام انتشر بالسيف؟", False),
        ("هل الإسلام انتشر بالسيف؟", "شبهة انتشار الإسلام بالسيف", True),
        ("ما حكم ترك صلاة العصر؟", "فضل صلاة الفجر", False),
        ("لماذا؟", "لماذا؟", False),
        (KAABA, "", False),
    ],
)
def test_title_match_counts_content_words_only(question, title, expected):
    assert _title_matches(question, {"title_ar": title}) is expected


def test_low_confidence_with_matching_title_shows_the_publisher_answer(harness):
    with received(faq_titled("هل يعبد المسلمون الكعبة؟")), model_knobs(harness, confidence=0.2):
        card = check(
            harness,
            KAABA,
            route(KAABA, kind="doubt", level="A", origin="presupposition"),
            alignment="CONTRADICTS",
        )
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"
    assert card["abstained_reason"] is None and card["referral"] is None
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    assert card["published_answer"]["title_ar"] == "هل يعبد المسلمون الكعبة؟"
    assert card["evidence"][0]["ref"] == {"label": "هل يعبد المسلمون الكعبة؟"}
    # No generated prose stands on the low-confidence proposal.
    assert card["explanation_ar"] == SEPARATION_FALLBACK_TEXT[0]
    quotes_are_copied(card)


@pytest.mark.parametrize("knob", ["evidence_gap", "state", "error", "level_c_rules"])
def test_every_confidence_block_yields_to_a_matching_title(harness, knob):
    knobs = {
        "evidence_gap": {"evidence_gap": True},
        "state": {"state": "CANNOT_CONFIRM", "prefer": ("quran",)},
        "error": {"error": RuntimeError("provider failed")},
        "level_c_rules": {"prefer": ("quran",)},
    }[knob]
    level = "C" if knob == "level_c_rules" else "A"
    # A nominated scripture record is offered beside the Bayyinat answer, so the
    # model can select it and abstain, or leave level C with scripture alone.
    with received(faq_titled("هل يعبد المسلمون الكعبة؟")), model_knobs(harness, **knobs):
        card = check(
            harness,
            KAABA,
            route(KAABA, kind="doubt", level=level, origin="presupposition", refs=[(1, 1)]),
            alignment="CONTRADICTS",
            state=knobs.get("state", "SUPPORTED"),
        )
    assert card["state"] == "SUPPORTED"
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    assert [e["domain"] for e in card["evidence"]] == ["faq"]
    assert card["explanation_ar"] == SEPARATION_FALLBACK_TEXT[0]
    quotes_are_copied(card)


def test_low_confidence_keeps_the_block_when_no_title_matches(harness):
    with received(faq_titled("هل الإسلام انتشر بالسيف؟")), model_knobs(harness, confidence=0.2):
        card = check(harness, KAABA, route(KAABA, kind="doubt", level="A", origin="presupposition"))
    abstains_without_evidence(card, "LOW_CONFIDENCE")


# 6. A complete question is never the "unspecified matter".


@pytest.mark.parametrize(
    "text,no_claim", [(ASR, False), (UNSPECIFIED, True), ("ما حكم كذا؟", True)]
)
def test_router_keeps_no_checkable_claim_only_for_placeholder_subjects(text, no_claim):
    value = route_proposal(text, input_kind="other")
    value["claims"][0]["origin"] = "term_lookup"
    checker, _, _ = service(value)
    routed = checker.router.route(text)
    assert routed.extracted.no_checkable_claim is no_claim
    assert routed.extracted.claims[0].origin == ("term_lookup" if no_claim else "question_subject")


def test_complete_question_never_gets_the_unspecified_matter_text(harness):
    card = check(
        harness, ASR, route(ASR, kind="other", level="A", origin="question_subject", no_claim=True)
    )
    assert card["abstained_reason"] != "NO_CHECKABLE_CLAIM"
    assert card["explanation_ar"] != ABSTENTION_TEXT["NO_CHECKABLE_CLAIM"][0]
    unspecified = check(
        harness,
        UNSPECIFIED,
        route(UNSPECIFIED, kind="other", level="C", origin="question_subject", no_claim=True),
    )
    assert unspecified["abstained_reason"] == "NO_CHECKABLE_CLAIM"


# 7. The scripture scan of one displayed excerpt runs once per request.


def test_embedded_scan_of_the_same_excerpt_runs_once():
    record = raw()
    g = gate(record)
    scanned = []
    original = g.scan_scripture

    def counting(text):
        scanned.append(text)
        return original(text)

    g.scan_scripture = counting
    key = "live:islamqa:one"
    assert g.verify(key, record["text_ar"]) is not None
    assert g.dependencies(key, record["text_ar"]) == []
    published, _ = g.published_answer(key, record["text_ar"])
    assert published["excerpt_ar"] == record["text_ar"]
    assert scanned.count(record["text_ar"]) == 1
    assert scanned.count(record["title_ar"]) == 1
    # The cached result is a copy: callers cannot alter what the next caller sees.
    first = g._embedded(record["text_ar"])
    first.append({"corpus_id": "forged"})
    assert g._embedded(record["text_ar"]) == []


def test_bayyinat_card_scans_the_excerpt_once_through_the_composer(harness):
    client, model = harness
    scans = []
    composer = client.app.state.checker.composer
    original = QuoteGatekeeper.scan_scripture

    def counting(self, text):
        scans.append(text)
        return original(self, text)

    QuoteGatekeeper.scan_scripture = counting
    try:
        card = check(harness, KAABA, route(KAABA, kind="doubt", level="A", origin="presupposition"))
    finally:
        QuoteGatekeeper.scan_scripture = original
    assert composer is client.app.state.checker.composer
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    assert scans.count(FAQ_ANSWER) == 1
    assert json.dumps(card, ensure_ascii=False).count(FAQ_ANSWER) == 2  # evidence + published block
