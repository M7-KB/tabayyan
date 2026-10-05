"""Default source discovery accepts only the minimized public query."""

from concurrent.futures import ThreadPoolExecutor, wait
from contextvars import copy_context
from time import monotonic

from api.deadline import request_deadline
from api.diagnostics import record
from api.gatekeeper import SourceRequest


class DefaultDiscovery:
    TIMEOUT = 3.0

    def __init__(self, *, mcp=None, hadeethenc=None):
        self.mcp = mcp
        self.hadeethenc = hadeethenc

    def discover(self, query: str, request: SourceRequest, *, hadith: bool = False) -> list:
        if request._used:
            return []
        results = []
        # HadeethEnc runs only when the router classified the input as a hadith check.
        adapters = [
            (name, adapter)
            for name, adapter in (("mcp", self.mcp), ("hadeethenc", self.hadeethenc))
            if adapter is not None and (name != "hadeethenc" or hadith)
        ]
        if not adapters:
            return []
        started = monotonic()
        deadline = min(started + self.TIMEOUT, request_deadline.get() or float("inf"))
        if deadline <= started:
            return []

        def discover(adapter, scope):
            token = request_deadline.set(deadline)
            try:
                return adapter.discover(query, scope), monotonic()
            except Exception:
                return None, monotonic()
            finally:
                request_deadline.reset(token)

        pool = ThreadPoolExecutor(max_workers=len(adapters))
        jobs = []
        try:
            for name, adapter in adapters:
                # Late workers cannot mutate the request used by composition.
                scope = SourceRequest()
                context = copy_context()
                source_started = monotonic()
                future = pool.submit(context.run, discover, adapter, scope)
                jobs.append((name, scope, future, source_started))
            done, _ = wait([j[2] for j in jobs], timeout=max(0, deadline - monotonic()))
            for name, scope, future, source_started in jobs:
                scope._used = True
                if future not in done:
                    future.cancel()
                    record(f"retrieval_{name}", "timeout", source_started)
                    continue
                received, ended = future.result()
                if ended > deadline:
                    record(f"retrieval_{name}", "timeout", source_started, ended=deadline)
                    continue
                record(
                    f"retrieval_{name}",
                    "completed" if received is not None else "unavailable",
                    source_started,
                    ended=ended,
                )
                if received is not None:
                    for receipt in received:
                        if receipt.request_token is scope._token:
                            results.append(request.receive(receipt.record))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        return results
