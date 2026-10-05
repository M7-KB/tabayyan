"""Request correlation without input, source text or exception messages."""

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic

request_id: ContextVar[str] = ContextVar("request_id", default="none")
logger = logging.getLogger(__name__)


@dataclass
class Summary:
    stages: list = field(default_factory=list)
    states: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)


summary: ContextVar[Summary | None] = ContextVar("summary", default=None)


def configure_logging():
    api_logger = logging.getLogger("api")
    api_logger.setLevel(logging.INFO)
    if not api_logger.hasHandlers():
        api_logger.addHandler(logging.StreamHandler())


def final_states(cards):
    current = summary.get()
    if current is not None:
        with current.lock:
            current.states = [card["state"] for card in cards]


def finish(outcome, started):
    current = summary.get()
    logger.info(
        "Request summary: request_id=%s outcome=%s elapsed_ms=%d stages=%s states=%s failures=%s",
        request_id.get(),
        outcome,
        round((monotonic() - started) * 1000),
        current.stages,
        current.states,
        current.failures,
    )


def record(stage: str, outcome: str, started: float) -> None:
    elapsed = round((monotonic() - started) * 1000)
    current = summary.get()
    if current is not None:
        with current.lock:
            current.stages.append((stage, outcome, elapsed))
            if outcome not in {"completed", "validated"}:
                current.failures.append(outcome)
    logger.debug(
        "Pipeline diagnostic: request_id=%s stage=%s outcome=%s elapsed_ms=%d",
        request_id.get(),
        stage,
        outcome,
        elapsed,
    )
