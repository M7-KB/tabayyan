"""Application scaffold. Verification endpoints arrive in later tasks."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_config
from api.errors import install_handlers
from api.settings import Settings
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
            "card_schema_version": None,
            "build": settings.build_sha,
        }

    return app


app = create_app()
