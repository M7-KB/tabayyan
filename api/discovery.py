"""Default source discovery accepts only the minimized public query."""

from api.gatekeeper import SourceRequest
from api.retrieval import tokens


class DefaultDiscovery:
    def __init__(self, *, mcp=None, hadeethenc=None):
        self.mcp = mcp
        self.hadeethenc = hadeethenc

    def discover(self, query: str, request: SourceRequest) -> list:
        if request._used:
            return []
        results = []
        # Hadith discovery is for a disclosed hadith topic, not every question.
        hadith_topic = bool(
            set(tokens(query)) & {"حديث", "الحديث", "احاديث", "الاحاديث", "hadith", "hadeeth"}
        )
        adapters = [self.mcp, self.hadeethenc if hadith_topic else None]
        for adapter in adapters:
            if adapter is None:
                continue
            try:
                results.extend(adapter.discover(query, request))
            except Exception:
                # Keep independent source outages out of user/provider diagnostics.
                # They authorize no evidence; local gates and abstention remain.
                continue
        return results
