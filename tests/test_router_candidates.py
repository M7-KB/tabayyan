"""Question intent and nominated local lookup; evidence text is synthetic."""

import json

import pytest

from api.check import CheckRequest
from api.composer import COMPOSE_POOL
from api.diagnostics import Summary, summary
from api.router import QuranRef
from tests.test_composer import TEXT, claim, engine, proposal
from tests.test_composer import record as fixture_record
from tests.test_one_pass import route_proposal, service
from tests.test_quran_binding import paired


def quran_record():
    record = paired()
    record.update(corpus_id="quran:33:40", sura_no=33, aya_no=40, ref={"surah": 33, "ayah": 40})
    return record


def test_general_family_question_reaches_router_model_instead_of_rule_d():
    text = "التعاون مع أخي"
    checker, model, _ = service(route_proposal(text, input_kind="hadith"))
    route = checker.router.route(text)
    assert len(model.calls) == 1
    assert route.kind == "hadith"
    assert route.extracted.claims[0].level == "A"
    assert route.safe_to_search


def test_family_case_still_short_circuits_router_model():
    text = "عقد أخي"
    checker, model, _ = service(route_proposal(text, input_kind="hadith"))
    route = checker.router.route(text)
    assert model.calls == []
    assert route.extracted.claims[0].level == "D"
    assert not route.safe_to_search


def test_nominated_33_40_reaches_candidates_but_needs_overlap_to_be_shown():
    record = quran_record()
    for question, shown in (("من هو خاتم الأنبياء؟", False), ("من هو خاتم الأنبياء تفاحة؟", True)):
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
        # The nomination always reaches the model, ahead of lexical hits.
        sent = json.loads(composer.model.calls[0]["data"]["records"])
        assert sent[0]["corpus_id"] == "quran:33:40"
        card = result["cards"][0]
        if shown:
            assert card["state"] == "SUPPORTED" and card["alignment"] == "CONFIRMS"
            assert card["evidence"][0]["quote_ar"] == record["aya_text_unicode"]
            assert card["evidence"][0]["retrieval_score"] > 0
        else:
            # A cited nomination with no word in common with the question is not evidence.
            assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []


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


def test_multiple_complete_questions_retain_their_own_context():
    questions = [
        "If not ripe, is eating fruit allowed? Only when stored safely.",
        "If not fresh, is storing fruit allowed? Only when sealed.",
    ]
    text = " ".join(questions)
    routed = route_proposal(text)
    routed["claims"] = []
    for question in questions:
        start = text.index(question)
        routed["claims"].append(
            {
                "text_ar": "narrow interpretation",
                "source_text": question,
                "origin": "question_subject",
                "span": {"start": start, "end": start + len(question)},
            }
        )
    checker, _, _ = service(routed)
    claims = checker.router.route(text).extracted.claims
    assert [claim.text_ar for claim in claims] == questions
    assert [text[c.span.start : c.span.end] for c in claims] == questions


@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.parametrize(
    "question,subject",
    [
        ("Is storing fruit allowed? Only if it is not fresh.", "storing fruit"),
        ("هل يجوز الصلاة متأخراً؟ أقصد إذا كان هناك عذر.", "الصلاة متأخراً"),
        ("Is storing fruit allowed?\nOnly if it is not fresh.", "storing fruit"),
    ],
)
def test_trailing_conditions_survive_narrow_and_complete_spans(question, subject, complete):
    source = question if complete else subject
    start = question.index(source)
    routed = route_proposal(question)
    routed["claims"][0].update(
        origin="question_subject",
        text_ar=subject,
        source_text=source,
        span={"start": start, "end": start + len(source)},
    )
    checker, _, _ = service(routed)
    claim = checker.router.route(question).extracted.claims[0]
    assert claim.text_ar == question
    assert question[claim.span.start : claim.span.end] == question


@pytest.mark.parametrize("subjects_only", [False, True])
def test_multiple_questions_fail_closed_when_context_is_omitted(subjects_only):
    questions = [
        "Is eating fruit allowed? Only when stored safely.",
        "Is storing fruit allowed? Only when sealed.",
    ]
    text = " ".join(questions)
    sources = (
        ["eating fruit", "storing fruit"]
        if subjects_only
        else [q.split("?")[0] + "?" for q in questions]
    )
    routed = route_proposal(text)
    routed["claims"] = []
    for source in sources:
        start = text.index(source)
        routed["claims"].append(
            {
                "text_ar": source,
                "source_text": source,
                "origin": "question_subject",
                "span": {"start": start, "end": start + len(source)},
            }
        )
    checker, _, composer = service(routed)
    result = checker.check(CheckRequest(original_text=text))
    # Omitted context never drops the request: the whole input becomes one
    # claim, so both questions and their conditions survive to the gates.
    assert len(result["cards"]) == 1
    assert result["cards"][0]["claim"]["text_ar"] == text


def test_nominated_ref_survives_compose_pool_and_counts_stay_text_free():
    question = "من هو خاتم الأنبياء؟"
    lexical = [
        fixture_record(f"fixture:l{i}", domain="quran", text=f"خاتم عينة {i}") for i in range(6)
    ]
    composer = engine(
        records=[quran_record(), *lexical],
        value=proposal(state="SUPPORTED", corpus_ids=["quran:33:40"]),
    )
    metrics = Summary()
    token = summary.set(metrics)
    try:
        result = composer.compose(
            claim(question, origin="question_subject"),
            original=question,
            lang="ar",
            input_kind="question",
            no_checkable_claim=False,
            propose_state=True,
            quran_refs=[QuranRef(surah=33, ayah=40)],
        )
    finally:
        summary.reset(token)
    sent = [r["corpus_id"] for r in json.loads(composer.model.calls[0]["data"]["records"])]
    assert "quran:33:40" in sent
    assert len(sent) <= COMPOSE_POOL + 1
    assert metrics.counts["resolved_refs"] == 1
    assert metrics.counts["lexical_hits_capped"] >= COMPOSE_POOL
    assert metrics.counts["compose_candidates"] == len(sent)
    assert result["state"] in {"SUPPORTED", "DISPUTED", "CANNOT_CONFIRM"}
