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
    assert service["plan"] == "free"
    assert service["branch"] == "main"
    assert service["autoDeployTrigger"] == "off"
    assert service["healthCheckPath"] == "/health"
    assert service["buildCommand"] == "python -m pip install ."
    assert service["startCommand"] == (
        "uvicorn api.main:app --host 0.0.0.0 --port $PORT --no-access-log"
    )
    assert {variable["key"] for variable in service["envVars"]} == {
        "HEALTH_ONLY",
        "CORS_ORIGINS",
        "BUILD_SHA",
        "PYTHON_VERSION",
    }
    assert all(
        set(variable) == {"key", "sync"} and variable["sync"] is False
        for variable in service["envVars"]
    )
