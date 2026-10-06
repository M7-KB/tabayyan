"""Router once, request-local retrieval, then parallel claim composition."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError, wait
from contextvars import copy_context
from time import monotonic

from api.check import CheckRequest, CheckService
from api.classifier import rule_level
from api.deadline import request_deadline, request_progress
from api.diagnostics import code, record, timed
from api.extract import ExtractionError
from api.gatekeeper import SourceRequest
from api.provider import ProviderUnavailable


class OnePassCheckService(CheckService):
    def __init__(
        self,
        *,
        router,
        composer,
        corpus_version,
        connector=None,
        search_phrases=None,
        deadline_seconds=35,
        private_indexes=None,
    ):
        super().__init__(
            extractor=router,
            composer=composer,
            corpus_version=corpus_version,
            connector=connector,
            search_phrases=search_phrases,
        )
        self.router = router
        self.deadline_seconds = deadline_seconds
        self.private_indexes = private_indexes

    def check(self, request: CheckRequest, *, source_request: SourceRequest | None = None) -> dict:
        deadline = monotonic() + self.deadline_seconds
        if request_deadline.get() is not None:
            deadline = min(deadline, request_deadline.get())
        token = request_deadline.set(deadline)
        try:
            return self._check(request, source_request=source_request)
        finally:
            request_deadline.reset(token)

    def _remaining(self):
        return max(0, request_deadline.get() - monotonic())

    def _stage(self, action):
        if self._remaining() <= 0:
            raise ExtractionError(503, "CHECK_INCOMPLETE")
        pool = ThreadPoolExecutor(max_workers=1)
        context = copy_context()
        future = pool.submit(context.run, action)
        try:
            return future.result(timeout=self._remaining())
        except TimeoutError:
            record(
                "check_deadline", "CHECK_INCOMPLETE", request_deadline.get() - self.deadline_seconds
            )
            raise ExtractionError(503, "CHECK_INCOMPLETE") from None
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _check(self, request, *, source_request):
        text = request.original_text or "\n".join(c.text_ar for c in request.claims)
        started = monotonic()
        route = self._stage(lambda: self.router.route(text))
        record("routing", "completed", started)
        for routed in route.extracted.claims:
            code(f"classifier:{routed.classifier_status}")
        client_floor = max((c.level for c in request.claims), key="ABCD".index, default="A")
        client_floor = max(
            (client_floor, *(rule_level(c.text_ar) for c in request.claims)), key="ABCD".index
        )
        claims = [
            c.model_copy(update={"level": max((client_floor, c.level), key="ABCD".index)})
            for c in route.extracted.claims
        ]
        if not claims:
            raise ExtractionError(400, "NO_CLAIMS")
        progress = request_progress.get()
        if progress is not None:
            progress.register(self._response([]), [unfinished(claim) for claim in claims])
        restricted = any(c.level == "D" for c in claims)
        started = monotonic()
        source_request = source_request or SourceRequest()
        if self.private_indexes is not None and not restricted:
            try:
                self._stage(
                    lambda: self.private_indexes.discover(
                        text,
                        source_request,
                        kind=route.kind,
                        level=max((c.level for c in claims), key="ABCD".index),
                        timeout=min(3, self._remaining()),
                    )
                )
            except Exception:
                # Discard partial private-index candidates, never invent a miss.
                source_request = SourceRequest()
                record("retrieval_private_index", "unavailable", started)
                result = self._response([])
                result["retryable_results"] = [unfinished(claim) for claim in claims]
                return result
        if self.connector is not None and not restricted and route.kind not in {"verse", "term"}:
            query = self.search_phrases.from_queries(
                route.queries,
                safe_to_search=route.safe_to_search,
                text=text,
                claims=[*(c.text_ar for c in claims), *(c.text_ar for c in request.claims)],
            )
            if query is not None:
                try:
                    self._stage(
                        lambda: self.connector.discover(
                            query, source_request, hadith=route.kind == "hadith"
                        )
                    )
                except ExtractionError as exc:
                    if exc.code != "CHECK_INCOMPLETE":
                        raise
                    result = self._response([])
                    result["retryable_results"] = [unfinished(claim) for claim in claims]
                    record("retrieval", "CHECK_INCOMPLETE", started)
                    return result
        try:
            composer = self._stage(lambda: self.composer.for_request(source_request))
        except ExtractionError as exc:
            if exc.code != "CHECK_INCOMPLETE":
                raise
            result = self._response([])
            result["retryable_results"] = [unfinished(claim) for claim in claims]
            return result
        record("retrieval", "completed", started)

        def compose(claim):
            if self._remaining() <= 0:
                raise ProviderUnavailable("timeout")
            with timed("composition_worker"):
                card = composer.compose(
                    claim,
                    original=text,
                    lang=route.extracted.detected_lang,
                    input_kind=route.extracted.input_kind,
                    no_checkable_claim=route.extracted.no_checkable_claim,
                    propose_state=True,
                    quran_refs=route.quran_refs,
                    hadith_kind=route.kind == "hadith",
                    hadith_phrases=route.hadith_phrases,
                )
            code(card["abstained_reason"] or card["state"])
            if progress is not None:
                progress.complete(claim.id, card)
            return card

        if restricted:
            # Restrict the whole request: no retrieval/composition model call, even
            # when the router split a personal case into some apparent public claims.
            claims = [c.model_copy(update={"level": "D"}) for c in claims]
        started = monotonic()
        pool = ThreadPoolExecutor(max_workers=min(8, len(claims)))
        context = copy_context()
        futures = [pool.submit(context.copy().run, compose, claim) for claim in claims]
        cards, retryable = [], []
        try:
            with timed("composition_wait"):
                done, _ = wait(futures, timeout=self._remaining())
            for claim, future in zip(claims, futures, strict=True):
                if future in done:
                    try:
                        cards.append(future.result())
                        continue
                    except ProviderUnavailable as exc:
                        if exc.category not in {"timeout", "retry_budget"}:
                            raise
                retryable.append(unfinished(claim))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        record("composition", "completed", started)
        result = self._response(cards)
        result["retryable_results"] = retryable
        if retryable:
            record("check_deadline", "CHECK_INCOMPLETE", started)
        return result


def unfinished(claim):
    return {
        "claim_id": claim.id,
        "text_ar": claim.text_ar,
        "code": "CHECK_INCOMPLETE",
        "retryable": True,
        "message_ar": "لم يكتمل التحقق، حاول مرة أخرى",
    }
