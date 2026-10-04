"""Exercise the shipped P-08 files through the scaffold; no model or religious text."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.config import load_config
from api.main import create_app
from api.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "api/policy/content_policy.yaml"
TUNING = ROOT / "api/tuning.yaml"


def test_shipped_policy_loads_and_health_reports_pending_approval():
    policy, tuning = load_config(POLICY, TUNING)
    settings = Settings(
        openai_api_key="inert-test-value",
        content_policy_path=POLICY,
        tuning_path=TUNING,
    )
    with TestClient(create_app(settings)) as client:
        health = client.get("/health").json()
    assert health["policy_version"] == policy.policy_version == "p1"
    assert health["policy_approved_by"] == policy.approved_by == "pending"
    assert health["tuning_version"] == tuning.tuning_version == "t1"
    assert health["status"] == "degraded"
    assert health["corpus_items"] == 0


@pytest.mark.parametrize("band", ["4", "10", "else"])
def test_shipped_policy_rejects_each_over_ceiling_band(tmp_path, band):
    policy, _ = load_config(POLICY, TUNING)
    data = yaml.safe_load(TUNING.read_text("utf-8"))
    # Keep the table monotone so this reaches the cross-file ceiling check.
    keys = list(data["word_budget_table"])
    for key in keys[keys.index(band) :]:
        data["word_budget_table"][key] = policy.alignment.word_budget_ceiling + 1
    tuning_path = tmp_path / "tuning.yaml"
    tuning_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match=rf"word_budget_table\.{band} exceeds"):
        load_config(POLICY, tuning_path)


def test_policy_rule_references_resolve():
    """Catch dangling rule ids and threshold references without duplicating T-410."""
    policy = yaml.safe_load(POLICY.read_text("utf-8"))
    tuning = yaml.safe_load(TUNING.read_text("utf-8"))
    assert set(policy["state_rules"]) == set(policy["levels"])
    for level, rules in policy["state_rules"].items():
        for rule in rules:
            assert rule["state"] in policy["levels"][level]["allowed_states"]
    rules = policy["alignment_rules"]
    assert len({rule["id"] for rule in rules}) == len(rules)
    for rule in rules:
        if rule["result"] is not None:
            assert rule["result"] in policy["alignment"]["allowed_values"]
        for key, value in rule.get("when", {}).items():
            if key.endswith("_at_least"):
                assert value in tuning


def test_model_confirms_requires_overlap_gate_literal():
    """Pin the approved gate independently of runtime threshold configuration."""
    policy = yaml.safe_load(POLICY.read_text("utf-8"))
    rule = next(rule for rule in policy["alignment_rules"] if rule["id"] == "model_confirms")
    assert rule["when"]["overlap_score_at_least"] == "retrieval_overlap_floor"
    assert "retrieval_score_at_least" not in rule["when"]
