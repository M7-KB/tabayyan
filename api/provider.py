"""Stateless OpenAI transport for the shared structured-model boundary."""

import copy
import json
import logging
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any

import httpx
from jsonschema import Draft202012Validator

from api.diagnostics import record

logger = logging.getLogger(__name__)


class ProviderUnavailable(RuntimeError):
    """Safe failure without provider diagnostics or request content."""

    def __init__(self, category: str = "invalid_output"):
        self.category = category
        super().__init__("Structured provider unavailable")


def retry_delay(value: str | None) -> float:
    """Accept Retry-After seconds or an HTTP date; never shorten the server delay."""
    if value is None:
        return 0.5
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 0.5
    return max(0.0, delay) if math.isfinite(delay) else math.inf


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
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport=None,
        client: httpx.Client | None = None,
        effort: str = "low",
        timeout: float = 25,
    ):
        if not api_key.strip() or not model.strip():
            raise ProviderUnavailable("configuration")
        if effort not in {"none", "low"} or not math.isfinite(timeout) or timeout <= 0:
            raise ProviderUnavailable("configuration")
        self._api_key = api_key
        self._model = model
        self._effort, self._timeout = effort, timeout
        self._owns_client = client is None
        self._client = client or httpx.Client(transport=transport, trust_env=False)

    def close(self):
        if self._owns_client:
            self._client.close()

    def _post(self, payload):
        deadline = time.monotonic() + self._timeout
        for attempt in range(2):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderUnavailable("timeout")
            try:
                result = self._client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=httpx.Timeout(remaining, connect=min(5, remaining)),
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                category = "timeout" if isinstance(exc, httpx.TimeoutException) else "network"
                if attempt or deadline - time.monotonic() <= 0.5:
                    raise ProviderUnavailable(category) from None
                time.sleep(0.5)
                continue
            if result.status_code in {408, 429, 500, 502, 503, 504} and not attempt:
                delay = retry_delay(result.headers.get("Retry-After"))
                result.close()
                if delay >= deadline - time.monotonic():
                    raise ProviderUnavailable("retry_budget")
                time.sleep(delay)
                continue
            if result.is_error:
                category = (
                    "rate_limit"
                    if result.status_code == 429
                    else "authentication"
                    if result.status_code in {401, 403}
                    else "server"
                    if result.status_code >= 500
                    else "http_error"
                )
                raise ProviderUnavailable(category)
            if time.monotonic() >= deadline:
                raise ProviderUnavailable("timeout")
            return result
        raise ProviderUnavailable("network")

    def warm_schema(self, schema: dict[str, Any]) -> None:
        """Compile the exact schema using synthetic data, never a stored user request."""
        payload = self._payload("Schema warm-up. Return a schema object.", {}, schema)
        payload["max_output_tokens"] = 1
        try:
            body = self._post(payload).json()
            if body.get("status") == "completed":
                return
            if (
                body.get("status") == "incomplete"
                and body.get("incomplete_details", {}).get("reason") == "max_output_tokens"
            ):
                return
            raise ProviderUnavailable("warmup_failed")
        except ProviderUnavailable:
            raise
        except Exception:
            raise ProviderUnavailable("warmup_failed") from None

    def _payload(self, instructions, data, schema):
        schema = copy.deepcopy(schema)

        def strict(node):
            if isinstance(node, dict):
                node.pop("default", None)
                if node.get("type") == "object":
                    node["required"] = list(node.get("properties", {}))
                    node["additionalProperties"] = False
                for value in node.values():
                    strict(value)
            elif isinstance(node, list):
                for value in node:
                    strict(value)

        strict(schema)
        # JSON encoding makes delimiters inside user text literal data. It cannot
        # add a developer message or replace the separately supplied instructions.
        return {
            "model": self._model,
            "reasoning": {"effort": self._effort},
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

    def complete_json(
        self, *, instructions: str, data: dict[str, str], schema: dict[str, Any]
    ) -> object:
        started = monotonic()
        stage = {
            "RouterProposal": "router_provider",
            "ExtractionProposal": "extraction_provider",
            "LevelProposal": "classification_provider",
            "CardProposal": "composition_provider",
            "DecisionProposal": "composition_provider",
        }.get(schema.get("title"), "structured_provider")
        outcome = "invalid_response"
        try:
            payload = self._payload(instructions, data, schema)
            body = self._post(payload).json()
            if body.get("status") != "completed":
                raise ProviderUnavailable("incomplete")
            texts = []
            for item in body["output"]:
                if item["type"] == "reasoning":
                    continue
                if item["type"] != "message" or item.get("role") != "assistant":
                    raise ValueError("Unexpected output")
                for content in item["content"]:
                    if content["type"] != "output_text":
                        raise ProviderUnavailable("refusal")
                    texts.append(content["text"])
            if len(texts) != 1:
                raise ValueError("Ambiguous output")
            value = json.loads(
                texts[0], parse_constant=_reject_constant, object_pairs_hook=_unique_keys
            )
            Draft202012Validator(payload["text"]["format"]["schema"]).validate(value)
            outcome = "completed"
            return value
        except ProviderUnavailable as exc:
            outcome = {
                "timeout": "provider_timeout",
                "network": "transport_error",
                "authentication": "authentication_error",
                "rate_limit": "rate_limited",
                "server": "provider_server_error",
                "http_error": "http_error",
                "retry_budget": "retry_budget",
                "incomplete": "incomplete_response",
                "refusal": "refusal_or_unexpected_content",
            }.get(exc.category, "invalid_response")
            logger.warning("Structured provider failure: category=%s", exc.category)
            raise ProviderUnavailable(exc.category) from None
        except Exception:
            # No exception chaining: HTTP errors can include secrets or input.
            logger.warning("Structured provider failure: category=invalid_output")
            raise ProviderUnavailable("invalid_output") from None
        finally:
            record(stage, outcome, started)
