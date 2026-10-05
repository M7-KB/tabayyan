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


def test_unparseable_router_output_fails_before_compose():
    value = route_proposal()
    value["level_confidence"] = float("nan")
    checker, _, compose_model = service(value)
    with pytest.raises(ExtractionError) as caught:
        checker.check(CheckRequest(original_text=TEXT))
    assert caught.value.code == "PIPELINE_DEGRADED"
    assert not compose_model.calls


@pytest.mark.parametrize("mutation", ["span", "source", "duplicate", "term"])
def test_router_shape_problems_fall_back_to_whole_input(mutation):
    # Model character offsets are unreliable. Shape problems never fail the
    # request: the input is kept whole as one claim and the gates still apply.
    value = route_proposal()
    if mutation == "span":
        value["claims"][0]["span"]["end"] += 1
    elif mutation == "source":
        value["claims"][0]["source_text"] = "fabricated source"
    elif mutation == "duplicate":
        value["claims"].append(copy.deepcopy(value["claims"][0]))
    elif mutation == "term":
        value["input_kind"] = "term"
    checker, router_model, _ = service(value)
    result = checker.check(CheckRequest(original_text=TEXT))
    assert len(result["cards"]) == 1
    card = result["cards"][0]["claim"]
    assert card["text_original"] == TEXT
    assert "fabricated" not in card["text_ar"]
    assert len(router_model.calls) <= 2


@pytest.mark.parametrize("origin", ["presupposition", "term_lookup", "stated"])
def test_absent_source_text_discards_generated_claim_for_every_origin(origin):
    # An invented source_text means the claim text is ungrounded model output.
    # It must never reach composition; the whole input replaces it.
    value = route_proposal()
    value["claims"][0].update(
        origin=origin, source_text="unrelated fruit storage", text_ar="Fruit must be sealed."
    )
    if origin == "term_lookup":
        value["input_kind"] = "term"
    checker, router_model, _ = service(value)
    result = checker.check(CheckRequest(original_text=TEXT))
    assert len(result["cards"]) == 1
    card = result["cards"][0]["claim"]
    assert card["text_ar"] == TEXT
    assert "Fruit" not in card["text_ar"]
    assert len(router_model.calls) == 1


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


def test_deadline_preserves_completed_cards_and_marks_unfinished_claims():
    from time import monotonic

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
    checker, _, _ = service(value)
    checker.deadline_seconds = 0.1
    release = threading.Event()
    composer = checker.composer
    bound = composer.for_request

    def for_request(request):
        current = bound(request)
        compose = current.compose

        def delayed(claim, **kwargs):
            if claim.id == "c2":
                release.wait(timeout=2)
            return compose(claim, **kwargs)

        current.compose = delayed
        return current

    composer.for_request = for_request
    started = monotonic()
    try:
        result = checker.check(CheckRequest(original_text=original))
        assert monotonic() - started < 0.5
        assert [c["claim"]["id"] for c in result["cards"]] == ["c1"]
        assert result["retryable_results"][0]["claim_id"] == "c2"
        assert result["retryable_results"][0]["retryable"] is True
        assert "state" not in result["retryable_results"][0]
    finally:
        release.set()


def test_router_deadline_is_retryable_http_failure():
    checker, _, _ = service()
    release = threading.Event()
    route = checker.router.route
    checker.deadline_seconds = 0.05
    checker.router.route = lambda text: (release.wait(timeout=2), route(text))[1]
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = checker
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/check", json={"original_text": TEXT})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "CHECK_INCOMPLETE"
    finally:
        release.set()


def test_composer_provider_timeout_is_unfinished_not_abstention():
    from api.provider import ProviderUnavailable

    checker, _, _ = service()

    class Timeout:
        def complete_json(self, **kwargs):
            raise ProviderUnavailable("timeout")

    checker.composer.model = Timeout()
    result = checker.check(CheckRequest(original_text=TEXT))
    assert result["cards"] == []
    assert result["retryable_results"][0]["code"] == "CHECK_INCOMPLETE"


def test_retrieval_deadline_keeps_known_claim_retryable():
    checker, _, _ = service()
    checker.deadline_seconds = 0.05
    release = threading.Event()

    class Slow:
        def discover(self, query, source_request, *, hadith=False):
            release.wait(timeout=2)

    checker.connector = Slow()
    try:
        result = checker.check(CheckRequest(original_text=TEXT))
        assert result["cards"] == []
        assert result["retryable_results"][0]["claim_id"] == "c1"
    finally:
        release.set()


def test_provider_budget_is_capped_by_request_deadline():
    import json
    from time import monotonic

    import httpx

    from api.deadline import request_deadline
    from api.provider import OpenAIStructuredModel
    from tests.test_provider import body, run

    def handler(request):
        assert request.extensions["timeout"]["read"] <= 1
        assert json.loads(request.content)["store"] is False
        return httpx.Response(200, json=body())

    token = request_deadline.set(monotonic() + 1)
    try:
        model = OpenAIStructuredModel(
            api_key="inert", model="configured", transport=httpx.MockTransport(handler)
        )
        assert run(model)["level"] == "B"
    finally:
        request_deadline.reset(token)


def test_binding_deadline_retains_claims_without_composition_dispatch():
    from time import monotonic

    checker, _, model = service()
    checker.deadline_seconds = 0.05
    release = threading.Event()
    bound = checker.composer.for_request
    checker.composer.for_request = lambda request: (release.wait(timeout=2), bound(request))[1]
    started = monotonic()
    try:
        result = checker.check(CheckRequest(original_text=TEXT))
        assert monotonic() - started < 0.5
        assert result["cards"] == []
        assert result["retryable_results"][0]["claim_id"] == "c1"
        assert not model.calls
    finally:
        release.set()


def test_first_request_service_setup_is_inside_http_deadline(monkeypatch):
    import asyncio
    from time import sleep

    from api.provider import ProviderUnavailable

    actual_wait = asyncio.wait_for

    async def short_wait(awaitable, *, timeout):
        return await actual_wait(awaitable, timeout=0.05)

    class SlowSetup:
        def __init__(self, **kwargs):
            sleep(0.2)
            raise ProviderUnavailable("configuration")

    monkeypatch.setattr("api.main.asyncio.wait_for", short_wait)
    monkeypatch.setattr("api.main.OpenAIStructuredModel", SlowSetup)
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    with TestClient(app) as client:
        result = client.post("/api/v1/check", json={"original_text": TEXT})
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "CHECK_INCOMPLETE"


@pytest.mark.parametrize("attempt", range(3))
def test_outer_http_deadline_retains_completed_cards(attempt, monkeypatch):
    import asyncio
    from time import monotonic

    from api.deadline import request_deadline, request_progress

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
    checker, _, _ = service(value)
    checker.deadline_seconds = 0.1
    release = threading.Event()
    bound = checker.composer.for_request

    def for_request(request):
        current = bound(request)
        compose = current.compose

        def delayed(claim, **kwargs):
            if claim.id == "c2":
                release.wait(timeout=1)
            return compose(claim, **kwargs)

        current.compose = delayed
        return current

    checker.composer.for_request = for_request
    actual_wait = asyncio.wait_for

    async def shared_deadline(awaitable, *, timeout):
        request_deadline.set(monotonic() + 0.1)
        return await actual_wait(awaitable, timeout=0.1)

    monkeypatch.setattr("api.main.asyncio.wait_for", shared_deadline)
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = checker
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/check", json={"original_text": original})
        assert response.status_code == 200
        result = response.json()
        assert [card["claim"]["id"] for card in result["cards"]] == ["c1"]
        assert result["cards"][0]["state"] == "SUPPORTED"
        assert [item["claim_id"] for item in result["retryable_results"]] == ["c2"]
        assert request_progress.get() is None
    finally:
        release.set()


def test_sealed_http_snapshot_ignores_late_results():
    from time import monotonic

    from api.deadline import RequestProgress, request_deadline

    progress = RequestProgress()
    progress.register({"cards": []}, [{"claim_id": "c1", "retryable": True}])
    token = request_deadline.set(monotonic() + 1)
    try:
        progress.complete("c1", {"state": "SUPPORTED"})
        snapshot = progress.snapshot()
        progress.complete("c1", {"state": "CANNOT_CONFIRM"})
        assert snapshot["cards"] == [{"state": "SUPPORTED"}]
        assert progress.snapshot() == snapshot
    finally:
        request_deadline.reset(token)


@pytest.mark.parametrize("kind,hadith", [("hadith", True), ("other", False)])
def test_hadeethenc_flag_follows_router_kind_only(kind, hadith):
    checker, _, _ = service(route_proposal(TEXT, input_kind=kind))
    seen = []

    class Connector:
        def discover(self, query, source_request, *, hadith=False):
            seen.append(hadith)
            return []

    checker.connector = Connector()
    checker.check(CheckRequest(original_text=TEXT))
    assert seen == [hadith]
