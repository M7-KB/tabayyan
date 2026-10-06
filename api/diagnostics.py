"""Request correlation without input, source text or exception messages."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock, get_ident
from time import monotonic

request_id: ContextVar[str] = ContextVar("request_id", default="none")
logger = logging.getLogger(__name__)


@dataclass
class Summary:
    stages: list = field(default_factory=list)
    states: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    codes: list = field(default_factory=list)
    active: dict = field(default_factory=dict)
    sequence: int = 0
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


def count(name: str, value: int) -> None:
    """Add a text-free integer to the request totals; never pass user or source text."""
    current = summary.get()
    if current is not None:
        with current.lock:
            current.counts[name] = current.counts.get(name, 0) + value


def code(value: str) -> None:
    """Record a text-free enum code, such as a classifier status or abstain reason.

    Codes grow by one per claim and one per card in a request. Requests are bounded
    by the router's claim cap (50), so the list stays small.
    """
    current = summary.get()
    if current is not None:
        with current.lock:
            current.codes.append(value)


def finish(outcome, started):
    current = summary.get()
    now = monotonic()
    with current.lock:
        active = [(stage, round((now - began) * 1000)) for stage, began in current.active.values()]
    logger.info(
        "Request summary: request_id=%s outcome=%s elapsed_ms=%d stages=%s states=%s "
        "failures=%s counts=%s codes=%s active_stages=%s",
        request_id.get(),
        outcome,
        round((monotonic() - started) * 1000),
        current.stages,
        current.states,
        current.failures,
        current.counts,
        current.codes,
        active,
    )


def record(stage: str, outcome: str, started: float, *, ended: float | None = None) -> None:
    elapsed = round(((monotonic() if ended is None else ended) - started) * 1000)
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


@contextmanager
def timed(stage):
    started = monotonic()
    current = summary.get()
    handle = None
    if current is not None:
        with current.lock:
            current.sequence += 1
            handle = (get_ident(), current.sequence)
            current.active[handle] = (stage, started)
    outcome = "completed"
    try:
        yield
    except BaseException:
        outcome = "failed"
        raise
    finally:
        if current is not None:
            with current.lock:
                current.active.pop(handle, None)
        record(stage, outcome, started)
