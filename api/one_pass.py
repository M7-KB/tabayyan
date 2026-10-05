"""Router once, request-local retrieval, then parallel claim composition."""

from concurrent.futures import ThreadPoolExecutor

from api.check import CheckRequest, CheckService
from api.classifier import rule_level
from api.extract import ExtractionError
from api.gatekeeper import SourceRequest


class OnePassCheckService(CheckService):
    def __init__(self, *, router, composer, corpus_version, connector=None, search_phrases=None):
        super().__init__(
            extractor=router,
            composer=composer,
            corpus_version=corpus_version,
            connector=connector,
            search_phrases=search_phrases,
        )
        self.router = router

    def check(self, request: CheckRequest, *, source_request: SourceRequest | None = None) -> dict:
        text = request.original_text or "\n".join(c.text_ar for c in request.claims)
        route = self.router.route(text)
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
        restricted = any(c.level == "D" for c in claims)
        source_request = source_request or SourceRequest()
        if self.connector is not None and not restricted and route.kind != "term":
            query = self.search_phrases.from_queries(
                route.queries,
                safe_to_search=route.safe_to_search,
                text=text,
                claims=[*(c.text_ar for c in claims), *(c.text_ar for c in request.claims)],
            )
            if query is not None:
                self.connector.discover(query, source_request)
        composer = self.composer.for_request(source_request)

        def compose(claim):
            return composer.compose(
                claim,
                original=text,
                lang=route.extracted.detected_lang,
                input_kind=route.extracted.input_kind,
                no_checkable_claim=route.extracted.no_checkable_claim,
                propose_state=True,
            )

        if restricted:
            # Restrict the whole request: no retrieval/composition model call, even
            # when the router split a personal case into some apparent public claims.
            claims = [c.model_copy(update={"level": "D"}) for c in claims]
        with ThreadPoolExecutor(max_workers=min(8, len(claims))) as pool:
            cards = list(pool.map(compose, claims))
        return self._response(cards)
