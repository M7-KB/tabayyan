"""Request correlation without input, source text or exception messages."""

import logging
from contextvars import ContextVar
from time import monotonic

request_id: ContextVar[str] = ContextVar("request_id", default="none")
logger = logging.getLogger(__name__)


def record(stage: str, outcome: str, started: float) -> None:
    logger.info(
        "Pipeline diagnostic: request_id=%s stage=%s outcome=%s elapsed_ms=%d",
        request_id.get(),
        stage,
        outcome,
        round((monotonic() - started) * 1000),
    )
