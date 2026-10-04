"""Card sources for the harness: a stub bundle, and the HTTP API of SPEC.md section 3.

Both clients return a ClientResponse. A transport or pipeline failure is carried
as `error` and is reported as a failing case: the harness never treats a missing
response as an absent expectation.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "contracts" / "fixtures"


@dataclass(frozen=True)
class ClientResponse:
    """Cards for one case, or an error explaining why there are none."""

    cards: list[Any] = field(default_factory=list)
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def _merge(base: Any, override: Any) -> Any:
    """Deep-merge dictionaries; any other value, including null, replaces.

    A list is patched by index when the override is an object whose keys are
    index strings (`{"0": {...}}`), so a bundle can change one field of one
    evidence item without restating the fixture's text.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _merge(merged.get(key), value) if key in merged else value
        return merged
    if isinstance(base, list) and isinstance(override, dict):
        patched = list(base)
        for key, value in override.items():
            index = int(key)
            patched[index] = _merge(patched[index], value)
        return patched
    return override


class StubClient:
    """Serve cards from a bundle of overrides applied to the contract fixtures.

    The bundle never carries Arabic source text of its own: every card starts as
    a `contracts/fixtures/*.json` card, so a stub cannot drift away from the
    card contract, and the harness is exercised end to end before the pipeline
    exists. Claim text is filled from the test-set record, which is the user's
    own words, never scripture.
    """

    def __init__(self, bundle_path: Path, fixtures_dir: Path | None = None) -> None:
        self.bundle_path = Path(bundle_path)
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else FIXTURES_DIR
        self.bundle = json.loads(self.bundle_path.read_text(encoding="utf-8"))
        self.arm: str = self.bundle.get("arm", "tabayyan")
        self._cases: dict[str, Any] = self.bundle.get("cases", {})
        self._templates: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return f"stub:{self.bundle_path.name}"

    def _template(self, name: str) -> dict[str, Any]:
        if name not in self._templates:
            path = self.fixtures_dir / f"{name}.json"
            self._templates[name] = json.loads(path.read_text(encoding="utf-8"))
        return json.loads(json.dumps(self._templates[name]))

    def _card(self, record: dict[str, Any], spec: dict[str, Any], template: str) -> dict[str, Any]:
        card = self._template(spec.get("template", template))
        text = record["input"]["text"]
        lang = record["input"]["lang"]
        card["claim"]["text_original"] = text
        card["claim"]["lang"] = lang
        card["claim"]["span"] = {"start": 0, "end": len(text)}
        if lang == "ar":
            # English input keeps the fixture's Arabic rendering; section 4.1 says
            # claim.text_ar is the Arabic text used downstream, not the input echo.
            card["claim"]["text_ar"] = text
        return _merge(card, spec.get("overrides", {}))

    def cards_for(self, record: dict[str, Any]) -> ClientResponse:
        case_id = record["case_id"]
        spec = self._cases.get(case_id)
        if spec is None:
            return ClientResponse(error=f"no stub response for case {case_id}")
        if "error" in spec:
            return ClientResponse(error=str(spec["error"]))
        template = spec.get("template", "")
        cards = [self._card(record, card_spec, template) for card_spec in spec.get("cards", [])]
        return ClientResponse(cards=cards, meta={"arm": self.arm, "stub": self.bundle_path.name})


class HttpApiClient:
    """Call POST /api/v1/extract then POST /api/v1/check (SPEC.md section 3)."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"http:{self.base_url}"

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            return None, f"POST {path} returned {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return None, f"POST {path} failed: {exc}"
        try:
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                return None, f"POST {path} returned a non-object JSON body"
            return decoded, None
        except json.JSONDecodeError as exc:
            return None, f"POST {path} returned invalid JSON: {exc}"

    def cards_for(self, record: dict[str, Any]) -> ClientResponse:
        text = record["input"]["text"]
        extracted, error = self._post("/api/v1/extract", {"text": text, "max_claims": 10})
        if error is not None or extracted is None:
            return ClientResponse(error=error or "extract returned no body")

        raw_claims = extracted.get("claims")
        if not isinstance(raw_claims, list) or any(
            not isinstance(claim, dict) for claim in raw_claims
        ):
            return ClientResponse(error="extract response has no valid claims array")
        claims = [
            {"id": claim.get("id"), "text_ar": claim.get("text_ar"), "level": claim.get("level")}
            for claim in raw_claims
        ]
        if not claims:
            return ClientResponse(error="extract returned no claims")

        payload = {
            "claims": claims,
            "original_text": text,
            "input_kind": extracted.get("input_kind"),
            "locale": record["input"]["lang"],
        }
        checked, error = self._post("/api/v1/check", payload)
        if error is not None or checked is None:
            return ClientResponse(error=error or "check returned no body")

        cards = checked.get("cards")
        if not isinstance(cards, list):
            return ClientResponse(error="check response has no cards array")
        meta = {
            key: checked.get(key)
            for key in (
                "corpus_version",
                "policy_version",
                "tuning_version",
                "card_schema_version",
                "generated_at",
            )
        }
        meta["input_kind"] = extracted.get("input_kind")
        return ClientResponse(cards=cards, meta=meta)
