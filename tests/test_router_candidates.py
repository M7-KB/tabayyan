"""Question intent and nominated local lookup; evidence text is synthetic."""

import json

import pytest

from api.check import CheckRequest
from api.router import QuranRef
from tests.test_composer import TEXT, claim, engine, proposal
from tests.test_one_pass import route_proposal, service
from tests.test_quran_binding import paired


def quran_record():
    record = paired()
    record.update(corpus_id="quran:33:40", sura_no=33, aya_no=40, ref={"surah": 33, "ayah": 40})
    return record


def test_nominated_33_40_reaches_candidates_without_lexical_overlap():
    question = "من هو خاتم الأنبياء؟"
    record = quran_record()
    composer = engine(
        records=[record], value=proposal(state="SUPPORTED", corpus_ids=["quran:33:40"])
    )
    routed = route_proposal(
        question, input_kind="verse", proposed_quran_refs=[{"surah": 33, "ayah": 40}]
    )
    routed["claims"][0]["origin"] = "question_subject"
    checker, _, _ = service(routed)
    checker.composer = composer
    result = checker.check(CheckRequest(original_text=question))
    sent = json.loads(composer.model.calls[0]["data"]["records"])
    assert sent[0]["corpus_id"] == "quran:33:40"
    assert result["cards"][0]["state"] == "CANNOT_CONFIRM"
    assert result["cards"][0]["abstained_reason"] == "ALIGNMENT_UNDETERMINED"
    assert result["cards"][0]["evidence"][0]["quote_ar"] == record["aya_text_unicode"]
    assert result["cards"][0]["evidence"][0]["retrieval_score"] == 0


def test_nominated_reference_keeps_measured_overlap_and_allows_supported():
    record = quran_record()
    question = "Which " + TEXT + "?"
    composer = engine(
        records=[record], value=proposal(state="SUPPORTED", corpus_ids=["quran:33:40"])
    )
    result = composer.compose(
        claim(question, origin="question_subject"),
        original=question,
        lang="en",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=33, ayah=40)],
    )
    assert result["state"] == "SUPPORTED"
    assert result["evidence"][0]["quote_ar"] == record["aya_text_unicode"]


@pytest.mark.parametrize("mutation", ["missing", "wrong_source", "wrong_ref", "low_confidence"])
def test_nomination_cannot_bypass_source_or_decision_gates(mutation):
    record = quran_record()
    if mutation == "wrong_source":
        record["source_id"] = "synthetic"
        for key in ("aya_text_emlaey", "aya_text_unicode", "checksum_unicode_sha256"):
            record.pop(key)
    if mutation == "wrong_ref":
        record["ref"] = {"surah": 1, "ayah": 1}
        for key in ("aya_text_emlaey", "aya_text_unicode", "checksum_unicode_sha256"):
            record.pop(key)
    composer = engine(
        records=[record],
        value=proposal(
            state="SUPPORTED",
            corpus_ids=["quran:33:40"],
            confidence=0.1 if mutation == "low_confidence" else 0.9,
        ),
    )
    question = "Unrelated synthetic question?"
    result = composer.compose(
        claim(question, origin="question_subject"),
        original=question,
        lang="en",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=33, ayah=41 if mutation == "missing" else 40)],
    )
    assert result["state"] == "CANNOT_CONFIRM"
    assert result["evidence"] == []


def test_permission_question_keeps_original_intent_and_referral_question():
    question = "هل يجوز الصلاة متأخراً؟"
    routed = route_proposal(question)
    routed["claims"][0].update(origin="question_subject", text_ar="الصلاة متأخرة")
    checker, _, _ = service(routed)
    result = checker.check(CheckRequest(original_text=question))
    card = result["cards"][0]
    assert card["claim"]["text_ar"] == question
    assert card["referral"]["ready_to_ask_question_ar"] == "سؤالي: " + question


def test_level_d_keeps_user_question_and_skips_nominated_retrieval():
    question = "Can I change my marriage contract?"
    checker, _, model = service(
        route_proposal(question, proposed_quran_refs=[{"surah": 33, "ayah": 40}])
    )
    result = checker.check(CheckRequest(original_text=question))
    assert not model.calls
    assert result["cards"][0]["state"] == "CANNOT_CONFIRM"
    assert question in result["cards"][0]["referral"]["ready_to_ask_question_ar"]


def test_assertions_keep_stated_wording():
    checker, _, _ = service(route_proposal(TEXT))
    assert checker.router.route(TEXT).extracted.claims[0].text_ar == TEXT


@pytest.mark.parametrize(
    "question",
    [
        "هل يجوز الصلاة متأخراً؟",
        "هل لا يجوز الصلاة متأخراً؟",
        "إذا تأخرت، هل يجوز الصلاة متأخراً؟",
        "إذا تأخرت\nهل يجوز الصلاة متأخراً؟",
    ],
)
def test_narrow_subject_span_restores_permission_negation_and_conditions(question):
    subject = "الصلاة متأخراً"
    start = question.index(subject)
    routed = route_proposal(question)
    routed["claims"][0].update(
        origin="question_subject",
        text_ar=subject,
        source_text=subject,
        span={"start": start, "end": start + len(subject)},
    )
    checker, _, _ = service(routed)
    claim = checker.router.route(question).extracted.claims[0]
    assert claim.text_ar == question
    assert question[claim.span.start : claim.span.end] == question


def test_multiple_narrowed_questions_retain_their_own_complete_context():
    questions = ["If not ripe, is eating fruit allowed?", "If not fresh, is storing fruit allowed?"]
    text = " ".join(questions)
    routed = route_proposal(text)
    routed["claims"] = []
    for subject in ("eating fruit", "storing fruit"):
        start = text.index(subject)
        routed["claims"].append(
            {
                "text_ar": subject,
                "source_text": subject,
                "origin": "question_subject",
                "span": {"start": start, "end": start + len(subject)},
            }
        )
    checker, _, _ = service(routed)
    claims = checker.router.route(text).extracted.claims
    assert [claim.text_ar for claim in claims] == questions
    assert [text[c.span.start : c.span.end] for c in claims] == questions
