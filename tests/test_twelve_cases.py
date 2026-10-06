"""End-to-end behaviour for the twelve brief cases over the HTTP check path.

Synthetic records and a scripted model drive every code path deterministically.
No scripture, hadith text, grading or definition is written here: record texts are
placeholder words, and the only real strings are the brief's public test inputs.
What each case asserts is the behaviour the brief expects (state, alignment,
referral, explanation, term, evidence source) and the invariant that every quote
on a card is copied from a loaded record.
"""

import copy
import json

import pytest
from fastapi.testclient import TestClient

from api.classifier import LevelClassifier
from api.composer import (
    ABSTENTION_TEXT,
    CORRECTION_TEXT,
    EXPLANATION_SENTENCES,
    LEVEL_D_TEXT,
    VALIDATOR,
    Composer,
)
from api.config import load_config
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.main import create_app
from api.one_pass import OnePassCheckService
from api.retrieval import BM25Retriever
from api.router import Router
from api.settings import Settings
from api.span_detector import DetectorConfig
from corpus.normalize import normalize_arabic

POLICY = __import__("tests.test_composer", fromlist=["POLICY"]).POLICY
TUNING = __import__("tests.test_composer", fromlist=["TUNING"]).TUNING

# Synthetic "verse": seventeen placeholder tokens; the altered-excerpt input below
# quotes five of them with the last one changed.
VERSE_WORDS = [f"كلمة{i}" for i in range(17)]
HADITH_WORDS = [f"رواية{i}" for i in range(9)]
FAQ_ANSWER = "جواب تجريبي منشور عن المسألة المطروحة في مصدر الشبهات."
GLOSSARY_RULE = "تعريف تجريبي للمصطلح من قاموس تجريبي."
EXPLANATION = "جملة تجريبية أولى. جملة تجريبية ثانية. جملة تجريبية ثالثة. جملة تجريبية رابعة."
EXPLANATION_EN = "First test sentence. Second test sentence. Third one. Fourth one."
FORBIDDEN_HADITH_MARKERS = (
    "قال رسول الله",
    "قال النبي",
    "رواه البخاري",
    "رواه مسلم",
    "درجة الحديث: صحيح",
    "إسناده صحيح",
)


def quran_record():
    text = " ".join(VERSE_WORDS)
    return {
        "corpus_id": "quran:1:1",
        "domain": "quran",
        "source_id": "kfc-mushaf",
        "source_name_ar": "مصدر تجريبي",
        "source_url": "https://example.invalid/quran/1/1",
        "text_ar": text,
        "text_normalized": normalize_arabic(text),
        "ref": {"surah": 1, "ayah": 1},
    }


def hadith_record():
    text = " ".join(HADITH_WORDS)
    url = "https://example.invalid/hadith/7"
    return {
        "corpus_id": "hadeethenc:7",
        "domain": "hadith",
        "source_id": "hadeethenc",
        "source_name_ar": "مصدر تجريبي",
        "source_url": url,
        "text_ar": text,
        "text_normalized": normalize_arabic(text),
        "ref": {"collection": "c", "number": "7", "attribution": "a"},
        "grading": {"grade_ar": "صحيح", "grader_ar": "اختبار", "grading_source_url": url},
    }


def faq_received():
    return {
        "domain": "faq",
        "title_ar": "عنوان تجريبي",
        "source_id": "bayyinat",
        "record_ref": "/question/1",
        "source_url": "https://bayenat.net/question/1",
        "text_ar": FAQ_ANSWER,
        "ref": {"label": "/question/1"},
    }


def glossary_received(term_ar, term_en, ref):
    return {
        "domain": "glossary",
        "term_ar": term_ar,
        "text_en": term_en,
        "source_id": "jamhara-glossary",
        "record_ref": f"/dictionary/word/{ref}",
        "source_url": f"https://islamic-content.com/dictionary/word/{ref}",
        "text_ar": GLOSSARY_RULE,
        "ref": {"label": f"/dictionary/word/{ref}"},
    }


class Indexes:
    """Stands in for the owner's private Bayyinat and glossary indexes."""

    def discover(self, text, request, *, kind, level, timeout):
        if level == "D":
            return
        if kind == "doubt":
            request.receive(faq_received())
        elif kind == "term":
            request.receive(glossary_received("التوحيد", "Synthetic equivalent", 101))
            request.receive(glossary_received("الشريعة", "Sharia", 202))


class Scripted:
    """Returns the routing and composition a capable model would for one case."""

    def __init__(self):
        self.route = None
        self.alignment = "CONFIRMS"
        self.alignment_confidence = 0.9
        self.state = "SUPPORTED"
        self.prefer = ("faq", "glossary", "quran", "hadith")
        self.term_label = None
        self.calls = []

    def complete_json(self, *, instructions, data, schema):
        self.calls.append(schema)
        fields = schema.get("properties", {})
        if "search_queries" in fields:
            return copy.deepcopy(self.route)
        if "meaning" in fields:
            return {"corpus_id": None, "meaning": "no", "confidence": 0.9}
        records = json.loads(data["records"])
        chosen = next(
            (r for domain in self.prefer for r in records if r["domain"] == domain), records[0]
        )
        return {
            "state": self.state,
            "corpus_ids": [chosen["corpus_id"]],
            "positions": [],
            "recorded_disagreement": False,
            "evidence_gap": False,
            "alignment_proposal": self.alignment,
            "alignment_confidence": self.alignment_confidence,
            "confidence": 0.9,
            "explanation_ar": EXPLANATION,
            "explanation_en": EXPLANATION_EN,
            "term_label_ar": self.term_label,
        }


def route(text, *, kind, level, origin, lang="ar", refs=(), phrases=(), no_claim=False):
    return {
        "detected_lang": lang,
        "level": level,
        "level_confidence": 0.95,
        "level_d": level == "D",
        "premise": text,
        "input_kind": kind,
        "search_queries": [],
        "safe_to_search": False,
        "proposed_quran_refs": [{"surah": s, "ayah": a} for s, a in refs],
        "proposed_hadith_phrases": list(phrases),
        "claims": [
            {
                "text_ar": text,
                "source_text": text,
                "span": {"start": 0, "end": len(text)},
                "origin": "term_lookup" if no_claim else origin,
            }
        ],
    }


@pytest.fixture(scope="module")
def harness():
    _, tuning = load_config(POLICY, TUNING)
    gatekeeper = QuoteGatekeeper(
        local_records=[quran_record(), hadith_record()],
        request=SourceRequest(),
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    model = Scripted()
    records = gatekeeper.records
    composer = Composer(
        model=model,
        retriever=BM25Retriever(records, tuning),
        detector=gatekeeper.detector,
        records=records,
        policy_path=POLICY,
        tuning_path=TUNING,
        gatekeeper=gatekeeper,
        local_hadith=True,
    )
    router = Router(
        model=model,
        classifier=LevelClassifier(model=None, policy_path=POLICY, tuning_path=TUNING),
        detector=gatekeeper.detector,
    )
    service = OnePassCheckService(
        router=router,
        composer=composer,
        corpus_version="synthetic",
        private_indexes=Indexes(),
        deadline_seconds=30,
    )
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = service
    with TestClient(app) as client:
        yield client, model


def check(
    harness,
    text,
    routed,
    *,
    alignment="CONFIRMS",
    term_label=None,
    alignment_confidence=0.9,
    state="SUPPORTED",
):
    client, model = harness
    model.route, model.alignment, model.term_label = routed, alignment, term_label
    model.alignment_confidence, model.state = alignment_confidence, state
    model.calls.clear()
    response = client.post("/api/v1/check", json={"original_text": text})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["retryable_results"] == []
    assert len(body["cards"]) == 1
    card = body["cards"][0]
    VALIDATOR.validate(card)
    return card


def quotes_are_copied(card):
    """Every displayed quote equals a loaded or received record text, byte for byte."""
    known = {quran_record()["text_ar"], hadith_record()["text_ar"], FAQ_ANSWER, GLOSSARY_RULE}
    for item in card["evidence"]:
        assert item["quote_ar"] in known
        assert item["verbatim_verified"] is True
    if card["misquote_notice"]:
        assert card["misquote_notice"]["evidence"]["quote_ar"] in known
    if card["published_answer"]:
        assert card["published_answer"]["excerpt_ar"] in known


def capped(text):
    return text.count(".") <= EXPLANATION_SENTENCES and "رابعة" not in text


def test_case_1_kaaba_misconception_is_corrected_calmly_with_source(harness):
    text = "لماذا يعبد المسلمون الكعبة؟"
    card = check(
        harness,
        text,
        route(text, kind="doubt", level="A", origin="presupposition"),
        alignment="CONTRADICTS",
    )
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"
    assert card["state_label_key"] == "supported_contradicts"
    assert card["evidence"][0]["domain"] == "faq"
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    assert card["explanation_ar"] and capped(card["explanation_ar"])
    assert card["referral"] is None
    quotes_are_copied(card)


def test_case_2_quran_authorship_gets_grounded_introductory_answer(harness):
    text = "هل القرآن من تأليف محمد ﷺ؟"
    card = check(
        harness,
        text,
        route(text, kind="doubt", level="A", origin="presupposition"),
        alignment="CONTRADICTS",
    )
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"
    assert card["evidence"][0]["source_id"] == "bayyinat"
    assert card["explanation_ar"] and capped(card["explanation_ar"])
    quotes_are_copied(card)


def test_case_3_spread_by_sword_shows_the_publisher_answer_at_level_c(harness):
    text = "هل الإسلام انتشر بالسيف؟"
    # The model follows the old level-C instinct and proposes CANNOT_CONFIRM while still
    # selecting the matched Bayyinat answer; the match decides the card (owner decision).
    card = check(
        harness,
        text,
        route(text, kind="doubt", level="C", origin="question_subject"),
        state="CANNOT_CONFIRM",
        alignment=None,
        alignment_confidence=0.0,
    )
    assert card["claim"]["level"] == "C"
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONFIRMS"
    assert card["positions"] == []  # No second position is required for a published answer.
    assert card["published_answer"]["excerpt_ar"] == FAQ_ANSWER
    assert card["published_answer"]["url"] == faq_received()["source_url"]
    assert card["explanation_ar"] and capped(card["explanation_ar"])
    assert card["referral"] is None
    quotes_are_copied(card)


def test_case_4_scholarly_differences_explained_from_evidence(harness):
    text = "لماذا توجد أحكام مختلفة بين العلماء؟"
    card = check(harness, text, route(text, kind="doubt", level="B", origin="question_subject"))
    assert card["claim"]["level"] == "B"
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONFIRMS"
    assert card["evidence"][0]["domain"] == "faq"
    assert card["explanation_ar"] and capped(card["explanation_ar"])
    assert card["positions"] == []  # Differences are never ranked or invented.
    quotes_are_copied(card)


def test_case_5_personal_marriage_case_gets_general_info_and_referral_only(harness):
    text = "أنا في دولة كذا، هل يجوز لي فعل كذا في زواجي؟"
    card = check(harness, text, route(text, kind="other", level="A", origin="question_subject"))
    client, model = harness
    assert model.calls == []  # The deterministic level D path never calls a model.
    assert card["claim"]["level"] == "D"
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "LEVEL_D_PERSONAL_CASE"
    assert card["evidence"] == [] and card["positions"] == []
    assert card["explanation_ar"] == LEVEL_D_TEXT[0]
    assert card["referral"]["body_url"].startswith("https://")
    assert card["referral"]["ready_to_ask_question_ar"].endswith(text)


def test_case_6_requested_hadith_without_match_states_nothing_was_found(harness):
    text = "أعطني حديثاً يثبت هذا الكلام"
    card = check(
        harness,
        text,
        route(text, kind="hadith", level="A", origin="question_subject", phrases=["كلام"]),
    )
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "NO_MATCHING_EVIDENCE"
    assert card["evidence"] == [] and card["misquote_notice"] is None
    assert card["explanation_ar"] == ABSTENTION_TEXT["hadith"][0]
    assert card["referral"]
    for marker in FORBIDDEN_HADITH_MARKERS:
        assert marker not in json.dumps(card, ensure_ascii=False)


def test_case_7_term_meaning_shows_definition_then_term(harness):
    text = "ما معنى التوحيد لشخص لم يسمع بالمصطلح؟"
    card = check(
        harness,
        text,
        route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
        term_label="التوحيد",
    )
    assert card["input_kind"] == "term"
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONFIRMS"
    assert card["evidence"][0]["domain"] == "glossary"
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    assert card["term"] == {
        "term_ar": "التوحيد",
        "term_en": "Synthetic equivalent",
        "source_ref": card["evidence"][0]["source_ref"],
    }
    assert card["explanation_ar"] and capped(card["explanation_ar"])
    assert "glossary_link" not in card  # A shown definition needs no link-only block.
    quotes_are_copied(card)


def test_case_8_translation_uses_glossary_equivalent(harness):
    text = "ترجم كلمة التوحيد إلى الإنجليزية"
    card = check(
        harness,
        text,
        route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
        term_label="التوحيد",
    )
    assert card["state"] == "SUPPORTED"
    assert card["term"]["term_en"] == "Synthetic equivalent"
    assert card["evidence"][0]["source_id"] == "jamhara-glossary"
    quotes_are_copied(card)


def test_case_8b_glossary_without_equivalent_still_shows_definition(harness):
    text = "ترجم كلمة الوحي إلى الإنجليزية"
    client, model = harness
    original = Indexes.discover

    def without_equivalent(self, text, request, *, kind, level, timeout):
        record = glossary_received("الوحي", "", 303)
        del record["text_en"]
        request.receive(record)

    Indexes.discover = without_equivalent
    try:
        card = check(
            harness,
            text,
            route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    finally:
        Indexes.discover = original
    assert card["state"] == "SUPPORTED" and card["evidence"][0]["domain"] == "glossary"
    assert card["term"] is None  # No equivalent is inferred from language names.
    assert "glossary_link" not in card


def test_case_9_hostile_phrasing_is_answered_on_the_real_question(harness):
    text = "لماذا يمنع الإسلام الاجتهاد؟ هذا عبث!"
    card = check(
        harness,
        text,
        route(text, kind="doubt", level="B", origin="presupposition"),
        alignment="CONTRADICTS",
    )
    assert card["claim"]["level"] == "B"  # Tone never changes the level.
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"
    assert "عبث" not in card["explanation_ar"]
    # Three sentences kept, the fourth dropped, text otherwise unchanged.
    assert card["explanation_ar"] == "جملة تجريبية أولى. جملة تجريبية ثانية. جملة تجريبية ثالثة."
    quotes_are_copied(card)


def test_case_10_unspecified_matter_never_claims_consensus(harness):
    text = "هل كل المسلمين يتفقون في هذه المسألة؟"
    card = check(
        harness,
        text,
        route(text, kind="other", level="C", origin="question_subject", no_claim=True),
    )
    assert card["claim"]["level"] == "C"
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "NO_CHECKABLE_CLAIM"
    assert card["explanation_ar"] == ABSTENTION_TEXT["NO_CHECKABLE_CLAIM"][0]
    assert card["evidence"] == [] and card["positions"] == []
    assert card["referral"]["ready_to_ask_question_ar"].endswith(text)


def test_case_11_misquoted_excerpt_is_corrected_from_the_record(harness):
    altered = " ".join(VERSE_WORDS[7:11] + ["مغايرة"])
    text = f"قال الله تعالى: «{altered}»، فهل هذا صحيح؟"
    card = check(
        harness, text, route(text, kind="verse", level="A", origin="stated", refs=[(1, 1)])
    )
    client, model = harness
    # The detector decided the card; no composition call was made.
    assert all("search_queries" in s.get("properties", {}) for s in model.calls)
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"
    assert card["state_label_key"] == "supported_contradicts"
    assert [e["evidence_id"] for e in card["evidence"]] == ["quran:1:1"]
    assert card["evidence"][0]["ref"] == {"surah": 1, "ayah": 1}
    assert card["evidence"][0]["quote_ar"] == quran_record()["text_ar"]
    assert "مغايرة" not in json.dumps(card["evidence"], ensure_ascii=False)
    assert card["explanation_ar"] == CORRECTION_TEXT[0]
    assert card["claim"]["scripture_spans"][0]["classification"] == "NEAR_MISS"
    quotes_are_copied(card)


def test_case_11b_correct_excerpt_is_not_flagged(harness):
    exact = " ".join(VERSE_WORDS[7:12])
    text = f"قال الله تعالى: «{exact}»"
    card = check(
        harness, text, route(text, kind="verse", level="A", origin="stated", refs=[(1, 1)])
    )
    assert card["claim"]["scripture_spans"][0]["classification"] == "VERBATIM"
    assert card["alignment"] != "CONTRADICTS"


def test_case_12_english_loaded_term_is_explained_from_glossary(harness):
    text = "Does Sharia mean only criminal punishments, or does the term have a wider meaning?"
    card = check(
        harness,
        text,
        route(text, kind="term", level="B", origin="term_lookup", lang="en", no_claim=True),
        term_label="الشريعة",
    )
    assert card["claim"]["lang"] == "en"
    assert card["state"] == "SUPPORTED" and card["term"]["term_en"] == "Sharia"
    assert card["evidence"][0]["source_id"] == "jamhara-glossary"
    assert card["explanation_en"] and "Fourth" not in card["explanation_en"]
    quotes_are_copied(card)


def test_understood_question_shows_the_users_words_not_the_premise(harness):
    text = "لماذا يعبد المسلمون الكعبة؟"
    routed = route(text, kind="doubt", level="A", origin="presupposition")
    routed["claims"][0]["text_ar"] = "المسلمون يعبدون الكعبة"  # router premise: retrieval key only
    card = check(harness, text, routed, alignment="CONTRADICTS")
    assert card["claim"]["text_ar"] == text
    assert card["claim"]["text_original"] == text
    assert "يعبدون" not in json.dumps(card["claim"], ensure_ascii=False)
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONTRADICTS"


def test_glossary_definition_does_not_need_a_model_alignment(harness):
    text = "ما معنى التوحيد؟"
    card = check(
        harness,
        text,
        route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
        term_label="التوحيد",
        alignment=None,
        alignment_confidence=0.0,
    )
    assert card["state"] == "SUPPORTED" and card["alignment"] == "CONFIRMS"
    assert card["abstained_reason"] is None
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    assert card["evidence"][0]["ref"] == {"label": "/dictionary/word/101"}
    assert card["term"]["term_ar"] == "التوحيد"
    assert "glossary_link" not in card
    assert card["explanation_ar"] != ABSTENTION_TEXT["default"][0]


def test_translation_request_uses_the_publisher_english_item(harness):
    text = "ترجم كلمة التوحيد إلى الإنجليزية؟"
    original = Indexes.discover

    def with_translation_list(self, text, request, *, kind, level, timeout):
        record = glossary_received("التوحيد", "", 404)
        del record["text_en"]
        record["translations"] = ["Français: Équivalent", "English: Synthetic equivalent"]
        request.receive(record)

    Indexes.discover = with_translation_list
    try:
        card = check(
            harness,
            text,
            route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
            alignment=None,
            alignment_confidence=0.0,
        )
    finally:
        Indexes.discover = original
    assert card["state"] == "SUPPORTED"
    assert card["evidence"][0]["quote_ar"] == GLOSSARY_RULE
    # The publisher's own English list item, verbatim; the label is the record's term.
    assert card["term"] == {
        "term_ar": "التوحيد",
        "term_en": "English: Synthetic equivalent",
        "source_ref": card["evidence"][0]["source_ref"],
    }


def test_language_name_alone_is_not_an_equivalent(harness):
    text = "ترجم كلمة التوحيد إلى الإنجليزية؟"
    original = Indexes.discover

    def names_only(self, text, request, *, kind, level, timeout):
        record = glossary_received("التوحيد", "", 505)
        del record["text_en"]
        record["translations"] = ["English", "Français"]
        request.receive(record)

    Indexes.discover = names_only
    try:
        card = check(
            harness,
            text,
            route(text, kind="term", level="A", origin="term_lookup", no_claim=True),
        )
    finally:
        Indexes.discover = original
    assert card["state"] == "SUPPORTED" and card["term"] is None
