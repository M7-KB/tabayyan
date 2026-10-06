"""Synthetic private-file binding and D7 regressions; no source excerpts."""

import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from jsonschema import ValidationError

from api.check import CheckRequest
from api.composer import VALIDATOR, Composer
from api.diagnostics import Summary, summary
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.main import create_app
from api.retrieval import BM25Retriever
from api.settings import Settings
from api.span_detector import DetectorConfig
from corpus import hadith_artifact as artifact
from corpus.validate import CorpusValidationError
from tests.test_composer import POLICY, TEXT, TUNING, Stub, claim, engine
from tests.test_one_pass import route_proposal, service
from tests.test_router_candidates import quran_record


def row(**updates):
    value = dict(
        id="123",
        title="Synthetic title",
        hadeeth=TEXT,
        attribution="Synthetic narrator",
        grade="[صحيح]",
        reference="Synthetic reference",
        explanation="Synthetic explanation",
        categories=["1"],
        url="https://hadeethenc.com/ar/browse/hadith/123",
    )
    value.update(updates)
    return value


def files(tmp_path, monkeypatch, rows=None, **manifest_updates):
    rows = [row()] if rows is None else rows
    data = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode()
    monkeypatch.setattr(artifact, "SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(artifact, "COUNT", len(rows))
    monkeypatch.setattr(artifact, "BYTES", len(data))
    path = tmp_path / "hadeethenc.jsonl"
    path.write_bytes(data)
    manifest = dict(
        sha256=artifact.SHA256,
        count=len(rows),
        bytes=len(data),
        categories=493,
        failures=0,
        complete=True,
        status="complete",
        source_host="hadeethenc.com",
        file="hadeethenc.jsonl",
    )
    manifest.update(manifest_updates)
    path.with_name("manifest.json").write_text(json.dumps(manifest), "utf-8")
    return path


def test_pinned_loader_copies_source_fields(tmp_path, monkeypatch):
    path = files(tmp_path, monkeypatch)
    record = artifact.load_hadith_artifact(path)[0]
    assert record["text_ar"] == TEXT
    assert record["ref"]["reference"] == row()["reference"]
    assert record["grading"]["grade_ar"] == "[صحيح]"
    assert record["source_url"] == record["grading"]["grading_source_url"] == row()["url"]
    assert record["corpus_id"] == "hadeethenc:123"


@pytest.mark.parametrize(
    "mutation", ["hash", "manifest", "count", "url", "id", "field", "duplicate"]
)
def test_corrupt_artifacts_fail_closed_without_echoing_values(tmp_path, monkeypatch, mutation):
    rows = [row()]
    if mutation == "url":
        rows[0]["url"] = "https://private-secret.invalid"
    if mutation == "id":
        rows[0]["id"] = "secret"
    if mutation == "field":
        rows[0]["grade"] = {"secret": "bad"}
    if mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    path = files(tmp_path, monkeypatch, rows)
    if mutation == "hash":
        path.write_bytes(path.read_bytes() + b" ")
    if mutation == "manifest":
        path.with_name("manifest.json").write_text('{"secret": "bad"}', "utf-8")
    if mutation == "count":
        monkeypatch.setattr(artifact, "COUNT", 99)
    with pytest.raises(CorpusValidationError) as caught:
        artifact.load_hadith_artifact(path)
    assert "secret" not in str(caught.value) and str(tmp_path) not in str(caught.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("grade", "ضعيف"),
        ("grade", ""),
        ("grade", "غير صحيح"),
        ("grade", "صحيح أو ضعيف"),
        ("reference", ""),
        ("attribution", ""),
    ],
)
def test_ungraded_weak_or_incomplete_row_never_authorizes_evidence(
    tmp_path, monkeypatch, field, value
):
    path = files(tmp_path, monkeypatch, [row(**{field: value})])
    assert artifact.load_hadith_artifact(path) == []


def hadith_composer(decision=None, grade="[صحيح]"):
    record = artifact._record(row())
    record["grading"]["grade_ar"] = grade
    gatekeeper = QuoteGatekeeper(
        local_records=[quran_record(), record],
        request=SourceRequest(),
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    base = engine()
    model = Stub(decision or dict(corpus_id="hadeethenc:123", meaning="yes", confidence=0.9))
    composer = Composer(
        model=model,
        retriever=BM25Retriever(gatekeeper.records, base.tuning),
        detector=gatekeeper.detector,
        records=gatekeeper.records,
        policy_path=POLICY,
        tuning_path=TUNING,
        gatekeeper=gatekeeper,
        local_hadith=True,
    )
    return composer, model


def run_hadith(composer, text="Synthetic fruit paraphrase", level="A", phrases=(TEXT,)):
    return composer.compose(
        claim(text, level=level),
        original=text,
        lang="en",
        input_kind="claim",
        no_checkable_claim=False,
        propose_state=True,
        hadith_kind=True,
        hadith_phrases=phrases,
    )


@pytest.mark.parametrize("grade", ["صحيح", "حسن", "[صحيح]", "[حسن]"])
def test_d7_uses_local_grade_and_verbatim_copy_with_referral(grade):
    composer, model = hadith_composer(grade=grade)
    card = run_hadith(composer)
    assert card["state"] == "SUPPORTED" and card["alignment"] == "SAME_MEANING"
    assert card["state_label_key"] == "supported_same_meaning"
    assert card["referral"] and card["hadith_caution_ar"]
    assert card["evidence"][0]["quote_ar"] == TEXT
    assert card["evidence"][0]["grading"]["grade_ar"] == grade
    assert card["evidence"][0]["source_url"] == row()["url"]
    assert card["explanation_ar"] is card["explanation_en"] is None
    assert len(model.calls) == 1
    assert set(model.calls[0]["schema"]["properties"]) == {"corpus_id", "meaning", "confidence"}


def test_exact_hadith_keeps_confirms():
    composer, _ = hadith_composer()
    card = run_hadith(composer, TEXT)
    assert card["alignment"] == "CONFIRMS"
    assert "hadith_caution_ar" not in card


def test_exact_text_in_another_claim_cannot_change_this_claims_alignment():
    composer, _ = hadith_composer()
    text = "Synthetic fruit paraphrase"
    card = composer.compose(
        claim(text),
        original=text + "\n" + TEXT,
        lang="en",
        input_kind="claim",
        no_checkable_claim=False,
        propose_state=True,
        hadith_kind=True,
        hadith_phrases=[TEXT],
    )
    assert card["alignment"] == "SAME_MEANING"


@pytest.mark.parametrize(
    "updates",
    [
        {"meaning": "no"},
        {"meaning": "unsure"},
        {"confidence": 0.1},
        {"corpus_id": "invented"},
        {"corpus_id": None},
        {"meaning": "invalid"},
    ],
)
def test_meaning_uncertainty_or_unbound_id_abstains(updates):
    decision = dict(corpus_id="hadeethenc:123", meaning="yes", confidence=0.9)
    decision.update(updates)
    composer, _ = hadith_composer(decision)
    card = run_hadith(composer)
    assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []
    assert card["referral"]


@pytest.mark.parametrize("grade", ["ضعيف", "", "غير صحيح"])
def test_weak_hadith_cannot_pass_even_if_model_would_say_yes(grade):
    composer, model = hadith_composer(grade=grade)
    card = run_hadith(composer)
    assert card["state"] == "CANNOT_CONFIRM" and card["evidence"] == []
    assert model.calls == []


@pytest.mark.parametrize("level", ["C", "D"])
def test_restricted_hadith_never_calls_meaning_model(level):
    composer, model = hadith_composer()
    assert run_hadith(composer, level=level)["state"] == "CANNOT_CONFIRM"
    assert not model.calls


def test_router_phrases_are_internal_and_malformed_items_fail_soft():
    text = "Synthetic fruit paraphrase"
    secret_phrase = "SENTINEL_9381 " + TEXT
    routed = route_proposal(text, input_kind="hadith", search_queries=[], safe_to_search=False)
    routed["proposed_hadith_phrases"] = [secret_phrase, {}, "x" * 161]
    checker, _, _ = service(routed)
    checker.composer, model = hadith_composer()
    metrics = Summary()
    token = summary.set(metrics)
    try:
        result = checker.check(CheckRequest(original_text=text))
    finally:
        summary.reset(token)
    assert result["cards"][0]["alignment"] == "SAME_MEANING"
    assert "SENTINEL_9381" not in json.dumps(result)
    assert "SENTINEL_9381" not in json.dumps(metrics.codes)
    assert "proposed_hadith_phrases" not in model.calls[0]["data"]
    assert "router_field:proposed_hadith_phrases" in metrics.codes


@pytest.mark.parametrize("mutation", ["source", "weak", "referral", "caution", "live"])
def test_same_meaning_contract_rejects_invalid_evidence_shape(mutation):
    composer, _ = hadith_composer()
    card = run_hadith(composer)
    if mutation == "source":
        card["evidence"][0]["source_id"] = "synthetic"
    if mutation == "weak":
        card["evidence"][0]["grading"]["grade_ar"] = "ضعيف"
    if mutation == "referral":
        card["referral"] = None
    if mutation == "caution":
        del card["hadith_caution_ar"]
    if mutation == "live":
        card["evidence"][0]["corpus_id"] = "live:hadeethenc:123"
    with pytest.raises(ValidationError):
        VALIDATOR.validate(card)


def test_configured_bad_index_is_degraded_and_never_enables_network_fallback(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("api.main.HadeethEncDiscovery", lambda: calls.append("network"))
    settings = Settings(
        openai_api_key="inert",
        openai_schema_warmup=False,
        private_hadith_path=tmp_path / "missing.jsonl",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["hadith_status"] == "unavailable"
        assert health["hadith_items"] == 0 and health["status"] == "degraded"
        response = client.post("/api/v1/check", json={"original_text": "Synthetic fruit"})
        assert response.status_code == 503  # No real provider is configured.
    assert calls == []


@pytest.mark.parametrize("valid", [True, False])
def test_real_http_route_loads_private_index_and_never_dispatches_phrases(
    tmp_path, monkeypatch, valid, caplog
):
    path = files(tmp_path, monkeypatch)
    if not valid:
        path.write_bytes(path.read_bytes() + b" ")
    quran = quran_record()
    quran["approved_by"] = "synthetic-owner"
    monkeypatch.setattr("api.main.load_private_corpus", lambda *a, **kw: ([quran], "synthetic"))
    text = "Synthetic fruit paraphrase"
    routed = route_proposal(text, input_kind="hadith", detected_lang="en")
    routed["proposed_hadith_phrases"] = ["PRIVATE_PHRASE_SENTINEL " + TEXT]
    route_model = Stub(routed)
    reason_model = Stub(dict(corpus_id="hadeethenc:123", meaning="yes", confidence=0.9))
    monkeypatch.setattr(
        "api.main.OpenAIStructuredModel",
        lambda **kw: route_model if kw["model"] == "router" else reason_model,
    )

    def forbidden():
        pytest.fail("Configured local hadith reached a network adapter")

    monkeypatch.setattr("api.main.HadeethEncDiscovery", forbidden)
    monkeypatch.setattr("api.main.IslamicContentConnector", forbidden)
    settings = Settings(
        openai_api_key="inert",
        openai_schema_warmup=False,
        private_corpus_path=tmp_path / "synthetic-quran.jsonl",
        private_hadith_path=path,
        openai_model_extract="router",
        openai_model_reason="reason",
        allow_pending_review=True,
    )
    with TestClient(create_app(settings)) as client:
        health = client.get("/health").json()
        response = client.post("/api/v1/check", json={"original_text": text})
    assert health["hadith_status"] == ("loaded" if valid else "unavailable")
    assert health["hadith_version"] == ("2026-10-06" if valid else None)
    assert health["hadith_items"] == int(valid)
    assert response.status_code == 200 and response.headers["X-Request-ID"]
    card = response.json()["cards"][0]
    assert card["state"] == ("SUPPORTED" if valid else "CANNOT_CONFIRM")
    if valid:
        assert card["alignment"] == "SAME_MEANING"
        assert card["evidence"][0]["quote_ar"] == TEXT
    else:
        assert card["evidence"] == []
    assert len(route_model.calls) == 1 and len(reason_model.calls) == int(valid)
    assert "PRIVATE_PHRASE_SENTINEL" not in response.text
    assert "PRIVATE_PHRASE_SENTINEL" not in caplog.text
    assert TEXT not in caplog.text
