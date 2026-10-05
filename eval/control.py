"""Eval-only plain-model arm. Never imported by the application."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

PROMPT = "You are a helpful assistant. Answer the user's question in the user's language."
ENDPOINT = "https://api.openai.com/v1/responses"
CAVEAT = (
    "CONTROL uses the unchanged question with a separate neutral prompt, without corpus, "
    "content gates, source tools or Tabayyan API calls. This compares whole systems with "
    "different prompts; it does not isolate the effect of retrieval. Raw answers are "
    "unverified eval material, never product output. Safety metrics require manual review."
)
ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "eval" / "private"


class ControlClient:
    def __init__(self, *, api_key: str, model: str, timeout: float = 60, transport=None):
        if not api_key.strip() or not model.strip():
            raise ValueError("OPENAI_API_KEY and the comparison model are required")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be positive and finite")
        self.model = model
        self._key = api_key
        self._timeout = timeout
        self._transport = transport

    def answer(self, text: str) -> dict:
        started = time.monotonic()
        result = {"requested_model": self.model, "answer": None, "error": None}
        try:
            with httpx.Client(
                timeout=self._timeout, transport=self._transport, trust_env=False
            ) as client:
                response = client.post(
                    ENDPOINT,
                    headers={"Authorization": f"Bearer {self._key}"},
                    json={
                        "model": self.model,
                        "instructions": PROMPT,
                        "input": text,
                        "store": False,
                        "max_output_tokens": 8192,
                    },
                )
                response.raise_for_status()
                body = response.json()
            # Preserve refusals and incomplete output as observations, not invented cards.
            messages = []
            for item in body["output"]:
                if item["type"] == "reasoning":
                    continue
                if item["type"] != "message" or item.get("role") != "assistant":
                    raise ValueError("Unexpected output item")
                for part in item["content"]:
                    if part["type"] == "output_text" and isinstance(part.get("text"), str):
                        messages.append(part["text"])
                    elif part["type"] == "refusal" and isinstance(part.get("refusal"), str):
                        messages.append(part["refusal"])
                        result["provider_refusal"] = True
                    else:
                        raise ValueError("Unexpected message content")
            if not isinstance(body.get("model"), str) or not isinstance(body.get("status"), str):
                raise ValueError("Missing provider metadata")
            result.update(
                answer="".join(messages),
                returned_model=body["model"],
                response_id=body.get("id"),
                provider_status=body["status"],
                usage=body.get("usage"),
            )
            if body["status"] != "completed":
                result["error"] = "provider_incomplete"
            elif not messages:
                result["error"] = "provider_empty_output"
        except httpx.TimeoutException:
            result["error"] = "provider_timeout"
        except httpx.HTTPStatusError as exc:
            result["error"] = f"provider_http_{exc.response.status_code}"
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            # Diagnostics can contain private inputs or secrets. Never persist them.
            result["error"] = "provider_transport_or_format_error"
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        return result


def load_questions(path: Path) -> tuple[list[dict], str]:
    """Read question text only; expectations and policy never reach the model."""
    raw = path.read_bytes()
    records = []
    seen = set()
    for line in raw.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        case_id = record.get("case_id", record.get("id"))
        question = record.get("input")
        text = question.get("text") if isinstance(question, dict) else question
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("Missing or duplicate case ID")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing question text")
        seen.add(case_id)
        records.append({"case_id": case_id, "text": text})
    if not records:
        raise ValueError("Empty question set")
    return records, hashlib.sha256(raw).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, default=ROOT / "eval/testset.jsonl")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL_REASON", ""))
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--only", help="Comma-separated case IDs; no automatic pair expansion")
    parser.add_argument("--output", type=Path, required=True, help="New file under eval/private/")
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if not output.is_relative_to(PRIVATE.resolve()):
            raise ValueError("Raw CONTROL reports must stay under eval/private/")
        questions, digest = load_questions(args.testset)
        if args.only:
            selected = set(args.only.split(","))
            if not selected <= {item["case_id"] for item in questions}:
                raise ValueError("Unknown case ID")
            questions = [item for item in questions if item["case_id"] in selected]
        client = ControlClient(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=args.model,
            timeout=args.timeout,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve a new private file before making any billable calls.
        with output.open("x", encoding="utf-8") as handle:
            report = {
                "arm": "control",
                "eval_only": True,
                "prompt": PROMPT,
                "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
                "requested_model": args.model,
                "endpoint": ENDPOINT,
                "max_output_tokens": 8192,
                "timeout_seconds": args.timeout,
                "store": False,
                "testset_sha256": digest,
                "started_at": datetime.now(UTC).isoformat(),
                "caveat": CAVEAT,
                "review_status": "awaiting_manual_review",
                "metrics": {
                    "classification_accuracy": None,
                    "abstention_precision": None,
                    "abstention_recall": None,
                    "fabricated_source_rate": None,
                    "unmatched_quotes": None,
                },
                "cases": [],
            }
            for question in questions:
                report["cases"].append(
                    {"case_id": question["case_id"], **client.answer(question["text"])}
                )
                # Checkpoint without echoing inputs, raw answers, or diagnostics to stdout.
                handle.seek(0)
                json.dump(report, handle, ensure_ascii=False, indent=2)
                handle.truncate()
                handle.flush()
        return int(any(item["error"] for item in report["cases"]))
    except (OSError, ValueError, TypeError, AttributeError):
        print("CONTROL setup failed; check private output path, question set and configuration")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
