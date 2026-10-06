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
                # List items are publisher text, not an established English equivalent.
                # Do not synthesize text_en from language names or concatenate them.
                record = {"domain": "glossary", "term_ar": row["term_ar"]}
            if not quote.strip():
                continue
            request.receive(
                {
                    **record,
                    "source_id": candidate.source_id,
                    "record_ref": row["id"],
                    "source_url": row["url"],
                    "text_ar": quote,
                    "ref": {"label": row["id"]},
                }
            )
