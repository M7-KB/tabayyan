"""One-pass orchestration with synthetic, nonreligious fixtures."""

import copy
import threading

import pytest
from fastapi.testclient import TestClient

from api.check import CheckRequest
from api.classifier import LevelClassifier
from api.extract import ExtractionError
from api.main import create_app
from api.one_pass import OnePassCheckService
from api.router import Router
from api.settings import Settings
from tests.test_composer import POLICY, TEXT, TUNING, Stub, engine, proposal


def route_proposal(text=TEXT, **updates):
    value = {
        "detected_lang": "ar",
        "level": "A",
        "level_confidence": 0.95,
        "level_d": False,
        "premise": text,
        "input_kind": "other",
        "search_queries": ["ethics"],
        "safe_to_search": True,
        "proposed_quran_refs": [],
        "claims": [
            {
                "text_ar": text,
                "source_text": text,
                "span": {"start": 0, "end": len(text)},
                "origin": "stated",
            }
        ],
    }
    value.update(updates)
    return value


def service(value=None, decision=None):
    composer = engine(value=proposal(state="SUPPORTED") if decision is None else decision)
    router_model = Stub(route_proposal() if value is None else value)
    router = Router(
        model=router_model,
        classifier=LevelClassifier(model=None, policy_path=POLICY, tuning_path=TUNING),
        detector=composer.detector,
    )
    return (
        OnePassCheckService(router=router, composer=composer, corpus_version="synthetic"),
        router_model,
        composer.model,
    )


def test_original_only_http_and_exactly_one_router_and_compose_call():
    checker, route_model, compose_model = service()
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = checker
    with TestClient(app) as client:
        response = client.post("/api/v1/check", json={"original_text": TEXT})
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["state"] == "SUPPORTED"
    assert card["evidence"][0]["quote_ar"] == TEXT
    assert card["explanation_ar"] is None and card["explanation_en"] is None
    assert len(route_model.calls) == len(compose_model.calls) == 1
    assert "state" in compose_model.calls[0]["schema"]["required"]


def test_composition_is_parallel_and_output_keeps_source_order():
    original = f"{TEXT}\n{TEXT}"
    value = route_proposal(original)
    value["claims"] = [
        {
            "text_ar": TEXT,
            "source_text": TEXT,
            "span": {"start": start, "end": start + len(TEXT)},
            "origin": "stated",
        }
        for start in (0, len(TEXT) + 1)
    ]
    checker, route_model, _ = service(value)
    barrier = threading.Barrier(2)

    class Parallel:
        def complete_json(self, **kwargs):
            barrier.wait(timeout=5)
            return proposal(state="SUPPORTED")

    checker.composer.model = Parallel()
    result = checker.check(CheckRequest(original_text=original))
    assert [c["claim"]["span"]["start"] for c in result["cards"]] == [0, len(TEXT) + 1]
    assert len(route_model.calls) == 1
    assert all(c["state"] == "SUPPORTED" for c in result["cards"])


@pytest.mark.parametrize("mode", ["rule", "flag", "model", "client", "low_confidence"])
def test_restrictive_routes_skip_retrieval_and_composition(mode):
    text = "Can I change my marriage contract?" if mode == "rule" else TEXT
    value = route_proposal(text)
    if mode == "flag":
        value["level_d"] = True
    elif mode == "model":
        value["level"] = "D"
    elif mode == "low_confidence":
        value["level_confidence"] = 0.1
    checker, router_model, compose_model = service(value)

    class Forbidden:
        def discover(self, *args):
            pytest.fail("Restricted input reached retrieval")

    checker.connector = Forbidden()
    request = CheckRequest(
        original_text=text,
        claims=[{"id": "client", "text_ar": text, "level": "D"}] if mode == "client" else [],
    )
    result = checker.check(request)
    assert all(c["state"] == "CANNOT_CONFIRM" and c["referral"] for c in result["cards"])
    assert not compose_model.calls
    assert len(router_model.calls) == (0 if mode == "rule" else 1)


@pytest.mark.parametrize("mutation", ["span", "source", "duplicate", "nan", "term"])
def test_invalid_router_output_fails_before_compose(mutation):
    value = route_proposal()
    if mutation == "span":
        value["claims"][0]["span"]["end"] += 1
    elif mutation == "source":
        value["claims"][0]["source_text"] = "fabricated source"
    elif mutation == "duplicate":
        value["claims"].append(copy.deepcopy(value["claims"][0]))
    elif mutation == "nan":
        value["level_confidence"] = float("nan")
    elif mutation == "term":
        value["input_kind"] = "term"
    checker, _, compose_model = service(value)
    with pytest.raises(ExtractionError) as caught:
        checker.check(CheckRequest(original_text=TEXT))
    assert caught.value.code == "PIPELINE_DEGRADED"
    assert not compose_model.calls


@pytest.mark.parametrize(
    "decision",
    [
        proposal(state="SUPPORTED", corpus_ids=["fixture:one", "invented"]),
        proposal(state="SUPPORTED", corpus_ids=["fixture:one", "fixture:one"]),
        proposal(state="DISPUTED"),
        proposal(state="CANNOT_CONFIRM"),
    ],
)
def test_state_and_id_proposals_never_override_code_gates(decision):
    checker, _, _ = service(decision=decision)
    result = checker.check(CheckRequest(original_text=TEXT))
    assert result["cards"][0]["state"] == "CANNOT_CONFIRM"
    assert result["cards"][0]["referral"]


def test_original_text_preserves_restrictive_client_context():
    checker, _, compose_model = service()
    result = checker.check(
        CheckRequest(
            original_text=TEXT,
            claims=[{"id": "c1", "text_ar": "Can I change my marriage contract?"}],
        )
    )
    assert result["cards"][0]["claim"]["level"] == "D"
    assert not compose_model.calls


def test_empty_input_returns_no_claims_without_router_call():
    checker, router_model, _ = service()
    with pytest.raises(ExtractionError) as caught:
        checker.check(CheckRequest())
    assert caught.value.code == "NO_CLAIMS" and not router_model.calls


def test_term_is_link_only_until_owner_override_even_if_index_has_definition():
    value = route_proposal(input_kind="term")
    value["claims"][0]["origin"] = "term_lookup"
    checker, _, compose_model = service(value)

    class Forbidden:
        def retrieve(self, *args, **kwargs):
            pytest.fail("Glossary matcher must remain off")

    checker.composer.retriever = Forbidden()
    result = checker.check(CheckRequest(original_text=TEXT))
    card = result["cards"][0]
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["glossary_link"] == "https://islamic-content.com/dictionary"
    assert card["term"] is None and not card["evidence"] and not compose_model.calls


@pytest.mark.parametrize("topics,safe", [(["invented"], True), (["ethics"], False), ([], True)])
def test_router_topics_fail_closed(topics, safe):
    from api.search_phrases import SearchPhraseExtractor

    assert (
        SearchPhraseExtractor(None).from_queries(
            topics, safe_to_search=safe, text=TEXT, claims=[TEXT]
        )
        is None
    )


def test_router_topic_mapping_drops_complete_claim_overlap():
    from api.search_phrases import SearchPhraseExtractor

    assert (
        SearchPhraseExtractor(None).from_queries(
            ["hadith"], safe_to_search=True, text="الحديث", claims=[]
        )
        is None
    )
