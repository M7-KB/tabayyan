"""Offline extraction contract tests; no religious answers or live inference."""

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.classifier import LevelClassifier
from api.extract import ExtractionError, Extractor, ExtractRequest
from api.main import create_app
from api.settings import Settings
from api.span_detector import DetectorConfig, Record, SpanDetector

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "api/policy/content_policy.yaml"
TUNING = ROOT / "api/tuning.yaml"


class Stub:
    def __init__(self, value):
        self.value, self.calls = value, []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.value, Exception):
            raise self.value
        return copy.deepcopy(self.value)


def proposal(text, *, kind="claim", origin="stated", lang="ar", no_claim=False):
    return {
        "detected_lang": lang,
        "input_kind": kind,
        "no_checkable_claim": no_claim,
        "claims": [
            {
                "text_ar": text,
                "source_text": text,
                "span": {"start": 0, "end": len(text)},
                "origin": origin,
            }
        ],
    }


def service(value, *, level=None, records=()):
    extract_model = Stub(value)
    reason_model = Stub(level if level is not None else {"level": "A", "confidence": 0.9})
    return Extractor(
        model=extract_model,
        classifier=LevelClassifier(model=reason_model, policy_path=POLICY, tuning_path=TUNING),
        detector=SpanDetector(records, DetectorConfig.from_files(POLICY, TUNING)),
    )


def test_question_presupposition_and_original_source_span():
    text = "لماذا يعبد المسلمون الكعبة؟"
    value = proposal(text, kind="question", origin="presupposition")
    value["claims"][0]["text_ar"] = "المسلمون يعبدون الكعبة"
    engine = service(value)
    result = engine.extract(ExtractRequest(text=text))
    claim = result.claims[0]
    assert claim.origin == "presupposition"
    assert text[claim.span.start : claim.span.end] == text
    assert claim.text_ar == value["claims"][0]["text_ar"]
    assert engine.classifier.model.calls[0]["data"]["input_context"] == text


@pytest.mark.parametrize(
    "text,kind,origin,no_claim,lang",
    [
        ("لماذا توجد أحكام مختلفة بين العلماء؟", "question", "question_subject", False, "ar"),
        ("ما معنى التوحيد؟", "term", "term_lookup", True, "ar"),
        ("Translate Tawhid into English", "term", "term_lookup", True, "en"),
        ("Worship has a wider meaning", "claim", "stated", False, "en"),
        ("I feel confused", "question", "term_lookup", True, "en"),
    ],
)
def test_input_shapes(text, kind, origin, no_claim, lang):
    result = service(proposal(text, kind=kind, origin=origin, no_claim=no_claim, lang=lang))
    result = result.extract(ExtractRequest(text=text))
    assert result.detected_lang == lang
    assert result.input_kind == kind
    assert result.no_checkable_claim == no_claim
    assert result.claims[0].origin == origin


def test_segmentation_unicode_offsets_and_limit():
    text = "😀 First statement. Second statement."
    value = proposal(text, lang="en")
    value["claims"] = []
    for fragment in ["First statement.", "Second statement."]:
        start = text.index(fragment)
        value["claims"].append(
            {
                "text_ar": fragment,
                "source_text": fragment,
                "span": {"start": start, "end": start + len(fragment)},
                "origin": "stated",
            }
        )
    result = service(value).extract(ExtractRequest(text=text, max_claims=1))
    assert result.dropped_count == 1
    assert len(result.claims) == 1
    assert result.claims[0].id == "c1"
    assert text[result.claims[0].span.start : result.claims[0].span.end] == "First statement."


def test_original_personal_context_cannot_be_erased_by_extraction():
    text = "Can I do this in my marriage?"
    value = proposal(text, kind="question", origin="question_subject", lang="en")
    value["claims"][0]["text_ar"] = "General marriage question"
    engine = service(value)
    result = engine.extract(ExtractRequest(text=text))
    assert result.claims[0].level == "D"
    assert result.claims[0].classifier_status == "rule_forced"
    assert not engine.classifier.model.calls


@pytest.mark.parametrize(
    "reason,status",
    [
        (RuntimeError("private request"), "unavailable"),
        ({"level": "A", "confidence": 0.1}, "low_confidence"),
        ({"level": "A", "confidence": 0.9, "state": "SUPPORTED"}, "unavailable"),
    ],
)
def test_reasoning_failures_keep_restrictive_level(reason, status):
    text = "A general concept"
    result = service(proposal(text, lang="en"), level=reason).extract(ExtractRequest(text=text))
    assert result.claims[0].level == "D"
    assert result.claims[0].classifier_status == status


def test_scripture_advisory_uses_original_text_and_never_returns_evidence():
    text = 'Prefix "synthetic alpha beta gamma" suffix'
    record = Record("synthetic:q", "quran", "synthetic alpha beta gamma")
    result = service(proposal(text, lang="en"), records=[record]).extract(ExtractRequest(text=text))
    claim = result.claims[0]
    assert claim.span_detector_status == "ran"
    assert any(text[s.start : s.end] == record.text_ar for s in claim.scripture_spans)
    assert "evidence" not in claim.model_dump()
    assert "state" not in claim.model_dump()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(state="SUPPORTED"),
        lambda v: v["claims"][0]["span"].update(end=999),
        lambda v: v["claims"][0]["span"].update(start=-1),
        lambda v: v["claims"][0]["span"].update(start=True),
        lambda v: v["claims"][0].update(source_text="invented"),
        lambda v: v["claims"][0].update(text_ar=" "),
        lambda v: v["claims"][0].update(text_ar="invented assertion"),
        lambda v: v["claims"].append(copy.deepcopy(v["claims"][0])),
        lambda v: v["claims"][0].update(origin="term_lookup"),
        lambda v: v.update(no_checkable_claim=True),
        lambda v: v.update(input_kind="term"),
    ],
)
def test_malformed_proposals_fail_closed(mutation):
    text = "synthetic input"
    value = proposal(text, lang="en")
    mutation(value)
    with pytest.raises(ExtractionError) as caught:
        service(value).extract(ExtractRequest(text=text))
    assert (caught.value.status, caught.value.code) == (503, "PIPELINE_DEGRADED")


@pytest.mark.parametrize("value", [None, [], "bad", RuntimeError("private input")])
def test_provider_failure(value):
    with pytest.raises(ExtractionError, match="PIPELINE_DEGRADED"):
        service(value).extract(ExtractRequest(text="synthetic"))


def app_with(engine, health_only=False):
    app = create_app(
        Settings(
            openai_api_key="inert",
            content_policy_path=POLICY,
            tuning_path=TUNING,
            health_only=health_only,
        )
    )
    app.state.extractor = engine
    return app


def test_http_workflow_and_no_request_persistence(caplog):
    text = "synthetic private phrase"
    app = app_with(service(proposal(text, lang="en")))
    with TestClient(app) as client:
        result = client.post("/api/v1/extract", json={"text": text})
        assert result.status_code == 200
        assert result.json()["claims"][0]["text_ar"] == text
        assert client.get("/health").status_code == 200
    assert text not in caplog.text
    assert not hasattr(app.state, "queries")


@pytest.mark.parametrize(
    "payload,status,code",
    [
        ({"text": " "}, 400, "NO_CLAIMS"),
        ({"text": "a", "max_claims": 0}, 422, "INVALID_REQUEST"),
        ({"text": "a", "max_claims": True}, 422, "INVALID_REQUEST"),
        ({"text": "a" * 12001}, 422, "INVALID_REQUEST"),
        ({"text": "a", "level": "A"}, 422, "INVALID_REQUEST"),
    ],
)
def test_http_errors_are_safe(payload, status, code):
    with TestClient(app_with(service(None))) as client:
        result = client.post("/api/v1/extract", json=payload)
    assert result.status_code == status
    assert result.json()["error"]["code"] == code
    assert "input" not in result.json()["error"]


def test_unavailable_configuration_is_503_and_health_only_has_no_extract():
    with TestClient(create_app(Settings(openai_api_key="inert"))) as client:
        result = client.post("/api/v1/extract", json={"text": "synthetic"})
        assert result.status_code == 503
    with TestClient(app_with(service(None), health_only=True)) as client:
        assert client.post("/api/v1/extract", json={"text": "a"}).status_code == 404


@pytest.mark.parametrize(
    "value,status,code",
    [
        (
            {
                "detected_lang": "en",
                "input_kind": "claim",
                "claims": [],
                "no_checkable_claim": False,
            },
            400,
            "NO_CLAIMS",
        ),
        (proposal("synthetic", lang="unsupported"), 422, "TEXT_NOT_SUPPORTED_LANG"),
        (RuntimeError("do not echo private phrase"), 503, "PIPELINE_DEGRADED"),
    ],
)
def test_provider_http_error_mapping(value, status, code):
    with TestClient(app_with(service(value))) as client:
        result = client.post("/api/v1/extract", json={"text": "synthetic"})
    assert result.status_code == status
    assert result.json()["error"]["code"] == code
    assert "private phrase" not in result.text


def test_http_uses_real_adapter_and_separate_extraction_reason_models(monkeypatch):
    import json

    import httpx

    from api.provider import OpenAIStructuredModel

    text = "synthetic assertion"
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        value = (
            proposal(text, lang="en")
            if payload["model"] == "extract-model"
            else {"level": "B", "confidence": 0.9}
        )
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": json.dumps(value)}],
                    }
                ],
            },
        )

    def factory(**kwargs):
        return OpenAIStructuredModel(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr("api.main.OpenAIStructuredModel", factory)
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_model_extract="extract-model",
            openai_model_reason="reason-model",
        )
    )
    with TestClient(app) as client:
        result = client.post("/api/v1/extract", json={"text": text})
    assert result.status_code == 200
    assert result.json()["claims"][0]["level"] == "B"
    assert result.json()["claims"][0]["span_detector_status"] == "index_unavailable"
    assert [c["model"] for c in calls] == ["extract-model", "reason-model"]
    assert all(c["store"] is False for c in calls)
    context = json.loads(calls[1]["input"][1]["content"])["untrusted_data"]
    assert context["input_context"] == text
