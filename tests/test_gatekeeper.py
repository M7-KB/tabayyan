"""Synthetic source responses; no live sources, scripture or religious evaluation."""

import copy

import pytest
from fastapi.testclient import TestClient

from api.composer import VALIDATOR, Composer
from api.config import load_config
from api.gatekeeper import QuoteGatekeeper, SourceRequest, allowed_url
from api.main import create_app
from api.retrieval import BM25Retriever
from api.settings import Settings
from api.span_detector import DetectorConfig
from tests.test_composer import POLICY, TEXT, TUNING, Stub, claim, proposal, record


def local(text=TEXT, cid="local:one", domain="quran"):
    r = record(cid, domain, text)
    r["source_id"] = "kfc-mushaf" if domain == "quran" else "sahih-bukhari"
    return r


def raw(source="islamqa", text="مصدر تجريبي يشرح الفاكهة وأسماءها", ref="one", domain="faq"):
    hosts = {"islamqa": "islamqa.info", "binbaz": "binbaz.org.sa", "dorar-hadith": "dorar.net"}
    r = record(domain=domain, text=text)
    r.update(
        source_id=source,
        record_ref=ref,
        source_url=f"https://{hosts[source]}/test/{ref}",
        title_ar="عنوان المصدر التجريبي",
    )
    r.pop("corpus_id")
    r["grading"]["grading_source_url"] = "https://dorar.net/test/grade"
    return r


def gate(*results, locals=None, request=None, received=None):
    request = request or SourceRequest()
    for r in results:
        request.receive(r)
    return QuoteGatekeeper(
        local_records=[local()] if locals is None else locals,
        request=request,
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
        received=received,
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.islamqa.info/test",
        "https://islamqa.info.evil/test",
        "http://islamqa.info/test",
        "https://islamqa.info:444/test",
        "https://user@islamqa.info/test",
        "https://islamqa.info/test#fragment",
        "https://127.0.0.1/test",
        "https://islamqa.info /test",
    ],
)
def test_unallowlisted_or_ambiguous_urls_are_refused(url):
    assert not allowed_url(url, "islamqa.info")
    r = raw()
    r["source_url"] = url
    assert all(not x["corpus_id"].startswith("live:") for x in gate(r).records)


def test_unknown_hosts_sources_and_domains_stay_disabled():
    for r in [
        raw(source="islamqa", domain="quran"),
        {**raw(), "source_id": "icadb"},
        {**raw(), "source_id": "jamhara-glossary"},
    ]:
        assert len(gate(r).records) == 1


def test_old_request_records_cannot_authorize_new_request_or_change_index():
    old = SourceRequest()
    receipt = old.receive(raw("dorar-hadith", TEXT.replace("موز", "خوخ"), domain="hadith"))
    g = gate(request=SourceRequest(), received=[receipt])
    assert len(g.records) == 1
    assert g.verify("live:dorar-hadith:one", receipt.record["text_ar"]) is None


def test_source_request_cannot_be_reused_or_extended_after_consumption():
    scope = SourceRequest()
    gate(raw(), request=scope)
    with pytest.raises(ValueError):
        gate(request=scope)
    with pytest.raises(ValueError):
        scope.receive(raw())


def test_matching_is_normalized_but_output_copies_original_bound_record():
    r = raw("dorar-hadith", "تُفّاحة برتقال موز عنب رمان", domain="hadith")
    g = gate(r)
    result = g.verify("live:dorar-hadith:one", "تفاحه برتقال موز عنب رمان")
    assert result["text_ar"] == r["text_ar"]
    assert result["source_ref"] == {
        "source_id": r["source_id"],
        "record_ref": r["record_ref"],
        "url": r["source_url"],
    }
    assert result["grading"] == r["grading"]
    assert g.verify("live:dorar-hadith:one", TEXT + " invented") is None
    assert g.verify("unknown", r["text_ar"]) is None


@pytest.mark.parametrize("field", ["grade_ar", "grader_ar", "grading_source_url"])
def test_hadith_cannot_borrow_grading_from_another_record(field):
    missing = raw("dorar-hadith", TEXT, domain="hadith")
    del missing["grading"][field]
    good = raw("dorar-hadith", TEXT, ref="two", domain="hadith")
    g = gate(missing, good)
    assert g.verify("live:dorar-hadith:one", TEXT) is None
    assert g.verify("live:dorar-hadith:two", TEXT) is not None


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("exact_live", [False, True])
@pytest.mark.parametrize("trigger", ["A", "B"])
def test_exact_veto_across_whole_local_live_comparison_set(reverse, exact_live, trigger):
    exact = TEXT.replace("موز", "خوخ")
    loc = local(TEXT if exact_live else exact)
    live = raw("dorar-hadith", exact if exact_live else TEXT, domain="hadith")
    g = gate(live, locals=[loc])
    if reverse:
        g.detector.index = tuple(reversed(g.detector.index))
    match = g.detector.classify(exact, trigger)
    assert match.classification == "VERBATIM"
    found = g.detector.detect('"' + exact + '"' if trigger == "A" else exact)
    assert not any(f.match.classification == "NEAR_MISS" for f in found.findings)


def test_exact_span_does_not_suppress_a_separate_altered_span():
    r = raw("dorar-hadith", "قلم دفتر ورقة مسطرة حقيبة", domain="hadith")
    g = gate(r)
    text = '"' + TEXT + '"\n"قلم دفتر كرسي مسطرة حقيبة"'
    result = g.detector.detect(text)
    assert {f.match.classification for f in result.findings} >= {"VERBATIM", "NEAR_MISS"}


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("trigger", ["A", "B"])
@pytest.mark.parametrize("invalid", ["grading", "reference", "grading_url", None])
def test_only_authorized_live_twins_can_veto_local_quran_correction(reverse, trigger, invalid):
    altered = TEXT.replace("موز", "خوخ")
    twin = raw("dorar-hadith", altered, domain="hadith")
    if invalid == "grading":
        del twin["grading"]
    elif invalid == "reference":
        twin["ref"] = {"number": 1}
    elif invalid == "grading_url":
        twin["grading"]["grading_source_url"] = "https://evil.invalid/grade"
    faq = raw()
    g = gate(twin, faq)
    if reverse:
        g.detector.index = tuple(reversed(g.detector.index))
    matched = g.detector.classify(altered, trigger)
    assert matched.classification == ("VERBATIM" if invalid is None else "NEAR_MISS")
    assert (g.verify("live:dorar-hadith:one", altered) is not None) == (invalid is None)
    span = '"' + altered + '"' if trigger == "A" else altered
    found = g.detector.detect(span)
    assert any(f.match.classification == "NEAR_MISS" for f in found.findings) == (
        invalid is not None
    )
    card = compose(g, proposal(corpus_ids=["live:islamqa:one"]), span + "\n" + faq["text_ar"])
    if invalid is not None:
        assert card["alignment"] == "CONTRADICTS"
        assert any(e["evidence_id"] == "local:one" for e in card["evidence"])
    else:
        assert card["alignment"] == "CONFIRMS"


def test_title_and_excerpt_are_bound_to_the_same_source_result():
    a, b = raw(), raw("binbaz", ref="two")
    a["title_ar"], b["title_ar"] = "عنوان أول", "عنوان ثان"
    g = gate(a, b)
    published, _ = g.published_answer("live:islamqa:one", a["text_ar"])
    assert published["title_ar"] == a["title_ar"]
    assert published["excerpt_ar"] == a["text_ar"]
    for title in ("model-written", b["title_ar"]):
        published, _ = g.published_answer("live:islamqa:one", a["text_ar"], proposed_title=title)
        assert published["title_ar"] == "الإسلام سؤال وجواب"


def test_title_scripture_passes_or_falls_back_without_losing_valid_excerpt():
    r = raw()
    r["title_ar"] = '"' + TEXT + '"'
    good, dependencies = gate(r).published_answer("live:islamqa:one", r["text_ar"])
    assert good["title_ar"] == r["title_ar"]
    assert dependencies[0]["corpus_id"] == "local:one"
    r["title_ar"] = '"' + TEXT.replace("موز", "خوخ") + '"'
    fallback, _ = gate(r).published_answer("live:islamqa:one", r["text_ar"])
    assert fallback["title_ar"] == "الإسلام سؤال وجواب"
    assert fallback["excerpt_ar"] == r["text_ar"]


def test_hadith_title_requires_its_own_same_request_graded_record():
    title = "قلم دفتر ورقة مسطرة حقيبة"
    article = raw()
    article["title_ar"] = '"' + title + '"'
    h = raw("dorar-hadith", title, domain="hadith")
    g = gate(article, h)
    published, deps = g.published_answer("live:islamqa:one", article["text_ar"])
    assert published["title_ar"] == article["title_ar"]
    assert deps[0]["grading"] == h["grading"]
    del h["grading"]
    published, _ = gate(article, h).published_answer("live:islamqa:one", article["text_ar"])
    assert published["title_ar"] == "الإسلام سؤال وجواب"


def test_excerpt_with_ungraded_hadith_is_dropped():
    text = "قلم دفتر ورقة مسطرة حقيبة"
    a = raw(text='"' + text + '"')
    h = raw("dorar-hadith", text, domain="hadith")
    del h["grading"]
    g = gate(a, h)
    assert g.verify("live:islamqa:one", a["text_ar"]) is None
    assert g.published_answer("live:islamqa:one", a["text_ar"]) is None


def test_duplicate_record_refs_fail_closed_even_when_seen_three_times():
    r = raw()
    assert len(gate(r, r, r).records) == 1


def composer_with(g, value):
    _, tuning = load_config(POLICY, TUNING)
    return Composer(
        model=Stub(value),
        retriever=BM25Retriever(g.records, tuning),
        detector=g.detector,
        records=g.records,
        policy_path=POLICY,
        tuning_path=TUNING,
        gatekeeper=g,
    )


def compose(g, value, text, level="A"):
    result = composer_with(g, value).compose(
        claim(text, level=level),
        original=text,
        lang="ar",
        input_kind="claim",
        no_checkable_claim=False,
    )
    VALIDATOR.validate(result)
    return result


def test_bad_quote_drops_without_discarding_independent_good_quote():
    a, b = raw(), raw("dorar-hadith", TEXT, domain="hadith")
    del b["grading"]
    card = compose(
        gate(a, b),
        proposal(corpus_ids=["live:islamqa:one", "live:dorar-hadith:one"]),
        a["text_ar"] + "\n" + TEXT,
    )
    assert card["state"] == "SUPPORTED"
    assert len(card["evidence"]) == 1
    assert "corpus_id" not in card["evidence"][0]
    assert card["published_answer"]["excerpt_ar"] == a["text_ar"]


def test_all_failed_quotes_abstain_with_referral_and_question():
    r = raw("dorar-hadith", TEXT, domain="hadith")
    del r["grading"]
    c = compose(gate(r), proposal(corpus_ids=["live:dorar-hadith:one"]), TEXT)
    assert c["state"] == "CANNOT_CONFIRM"
    assert c["alignment"] is None and c["positions"] == [] and c["evidence"] == []
    assert c["referral"]["ready_to_ask_question_ar"]


def test_losing_a_disputed_position_cannot_preserve_disputed():
    a, b = raw(), raw("dorar-hadith", raw()["text_ar"], domain="hadith")
    del b["grading"]
    ids = ["live:islamqa:one", "live:dorar-hadith:one"]
    positions = [
        {"label_ar": "موقف تجريبي", "summary_ar": "راجع المرجع المذكور.", "corpus_ids": [key]}
        for key in ids
    ]
    card = compose(
        gate(a, b),
        proposal(corpus_ids=ids, positions=positions, recorded_disagreement=True),
        a["text_ar"],
        "C",
    )
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["positions"] == [] and card["alignment"] is None


def test_two_surviving_positions_need_different_sources():
    a, b = raw(), raw("binbaz", raw()["text_ar"], ref="two")
    ids = ["live:islamqa:one", "live:binbaz:two"]
    positions = [
        {"label_ar": "موقف تجريبي", "summary_ar": "راجع المرجع المذكور.", "corpus_ids": [key]}
        for key in ids
    ]
    card = compose(
        gate(a, b),
        proposal(corpus_ids=ids, positions=positions, recorded_disagreement=True),
        a["text_ar"],
        "C",
    )
    assert card["state"] == "DISPUTED"
    assert card["published_answer"] is None


def test_local_index_unavailable_fails_closed_despite_live_hit():
    r = raw()
    c = compose(gate(r, locals=[]), proposal(corpus_ids=["live:islamqa:one"]), r["text_ar"])
    assert c["abstained_reason"] == "ALIGNMENT_UNDETERMINED"


def test_embedded_hadith_grading_is_visible_on_disputed_card():
    hadith_text = "قلم دفتر ورقة مسطرة حقيبة"
    a, b = (
        raw(text='"' + hadith_text + '"'),
        raw("binbaz", ref="two"),
    )
    h = raw("dorar-hadith", hadith_text, domain="hadith")
    ids = ["live:islamqa:one", "live:binbaz:two"]
    positions = [
        {"label_ar": "موقف تجريبي", "summary_ar": "راجع المرجع المذكور.", "corpus_ids": [key]}
        for key in ids
    ]
    card = compose(
        gate(a, b, h),
        proposal(corpus_ids=ids, positions=positions, recorded_disagreement=True),
        hadith_text + "\n" + b["text_ar"],
        "C",
    )
    assert card["state"] == "DISPUTED"
    graded = next(e for e in card["evidence"] if e["domain"] == "hadith")
    assert graded["grading"] == {
        k: h["grading"][k] for k in ("grade_ar", "grader_ar", "grading_source_url")
    }
    assert graded["source_ref"]["record_ref"] == h["record_ref"]


def test_embedded_hadith_with_missing_reference_cannot_authorize_excerpt():
    text = "قلم دفتر ورقة مسطرة حقيبة"
    a, h = raw(text='"' + text + '"'), raw("dorar-hadith", text, domain="hadith")
    h["ref"] = {"number": 1}
    assert gate(a, h).verify("live:islamqa:one", a["text_ar"]) is None


def test_result_metadata_is_copied_and_canonical_not_model_substituted():
    r = raw()
    r["source_name_ar"] = "Injected name"
    r["source_ref"] = {"source_id": "binbaz", "record_ref": "wrong", "url": "https://evil.invalid"}
    g = gate(r)
    r["text_ar"] = "Changed after receipt"
    original = g.verify("live:islamqa:one", raw()["text_ar"])
    assert original["source_name_ar"] == "الإسلام سؤال وجواب"
    assert original["source_ref"] == {
        "source_id": "islamqa",
        "record_ref": "one",
        "url": "https://islamqa.info/test/one",
    }


def test_dropped_position_prose_is_removed_before_separation_scan():
    a, b = raw(), raw("binbaz", raw()["text_ar"], ref="two")
    ids = ["live:islamqa:one", "live:binbaz:two"]
    positions = [
        {"label_ar": "موقف تجريبي", "summary_ar": "راجع المرجع المذكور.", "corpus_ids": [key]}
        for key in ids
    ]
    positions.append(
        {"label_ar": "Unbound", "summary_ar": '"fabricated quote"', "corpus_ids": ["invented"]}
    )
    card = compose(
        gate(a, b),
        proposal(corpus_ids=ids + ["invented"], positions=positions, recorded_disagreement=True),
        a["text_ar"],
        "B",
    )
    assert card["state"] == "DISPUTED"
    assert len(card["positions"]) == 2
    assert card["gate_report"]["separation"] == "pass"


def test_title_detector_failure_uses_neutral_source_name(monkeypatch):
    from api.span_detector import Detection

    r = raw()
    g = gate(r)
    detect = g.detector.detect
    monkeypatch.setattr(
        g.detector,
        "detect",
        lambda text: Detection("timeout") if text == r["title_ar"] else detect(text),
    )
    published, _ = g.published_answer("live:islamqa:one", r["text_ar"])
    assert published["title_ar"] == "الإسلام سؤال وجواب"


def test_real_endpoint_constructs_gatekeeper_and_does_not_accept_source_injection(monkeypatch):
    text = TEXT
    extraction = {
        "detected_lang": "ar",
        "input_kind": "claim",
        "no_checkable_claim": False,
        "claims": [
            {
                "text_ar": text,
                "source_text": text,
                "span": {"start": 0, "end": len(text)},
                "origin": "stated",
            }
        ],
    }

    class Model:
        def __init__(self, **kwargs):
            pass

        def complete_json(self, **kwargs):
            fields = kwargs["schema"].get("properties", {})
            if "claims" in fields:
                return copy.deepcopy(extraction)
            if "level" in fields:
                return {"level": "A", "confidence": 0.9}
            return proposal(corpus_ids=["local:one"])

    monkeypatch.setattr("api.main.OpenAIStructuredModel", Model)
    app = create_app(Settings(openai_api_key="inert-test-value"))
    with TestClient(app) as client:
        app.state.corpus = [local()]
        response = client.post("/api/v1/check", json={"claims": [{"id": "c1", "text_ar": text}]})
        assert response.status_code == 200
        assert response.json()["cards"][0]["state"] == "SUPPORTED"
        assert app.state.checker.composer.gatekeeper is not None
        response = client.post("/api/v1/check", json={"claims": [], "sources": [raw()]})
        assert response.status_code == 422
