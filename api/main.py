"""Application scaffold. Verification endpoints arrive in later tasks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_config
from api.errors import install_handlers
from api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.require_key()
        policy, tuning = load_config(settings.content_policy_path, settings.tuning_path)
        app.state.policy = policy
        app.state.tuning = tuning
        yield

    app = FastAPI(title="Tabayyan API", version="0.1.0", lifespan=lifespan)
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
            "corpus_version": None,
            "corpus_items": 0,
            "policy_version": app.state.policy.policy_version,
            "policy_approved_by": app.state.policy.approved_by,
            "tuning_version": app.state.tuning.tuning_version,
            "card_schema_version": None,
            "build": settings.build_sha,
        }

    return app


app = create_app()
