"""Health-only deployment never loads test policy or corpus artifacts."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


def test_health_only_without_artifacts_or_config(tmp_path, monkeypatch):
    def forbidden_config(*args):
        pytest.fail("Health-only deployment must not load policy or tuning")

    monkeypatch.setattr("api.main.load_config", forbidden_config)
    settings = Settings(
        openai_api_key="inert-test-value",
        health_only=True,
        content_policy_path=tmp_path / "absent-policy.yaml",
        tuning_path=tmp_path / "absent-tuning.yaml",
        build_sha="health-only-build",
        cors_origins=["https://web.example"],
    )
    app = create_app(settings)
    assert {route.path for route in app.routes} == {"/health"}
    with TestClient(app) as client:
        result = client.get("/health", headers={"Origin": "https://web.example"})
        assert result.status_code == 200
        assert result.json() == {
            "status": "degraded",
            "corpus_version": None,
            "corpus_items": 0,
            "corpus_status": "disabled",
            "corpus_error": None,
            "pending_review_items": 0,
            "allow_pending_review": False,
            "policy_version": None,
            "policy_approved_by": "pending",
            "tuning_version": None,
            "card_schema_version": None,
            "build": "health-only-build",
        }
        assert result.headers["access-control-allow-origin"] == "https://web.example"
        assert "inert-test-value" not in result.text
        for path in ("/verify", "/ingest/link", "/transcribe", "/docs", "/openapi.json"):
            response = client.post(path, json={"text": "private-input"})
            assert response.status_code == 404
            assert "private-input" not in response.text


def test_health_only_environment_startup_without_dashboard_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("HEALTH_ONLY", "true")
    with TestClient(create_app(Settings())) as client:
        assert client.get("/health").status_code == 200


def test_health_only_is_explicit_environment_opt_in(monkeypatch):
    monkeypatch.delenv("HEALTH_ONLY", raising=False)
    assert Settings().health_only is False
    monkeypatch.setenv("HEALTH_ONLY", "true")
    assert Settings().health_only is True


def test_blueprint_uses_manual_deploy_and_dashboard_only_values():
    blueprint = yaml.safe_load((Path(__file__).resolve().parents[1] / "render.yaml").read_text())
    (service,) = blueprint["services"]
    assert "plan" not in service  # Owner selects the paid instance in Render.
    assert service["branch"] == "main"
    assert service["autoDeployTrigger"] == "off"
    assert service["healthCheckPath"] == "/health"
    build_command = " ".join(service["buildCommand"].split())
    assert build_command.startswith(
        "python -m pip install . && mkdir -p corpus/private && curl -fsSL "
    )
    assert "Authorization: Bearer $PRIVATE_DATA_TOKEN" in build_command
    assert build_command.endswith(
        "https://api.github.com/repos/M7-KB/tabayyan-private-data/contents/"
        "quran-kfc-v30-20261005.jsonl.xz"
    )
    assert service["startCommand"] == (
        "uvicorn api.main:app --host 0.0.0.0 --port $PORT --no-access-log"
    )
    assert {variable["key"] for variable in service["envVars"]} == {
        "HEALTH_ONLY",
        "CORS_ORIGINS",
        "PYTHON_VERSION",
        "PRIVATE_DATA_TOKEN",
        "PRIVATE_CORPUS_PATH",
        "ALLOW_PENDING_REVIEW",
        "OPENAI_API_KEY",
        "OPENAI_MODEL_EXTRACT",
        "OPENAI_MODEL_REASON",
    }
    assert all(
        set(variable) == {"key", "sync"} and variable["sync"] is False
        for variable in service["envVars"]
    )


def test_build_sha_falls_back_to_render_commit(monkeypatch):
    monkeypatch.delenv("BUILD_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "0123456789abcdef")
    assert Settings().build_sha == "0123456"
    monkeypatch.setenv("BUILD_SHA", "manual-override")
    assert Settings().build_sha == "manual-override"


def test_build_sha_is_unknown_without_render_or_manual_value(monkeypatch):
    monkeypatch.delenv("BUILD_SHA", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert Settings().build_sha == "unknown"


def test_health_reports_render_commit(monkeypatch):
    monkeypatch.delenv("BUILD_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "fedcba9876543210")
    monkeypatch.setenv("HEALTH_ONLY", "true")
    with TestClient(create_app(Settings())) as client:
        assert client.get("/health").json()["build"] == "fedcba9"
