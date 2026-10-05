"""Stateless text-check orchestration; client classification is advisory."""

import copy
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, model_validator

from api.composer import Composer
from api.extract import ExtractionError, Extractor, ExtractRequest, StrictObject
from api.gatekeeper import SourceRequest


class CheckClaim(StrictObject):
    id: str = Field(min_length=1, max_length=100)
    text_ar: str = Field(min_length=1, max_length=12000)
    level: Literal["A", "B", "C", "D"] = "A"


class CheckRequest(StrictObject):
    claims: list[CheckClaim] = Field(max_length=50)
    input_kind: Literal["claim", "question", "term"] = "claim"
    locale: Literal["ar", "en"] = "ar"
    original_text: str | None = Field(default=None, min_length=1, max_length=12000)

    @model_validator(mode="after")
    def bounded_input(self):
        if sum(len(c.text_ar) for c in self.claims) > 12000:
            raise ValueError("Combined text exceeds limit")
        if len({c.id for c in self.claims}) != len(self.claims):
            raise ValueError("Duplicate IDs")
        return self


class CheckService:
    def __init__(
        self,
        *,
        extractor: Extractor,
        composer: Composer,
        corpus_version: str | None,
        connector=None,
    ):
        self.extractor, self.composer = extractor, composer
        self.corpus_version = corpus_version
        self.connector = connector

    def check(self, request: CheckRequest, *, source_request: SourceRequest | None = None) -> dict:
        if not request.claims:
            raise ExtractionError(400, "NO_CLAIMS")
        if self.connector is not None and source_request is None:
            # Classification precedes search. Personal cases and unverified term
            # paths never trigger source calls. Re-extraction below uses the
            # complete request-local scripture comparison set.
            text = request.original_text or "\n".join(c.text_ar for c in request.claims)
            preflight = self.extractor.extract(ExtractRequest(text=text, max_claims=50))
            if preflight.dropped_count:
                raise ExtractionError(503, "PIPELINE_DEGRADED")
            source_request = SourceRequest()
            if (
                request.input_kind != "term"
                and preflight.input_kind != "term"
                and all(c.level != "D" for c in preflight.claims)
                and all(c.level != "D" for c in request.claims)
                and all(
                    c.classifier_status in {"model_validated", "rule_forced"}
                    for c in preflight.claims
                )
            ):
                query = " ".join(c.text_ar for c in preflight.claims)[:12000]
                self.connector.discover(query, source_request)
        cards = []
        composer = self.composer.for_request(source_request)
        extractor = copy.copy(self.extractor)
        extractor.detector = composer.detector
        if request.original_text is not None:
            # Re-extract the original input rather than an earlier model paraphrase.
            # This preserves personal-case context, question origin and quote spans.
            extracted = extractor.extract(ExtractRequest(text=request.original_text, max_claims=50))
            if extracted.dropped_count:
                raise ExtractionError(503, "PIPELINE_DEGRADED")
            client_floor = max((c.level for c in request.claims), key="ABCD".index)
            kind = max(
                (request.input_kind, extracted.input_kind),
                key={"claim": 0, "question": 1, "term": 2}.__getitem__,
            )
            for claim in extracted.claims:
                claim = claim.model_copy(
                    update={
                        "level": max((client_floor, claim.level), key="ABCD".index),
                    }
                )
                cards.append(
                    composer.compose(
                        claim,
                        original=request.original_text,
                        lang=extracted.detected_lang,
                        input_kind=kind,
                        no_checkable_claim=extracted.no_checkable_claim,
                    )
                )
            return self._response(cards)
        for submitted in request.claims:
            extracted = extractor.extract(ExtractRequest(text=submitted.text_ar, max_claims=50))
            if extracted.dropped_count:
                raise ExtractionError(503, "PIPELINE_DEGRADED")
            kind = max(
                (request.input_kind, extracted.input_kind),
                key={"claim": 0, "question": 1, "term": 2}.__getitem__,
            )
            for claim in extracted.claims:
                claim = claim.model_copy(
                    update={
                        "id": submitted.id
                        if len(extracted.claims) == 1
                        else f"{submitted.id}:{claim.id}",
                        "level": max((submitted.level, claim.level), key="ABCD".index),
                    }
                )
                cards.append(
                    composer.compose(
                        claim,
                        original=submitted.text_ar,
                        lang=extracted.detected_lang,
                        input_kind=kind,
                        no_checkable_claim=extracted.no_checkable_claim,
                    )
                )
                if len(cards) > 50:
                    raise ExtractionError(503, "PIPELINE_DEGRADED")
        return self._response(cards)

    def _response(self, cards: list[dict]) -> dict:
        return {
            "cards": cards,
            "corpus_version": self.corpus_version,
            "policy_version": self.composer.metadata.policy_version,
            "tuning_version": self.composer.tuning.tuning_version,
            "card_schema_version": "1",
            "disclaimer_ar": "هذه أداة ذكاء اصطناعي، وليست فتوى.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
