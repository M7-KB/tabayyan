"""Validated v2 index candidates bound to the current request, never source fetches."""

import asyncio

import httpx

from api.bayyinat_matcher import BayyinatMatcher
from api.diagnostics import count, timed
from api.glossary_matcher import GlossaryMatcher
from api.private_index_search import OpenAIIndexEmbedder


class TransientIndexEmbedder:
    """A client per batch avoids sharing async clients across request worker loops."""

    def __init__(self, key, model):
        self.key = key
        self.model = model

    async def embed(self, texts, *, timeout):
        async with httpx.AsyncClient(trust_env=False) as client:
            return await OpenAIIndexEmbedder(client, self.key, model=self.model).embed(
                texts, timeout=timeout
            )


class PrivateShortDiscovery:
    def __init__(self, *, bayyinat=None, glossary=None):
        self.bayyinat = bayyinat
        self.glossary = glossary

    def discover(self, text, request, *, kind, level, timeout):
        if level == "D" or request._used:
            return
        matcher = self.glossary if kind == "term" else self.bayyinat if kind == "doubt" else None
        if matcher is None:
            return
        with timed("retrieval_private_index"):
            candidates = asyncio.run(matcher.candidates(text, level=level, timeout=timeout))
        count("private_index_candidates", len(candidates))
        for candidate in candidates:
            row = candidate.record
            if candidate.source_id == "bayyinat":
                quote = BayyinatMatcher.display_text(row)
                record = {"domain": "faq", "title_ar": row["title"]}
            else:
                quote = GlossaryMatcher.display_text(row)
                # The translation list items are publisher text, copied verbatim; the
                # composer may show the publisher's English item, never a translation.
                record = {
                    "domain": "glossary",
                    "term_ar": row["term_ar"],
                    "translations": [
                        item for item in row.get("translations", []) if isinstance(item, str)
                    ],
                }
            if not quote.strip():
                continue
            request.receive(
                {
                    **record,
                    "source_id": candidate.source_id,
                    "record_ref": row["id"],
                    "source_url": row["url"],
                    "text_ar": quote,
                    # A glossary card is labelled by its term; other records by their page id.
                    "ref": {"label": row["term_ar"] if "term_ar" in record else row["id"]},
                }
            )
