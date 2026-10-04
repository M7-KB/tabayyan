"""Application scaffold. Verification endpoints arrive in later tasks."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.check import CheckRequest, CheckService
from api.classifier import LevelClassifier
from api.composer import Composer
from api.config import load_config
from api.errors import install_handlers, response
from api.extract import ExtractionError, Extractor, ExtractRequest, ExtractResponse
from api.provider import OpenAIStructuredModel
from api.retrieval import BM25Retriever
from api.settings import Settings
from api.span_detector import DetectorConfig, Record, SpanDetector
from corpus.private_artifact import load_private_corpus
from corpus.validate import CorpusValidationError

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()

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
    )
    install_handlers(app)

    if not settings.health_only:

        @app.post("/api/v1/check")
        def check(request: CheckRequest):
            try:
                if not request.claims:
                    raise ExtractionError(400, "NO_CLAIMS")
                service = getattr(app.state, "checker", None)
                if service is None:
                    key = settings.openai_api_key.get_secret_value()
                    reason = OpenAIStructuredModel(api_key=key, model=settings.openai_model_reason)
                    detector = SpanDetector(
                        [
                            Record(r["corpus_id"], r["domain"], r["text_ar"])
                            for r in app.state.corpus
                        ],
                        DetectorConfig.from_files(
                            settings.content_policy_path, settings.tuning_path
                        ),
                    )
                    extractor = Extractor(
                        model=OpenAIStructuredModel(
                            api_key=key, model=settings.openai_model_extract
                        ),
                        classifier=LevelClassifier(
                            model=reason,
                            policy_path=settings.content_policy_path,
                            tuning_path=settings.tuning_path,
                        ),
                        detector=detector,
                    )
                    service = CheckService(
                        extractor=extractor,
                        composer=Composer(
                            model=reason,
                            retriever=BM25Retriever(app.state.corpus, app.state.tuning),
                            detector=detector,
                            records=app.state.corpus,
                            policy_path=settings.content_policy_path,
                            tuning_path=settings.tuning_path,
                        ),
                        corpus_version=app.state.corpus_version,
                    )
                    # Store only services/indexes, never request data or result cards.
                    app.state.checker = service
                result = service.check(request)
                logger.info(
                    "Check complete: cards=%d states=%s",
                    len(result["cards"]),
                    [card["state"] for card in result["cards"]],
                )
                return result
            except ExtractionError as exc:
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
                    key = settings.openai_api_key.get_secret_value()
                    model = OpenAIStructuredModel(api_key=key, model=settings.openai_model_extract)
                    classifier = LevelClassifier(
                        model=OpenAIStructuredModel(
                            api_key=key, model=settings.openai_model_reason
                        ),
                        policy_path=settings.content_policy_path,
                        tuning_path=settings.tuning_path,
                    )
                    detector = SpanDetector(
                        [
                            Record(r["corpus_id"], r["domain"], r["text_ar"])
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
        return {
            "status": "degraded",
            "corpus_version": app.state.corpus_version,
            "corpus_items": len(app.state.corpus),
            "corpus_status": app.state.corpus_status,
            "corpus_error": app.state.corpus_error,
            "pending_review_items": sum(
                record["approved_by"] == "pending" for record in app.state.corpus
            ),
            "allow_pending_review": settings.allow_pending_review,
            "policy_version": app.state.policy.policy_version if app.state.policy else None,
            "policy_approved_by": app.state.policy.approved_by if app.state.policy else "pending",
            "tuning_version": app.state.tuning.tuning_version if app.state.tuning else None,
            "card_schema_version": "1" if not settings.health_only else None,
            "build": settings.build_sha,
        }

    return app


app = create_app()
