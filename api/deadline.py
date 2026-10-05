"""Request-local deadline shared with parallel provider calls."""

from contextvars import ContextVar
from threading import Lock
from time import monotonic

request_deadline: ContextVar[float | None] = ContextVar("request_deadline", default=None)


class RequestProgress:
    """Ephemeral validated results shared with the HTTP deadline owner."""

    def __init__(self):
        self.lock = Lock()
        self.template = None
        self.claims = []
        self.cards = {}
        self.sealed = False

    def register(self, template, unfinished):
        with self.lock:
            if not self.sealed:
                self.template = template
                self.claims = unfinished

    def complete(self, claim_id, card):
        with self.lock:
            if not self.sealed and monotonic() < request_deadline.get():
                self.cards[claim_id] = card

    def snapshot(self):
        with self.lock:
            self.sealed = True
            if self.template is None:
                return None
            result = dict(self.template)
            result["cards"] = [
                self.cards[c["claim_id"]] for c in self.claims if c["claim_id"] in self.cards
            ]
            result["retryable_results"] = [
                c for c in self.claims if c["claim_id"] not in self.cards
            ]
            return result


request_progress: ContextVar[RequestProgress | None] = ContextVar("request_progress", default=None)
