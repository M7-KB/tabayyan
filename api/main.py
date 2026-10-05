"""Application scaffold. Verification endpoints arrive in later tasks."""

import asyncio
import logging
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.check import CheckRequest
from api.classifier import LevelClassifier, LevelProposal
from api.composer import Composer, DecisionProposal
from api.config import load_config
from api.deadline import request_deadline
from api.diagnostics import (
    Summary,
    configure_logging,
    final_states,
    finish,
    record,
    request_id,
    summary,
)
from api.discovery import DefaultDiscovery
from api.errors import install_handlers, response
from api.extract import (
    ExtractionError,
    ExtractionProposal,
    Extractor,
    ExtractRequest,
    ExtractResponse,
)
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.hadeethenc_discovery import HadeethEncDiscovery
from api.islamic_mcp import IslamicContentConnector
from api.one_pass import OnePassCheckService
from api.provider import OpenAIStructuredModel, ProviderUnavailable
from api.retrieval import BM25Retriever
from api.router import Router, RouterProposal
from api.settings import Settings
from api.span_detector import DetectorConfig, Record, SpanDetector
from corpus.private_artifact import load_private_corpus
from corpus.quran_binding import matching_text
from corpus.validate import CorpusValidationError

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings if settings is not None else Settings()

    def model_adapter(app, *, router=False):
        return OpenAIStructuredModel(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model_extract if router else settings.openai_model_reason,
            effort=settings.openai_router_effort if router else settings.openai_composer_effort,
            timeout=15 if router else 25,
            client=app.state.provider_client,
        )

    def warm(app, router, schema):
        try:
            model_adapter(app, router=router).warm_schema(schema)
        except ProviderUnavailable as exc:
            logger.warning("Provider warm-up failure: category=%s", exc.category)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        policy, tuning = (None, None)
        records, corpus_version = [], None
        corpus_status = "disabled" if settings.health_only else "not_configured"
        corpus_error = None
        if not settings.health_only:
            settings.require_key()
            policy, tuning = load_config(settings.content_policy_path, settings.tuning_path)
            if settings.private_corpus_path is not None:
                try:
                    records, corpus_version = load_private_corpus(
                        settings.private_corpus_path,
                        settings.corpus_manifest_path,
                        allow_pending_review=settings.allow_pending_review,
                    )
                except CorpusValidationError as exc:
                    corpus_status = "unavailable"
                    corpus_error = str(exc)
                    logger.warning("Private corpus unavailable: %s", corpus_error)
                else:
                    corpus_status = "loaded"
        app.state.policy = policy
        app.state.tuning = tuning
        app.state.corpus = records
        app.state.corpus_version = corpus_version
        app.state.corpus_status = corpus_status
        app.state.corpus_error = corpus_error
        # One connection pool shared across models and requests; never stores request data.
        with httpx.Client(trust_env=False) as provider_client:
            app.state.provider_client = provider_client
            if (
                not settings.health_only
                and settings.openai_schema_warmup
                and settings.openai_model_extract
                and settings.openai_model_reason
            ):
                await asyncio.gather(
                    asyncio.to_thread(warm, app, True, RouterProposal.model_json_schema()),
                    asyncio.to_thread(warm, app, False, DecisionProposal.model_json_schema()),
                    asyncio.to_thread(warm, app, True, ExtractionProposal.model_json_schema()),
                    asyncio.to_thread(warm, app, False, LevelProposal.model_json_schema()),
                )
            yield

    app = FastAPI(
        title="Tabayyan API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.health_only else "/docs",
        redoc_url=None if settings.health_only else "/redoc",
        openapi_url=None if settings.health_only else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    install_handlers(app)

    @app.middleware("http")
    async def diagnostic_request(request, call_next):
        stage = {"/api/v1/extract": "extract", "/api/v1/check": "check"}.get(request.url.path)
        if stage is None:
            return await call_next(request)
        token = request_id.set(uuid4().hex)
        summary_token = summary.set(Summary())
        started = monotonic()
        deadline_token = request_deadline.set(started + 35 if stage == "check" else None)
        outcome = "unhandled_failure"
        try:
            try:
                result = (
                    await asyncio.wait_for(call_next(request), timeout=35)
                    if stage == "check"
                    else await call_next(request)
                )
            except TimeoutError:
                record("check_deadline", "CHECK_INCOMPLETE", started)
                result = response(
                    503,
                    "CHECK_INCOMPLETE",
                    "Check unfinished; please retry",
                    "لم يكتمل التحقق، حاول مرة أخرى",
                )
            outcome = "completed" if result.status_code < 400 else "http_failure"
            result.headers["X-Request-ID"] = request_id.get()
            return result
        finally:
            record(stage, outcome, started)
            finish(outcome, started)
            summary.reset(summary_token)
            request_deadline.reset(deadline_token)
            request_id.reset(token)

    if not settings.health_only:

        @app.post("/api/v1/check")
        def check(request: CheckRequest):
            try:
                if not request.claims and not request.original_text:
                    raise ExtractionError(400, "NO_CLAIMS")
                service = getattr(app.state, "checker", None)
                if service is None:
                    reason = model_adapter(app)
                    gatekeeper = QuoteGatekeeper(
                        local_records=app.state.corpus,
                        request=SourceRequest(),
                        detector_config=DetectorConfig.from_files(
                            settings.content_policy_path, settings.tuning_path
                        ),
                    )
                    detector = gatekeeper.detector
                    router = Router(
                        model=model_adapter(app, router=True),
                        classifier=LevelClassifier(
                            model=reason,
                            policy_path=settings.content_policy_path,
                            tuning_path=settings.tuning_path,
                        ),
                        detector=detector,
                    )
                    service = OnePassCheckService(
                        router=router,
                        composer=Composer(
                            model=reason,
                            retriever=BM25Retriever(app.state.corpus, app.state.tuning),
                            detector=detector,
                            records=app.state.corpus,
                            policy_path=settings.content_policy_path,
                            tuning_path=settings.tuning_path,
                            gatekeeper=gatekeeper,
                        ),
                        corpus_version=app.state.corpus_version,
                        connector=DefaultDiscovery(
                            mcp=IslamicContentConnector()
                            if settings.islamic_content_mcp_url
                            else None,
                            hadeethenc=HadeethEncDiscovery(),
                        ),
                    )
                    # Store only services/indexes, never request data or result cards.
                    app.state.checker = service
                result = service.check(request)
                final_states(result["cards"])
                return result
            except ExtractionError as exc:
                if exc.code == "CHECK_INCOMPLETE":
                    return response(
                        503,
                        exc.code,
                        "Check unfinished; please retry",
                        "لم يكتمل التحقق، حاول مرة أخرى",
                    )
                return response(
                    exc.status, exc.code, "Check could not be completed", "تعذر إتمام التحقق"
                )
            except Exception:
                return response(503, "PIPELINE_DEGRADED", "Check unavailable", "التحقق غير متاح")

        @app.post("/api/v1/extract", response_model=ExtractResponse)
        def extract(request: ExtractRequest):
            try:
                if not request.text.strip():
                    raise ExtractionError(400, "NO_CLAIMS")
                # Construction is lazy so health checks do not call the provider.
                # Tests can inject the same swappable service through app.state.
                service = getattr(app.state, "extractor", None)
                if service is None:
                    model = model_adapter(app, router=True)
                    classifier = LevelClassifier(
                        model=model_adapter(app),
                        policy_path=settings.content_policy_path,
                        tuning_path=settings.tuning_path,
                    )
                    detector = SpanDetector(
                        [
                            Record(r["corpus_id"], r["domain"], matching_text(r))
                            for r in app.state.corpus
                        ],
                        DetectorConfig.from_files(
                            settings.content_policy_path,
                            settings.tuning_path,
                        ),
                    )
                    service = Extractor(model=model, classifier=classifier, detector=detector)
                return service.extract(request)
            except ExtractionError as exc:
                return response(
                    exc.status,
                    exc.code,
                    "Extraction could not be completed",
                    "تعذر إتمام استخراج الادعاءات",
                )
            except Exception:
                return response(
                    503, "PIPELINE_DEGRADED", "Extraction unavailable", "استخراج الادعاءات غير متاح"
                )

    @app.get("/health")
    async def health() -> dict:
        pending_items = sum(record["approved_by"] == "pending" for record in app.state.corpus)
        pending_review = pending_items > 0 or (
            app.state.policy is not None and app.state.policy.approved_by == "pending"
        )
        review_mode = (
            "disabled"
            if settings.health_only
            else "owner_accepted_pending_review"
            if pending_review and settings.allow_pending_review
            else "pending_review"
            if pending_review
            else "reviewed"
        )
        configured = (
            not settings.health_only
            and app.state.corpus_status == "loaded"
            and bool(app.state.corpus)
            and app.state.corpus_error is None
            and app.state.policy is not None
            and app.state.tuning is not None
            and bool(settings.openai_model_extract.strip())
            and bool(settings.openai_model_reason.strip())
        )
        return {
            "status": "ok"
            if configured and (not pending_review or settings.allow_pending_review)
            else "degraded",
            "review_mode": review_mode,
            "corpus_version": app.state.corpus_version,
            "corpus_items": len(app.state.corpus),
            "corpus_status": app.state.corpus_status,
            "corpus_error": app.state.corpus_error,
            "pending_review_items": pending_items,
            "allow_pending_review": settings.allow_pending_review,
            "policy_version": app.state.policy.policy_version if app.state.policy else None,
            "policy_approved_by": app.state.policy.approved_by if app.state.policy else "pending",
            "tuning_version": app.state.tuning.tuning_version if app.state.tuning else None,
            "card_schema_version": "1" if not settings.health_only else None,
            "build": settings.build_sha,
        }

    return app


app = create_app()
