"""Request-local deadline shared with parallel provider calls."""

from contextvars import ContextVar

request_deadline: ContextVar[float | None] = ContextVar("request_deadline", default=None)
