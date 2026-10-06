"""Evidence routing regressions using synthetic records and the public brief's question."""

import pytest

from api.router import QuranRef
from api.span_detector import Record
from tests import test_twelve_cases
from tests.test_composer import claim, engine, proposal
from tests.test_freeze_live_cards import faq_titled, model_knobs, received
from tests.test_gatekeeper import gate, local
from tests.test_span_detector import detector
from tests.test_twelve_cases import check, harness_client, route

QUESTION = "هل الإسلام انتشر بالسيف؟"
TITLE = "ألم ينتشر الإسلام بالسيف؟"


@pytest.mark.parametrize("opening", ["ألم", "أَلَمْ", "ا\u0654لم", "أ\u200dلم"])
def test_interrogative_is_not_an_unmarked_single_word_scripture_span(opening):
    scan = detector([Record("synthetic:short", "quran", "الم")]).detect(opening + " يصل القطار؟")
    assert scan.span_detector_status == "ran"
    assert scan.findings == ()


@pytest.mark.parametrize("text", ["الم", "اَلٓمٓ", "﴿الم﴾", "قال تعالى: الم"])
def test_actual_short_quote_remains_detectable(text):
    scan = detector([Record("synthetic:short", "quran", "الم")]).detect(text)
    assert scan.span_detector_status == "ran"
    assert any(f.match.classification == "VERBATIM" for f in scan.findings)


@pytest.mark.parametrize("field", ["title_ar", "text_ar"])
def test_publisher_prose_does_not_acquire_a_normalization_collision_dependency(field):
    answer = faq_titled(TITLE)
    if field == "text_ar":
        answer[field] = "ألم يصل القطار؟ نص تجريبي عن السفر."
    keeper = gate(answer, locals=[local("الم", "synthetic:short")])
    key = "live:bayyinat:" + answer["record_ref"]
    assert keeper.verify(key, answer["text_ar"]) is not None
    assert keeper.dependencies(key, answer["text_ar"]) == []
    published, dependencies = keeper.published_answer(key, answer["text_ar"])
    assert published["title_ar"] == answer["title_ar"]
    assert dependencies == []


def test_publisher_actual_short_quote_retains_its_source_dependency():
    answer = faq_titled("عنوان تجريبي")
    answer["text_ar"] = "نص تجريبي: ﴿الم﴾"
    keeper = gate(answer, locals=[local("الم", "synthetic:short")])
    key = "live:bayyinat:" + answer["record_ref"]
    assert keeper.verify(key, answer["text_ar"]) is not None
    assert [r["corpus_id"] for r in keeper.dependencies(key, answer["text_ar"])] == [
        "synthetic:short"
    ]


@pytest.mark.parametrize("confidence", [0.9, 0.2])
def test_http_publisher_answer_does_not_append_unrelated_short_verse(monkeypatch, confidence):
    short = local("الم", "quran:2:1")
    short["ref"] = {"surah": 2, "ayah": 1}
    monkeypatch.setattr(test_twelve_cases, "quran_record", lambda: short)
    for harness in harness_client():
        with received(faq_titled(TITLE)), model_knobs(harness, confidence=confidence):
            card = check(
                harness,
                QUESTION,
                route(QUESTION, kind="doubt", level="A", origin="question_subject"),
            )
        assert card["state"] == "SUPPORTED"
        assert [item["domain"] for item in card["evidence"]] == ["faq"]
        assert card["published_answer"]["title_ar"] == TITLE
        assert card["misquote_notice"] is None


@pytest.mark.parametrize("nominated", [False, True])
def test_scripture_candidate_needs_content_overlap_regardless_of_retrieval_path(nominated):
    question = "من يزرع التفاح؟"
    record = local("من", "quran:1:1")
    composer = engine(
        records=[record],
        value=proposal(state="SUPPORTED", corpus_ids=[record["corpus_id"]]),
    )
    card = composer.compose(
        claim(question, origin="question_subject"),
        original=question,
        lang="ar",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=1, ayah=1)] if nominated else [],
    )
    assert composer.model.calls  # The lexical hit was actually selected by the model.
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["evidence"] == []


@pytest.mark.parametrize("nominated", [False, True])
def test_rewritten_model_claim_cannot_supply_evidence_relevance(nominated):
    question = "هل يصل القطار؟"
    record = local("تفاحة برتقال موز", "quran:1:1")
    composer = engine(records=[record], value=proposal(state="SUPPORTED", corpus_ids=["quran:1:1"]))
    rewritten = claim(question, origin="presupposition").model_copy(
        update={"text_ar": "تفاحة برتقال موز"}
    )
    card = composer.compose(
        rewritten,
        original=question,
        lang="ar",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=1, ayah=1)] if nominated else [],
    )
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["evidence"] == []


@pytest.mark.parametrize("question", ["الم", "﴿الم﴾", "قال تعالى: الم"])
@pytest.mark.parametrize("nominated", [False, True])
def test_actual_complete_short_quote_survives_content_word_filter(question, nominated):
    record = local("الم", "quran:1:1")
    composer = engine(records=[record], value=proposal(state="SUPPORTED", corpus_ids=["quran:1:1"]))
    card = composer.compose(
        claim(question),
        original=question,
        lang="ar",
        input_kind="claim",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=1, ayah=1)] if nominated else [],
    )
    assert card["state"] == "SUPPORTED"
    assert [item["evidence_id"] for item in card["evidence"]] == [record["corpus_id"]]
