"""Health reports configuration readiness separately from review disclosure."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


@pytest.mark.parametrize("accepted", [False, True])
def test_loaded_pending_corpus_owner_acceptance_only_changes_health(monkeypatch, accepted):
    monkeypatch.setattr(
        "api.main.load_private_corpus", lambda *a, **k: ([{"approved_by": "pending"}], "fixture")
    )
    monkeypatch.setattr(
        "api.main.OpenAIStructuredModel", lambda **k: pytest.fail("health called model")
    )
    settings = Settings(
        openai_api_key="inert",
        openai_model_extract="fixture",
        openai_model_reason="fixture",
        private_corpus_path=Path("unused"),
        allow_pending_review=accepted,
    )
    with TestClient(create_app(settings)) as client:
        body = client.get("/health").json()
    assert body["status"] == ("ok" if accepted else "degraded")
    assert body["review_mode"] == (
        "owner_accepted_pending_review" if accepted else "pending_review"
    )
    assert body["pending_review_items"] == 1
    assert body["policy_approved_by"] == "pending"


@pytest.mark.parametrize(
    "missing",
    ["corpus", "extract_model", "reason_model", "empty_corpus", "corpus_error", "policy", "tuning"],
)
def test_pending_acceptance_cannot_mask_unavailable_runtime(monkeypatch, missing):
    monkeypatch.setattr(
        "api.main.load_private_corpus", lambda *a, **k: ([{"approved_by": "pending"}], "fixture")
    )
    settings = Settings(
        openai_api_key="inert",
        openai_model_extract="" if missing == "extract_model" else "fixture",
        openai_model_reason="" if missing == "reason_model" else "fixture",
        private_corpus_path=None if missing == "corpus" else Path("unused"),
        allow_pending_review=True,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        if missing == "empty_corpus":
            app.state.corpus = []
        if missing == "corpus_error":
            app.state.corpus_error = "fixture failure"
        if missing == "policy":
            app.state.policy = None
        if missing == "tuning":
            app.state.tuning = None
        assert client.get("/health").json()["status"] == "degraded"


def test_reviewed_mode_and_health_only_disclosure(monkeypatch):
    monkeypatch.setattr(
        "api.main.load_private_corpus", lambda *a, **k: ([{"approved_by": "reviewed"}], "fixture")
    )
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_model_extract="fixture",
            openai_model_reason="fixture",
            private_corpus_path=Path("unused"),
        )
    )
    with TestClient(app) as client:
        app.state.policy = app.state.policy.model_copy(update={"approved_by": "reviewed"})
        assert client.get("/health").json()["review_mode"] == "reviewed"
        assert client.get("/health").json()["status"] == "ok"
    with TestClient(create_app(Settings(health_only=True, allow_pending_review=True))) as client:
        body = client.get("/health").json()
        assert body["status"] == "degraded"
        assert body["review_mode"] == "disabled"
