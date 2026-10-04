"""Stateless OpenAI transport for the shared structured-model boundary."""

import json
from typing import Any

import httpx
from jsonschema import Draft202012Validator


class ProviderUnavailable(RuntimeError):
    """Safe failure without provider diagnostics or request content."""


def _reject_constant(value):
    raise ValueError("Non-JSON numeric constant")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class OpenAIStructuredModel:
    def __init__(self, *, api_key: str, model: str, transport=None):
        if not api_key.strip() or not model.strip():
            raise ProviderUnavailable("Provider configuration unavailable")
        self._api_key = api_key
        self._model = model
        self._transport = transport

    def complete_json(
        self, *, instructions: str, data: dict[str, str], schema: dict[str, Any]
    ) -> object:
        # JSON encoding makes delimiters inside user text literal data. It cannot
        # add a developer message or replace the separately supplied instructions.
        payload = {
            "model": self._model,
            "store": False,
            "max_output_tokens": 8192,
            "input": [
                {"role": "developer", "content": instructions},
                {"role": "user", "content": json.dumps({"untrusted_data": data})},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "structured_result",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        try:
            with httpx.Client(timeout=30, transport=self._transport, trust_env=False) as client:
                result = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                result.raise_for_status()
                body = result.json()
            if body.get("status") != "completed":
                raise ValueError("Incomplete response")
            texts = []
            for item in body["output"]:
                if item["type"] == "reasoning":
                    continue
                if item["type"] != "message" or item.get("role") != "assistant":
                    raise ValueError("Unexpected output")
                for content in item["content"]:
                    if content["type"] != "output_text":
                        raise ValueError("Refusal or unexpected content")
                    texts.append(content["text"])
            if len(texts) != 1:
                raise ValueError("Ambiguous output")
            value = json.loads(
                texts[0], parse_constant=_reject_constant, object_pairs_hook=_unique_keys
            )
            Draft202012Validator(schema).validate(value)
            return value
        except Exception:
            # No exception chaining: HTTP errors can include secrets or input.
            raise ProviderUnavailable("Structured provider unavailable") from None
