"""Plain-model boundary tests use synthetic text and mocked transport only."""

import json
from pathlib import Path

import httpx
import pytest

from eval import control


def response(**updates):
    return {
        "id": "synthetic-response",
        "model": "synthetic-model-snapshot",
        "status": "completed",
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "unverified synthetic answer"}],
            },
        ],
        "usage": {"input_tokens": 2, "output_tokens": 3},
        **updates,
    }


def test_exact_prompt_and_unchanged_question_are_the_entire_model_context():
    question = "  synthetic question\nwith instructions-looking data  "
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == control.ENDPOINT
        assert json.loads(request.content) == {
            "model": "synthetic-model",
            "instructions": (
                "You are a helpful assistant. Answer the user's question in the user's language."
            ),
            "input": question,
            "store": False,
            "max_output_tokens": 8192,
        }
        return httpx.Response(200, json=response())

    result = control.ControlClient(
        api_key="synthetic-key", model="synthetic-model", transport=httpx.MockTransport(handler)
    ).answer(question)
    assert len(requests) == 1
    assert result["answer"] == "unverified synthetic answer"
    assert result["returned_model"] == "synthetic-model-snapshot"
    assert result["error"] is None


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_partial_answers_remain_visible_to_reviewer_but_are_errors(status):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=response(status=status)))
    result = control.ControlClient(api_key="key", model="model", transport=transport).answer("x")
    assert result["answer"] == "unverified synthetic answer"
    assert result["error"] == "provider_incomplete"


def test_provider_refusal_is_preserved_without_becoming_an_abstention_score():
    body = response()
    body["output"][1]["content"] = [{"type": "refusal", "refusal": "synthetic refusal"}]
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    result = control.ControlClient(api_key="key", model="model", transport=transport).answer("x")
    assert result["answer"] == "synthetic refusal"
    assert result["provider_refusal"] is True
    assert "state" not in result


@pytest.mark.parametrize("body", [None, [], {}, {"output": []}])
def test_malformed_provider_output_is_a_transport_error(body):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    result = control.ControlClient(api_key="key", model="model", transport=transport).answer("x")
    assert result["error"] == "provider_transport_or_format_error"


def test_error_body_and_credentials_are_never_in_the_result():
    transport = httpx.MockTransport(lambda _: httpx.Response(401, text="private input secret key"))
    result = control.ControlClient(api_key="secret-key", model="model", transport=transport).answer(
        "private input"
    )
    assert result["error"] == "provider_http_401"
    assert "private input" not in json.dumps(result)
    assert "secret" not in json.dumps(result)


def test_timeout_is_recorded_without_retry():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("private diagnostics")

    result = control.ControlClient(
        api_key="key", model="model", transport=httpx.MockTransport(handler)
    ).answer("x")
    assert result["error"] == "provider_timeout"
    assert len(calls) == 1


def test_load_questions_accepts_both_shapes_without_changing_text(tmp_path):
    path = tmp_path / "questions.jsonl"
    path.write_text(
        json.dumps({"case_id": "T01", "input": {"text": " x \n"}, "expect": "ignored"})
        + "\n"
        + json.dumps({"id": "H01", "input": "y", "notes": "ignored"}),
        encoding="utf-8",
    )
    questions, digest = control.load_questions(path)
    assert questions == [{"case_id": "T01", "text": " x \n"}, {"case_id": "H01", "text": "y"}]
    assert len(digest) == 64


@pytest.mark.parametrize(
    "records",
    [[], [{"id": "a", "input": " "}], [{"id": "a", "input": "x"}] * 2],
)
def test_empty_or_duplicate_questions_are_setup_errors(tmp_path, records):
    path = tmp_path / "invalid.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    with pytest.raises(ValueError):
        control.load_questions(path)


def test_private_report_has_no_question_echo_and_no_automatic_safety_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "PRIVATE", tmp_path / "private")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    path = tmp_path / "questions.jsonl"
    path.write_text('{"id":"H01","input":"private synthetic question"}', encoding="utf-8")
    monkeypatch.setattr(
        control.ControlClient, "answer", lambda self, text: {"answer": "synthetic", "error": None}
    )
    output = tmp_path / "private/report.json"
    assert (
        control.main(["--testset", str(path), "--model", "synthetic", "--output", str(output)]) == 0
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["prompt"] == control.PROMPT
    assert report["caveat"] == control.CAVEAT
    assert report["review_status"] == "awaiting_manual_review"
    assert all(value is None for value in report["metrics"].values())
    assert "private synthetic question" not in output.read_text(encoding="utf-8")


def test_public_output_and_existing_report_fail_before_any_call(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "PRIVATE", tmp_path / "private")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    path = tmp_path / "questions.jsonl"
    path.write_text('{"id":"H01","input":"synthetic"}', encoding="utf-8")

    def forbidden(*args):
        pytest.fail("No call is allowed for invalid or existing output")

    monkeypatch.setattr(control.ControlClient, "answer", forbidden)
    assert control.main(["--output", str(tmp_path / "public.json")]) == 2
    output = tmp_path / "private/report.json"
    output.parent.mkdir()
    output.write_text("existing", encoding="utf-8")
    assert (
        control.main(["--testset", str(path), "--model", "synthetic", "--output", str(output)]) == 2
    )
    assert output.read_text(encoding="utf-8") == "existing"


def test_control_is_not_imported_by_product():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "api").rglob("*.py"):
        assert "eval.control" not in path.read_text(encoding="utf-8")


def test_force_added_private_eval_files_are_rejected():
    from corpus.check_public_tree import is_private_artifact

    assert is_private_artifact("eval/private/questions.jsonl")
    assert is_private_artifact("eval/private/raw-report.json")
    assert not is_private_artifact("eval/control.py")
