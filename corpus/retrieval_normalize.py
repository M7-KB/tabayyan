# SPDX-License-Identifier: MIT
"""Arabic search aliases only; never source/display text or quote authorization."""

import re

from corpus.normalize import normalize_arabic

RETRIEVAL_NORMALIZER_VERSION = "ar-search-v1"
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)
_ARABIC_WORD = re.compile(r"^[\u0621-\u063a\u0641-\u064a]+$")
# Ordered longest first: conjunction, preposition, article; contracted l+al = ll.
# These are search possibilities, not a morphological analysis or a claim of meaning.
_PREFIXES = tuple(
    sorted(
        {
            conjunction + prefix
            for conjunction in ("", "و", "ف")
            for prefix in ("", "ب", "ك", "ل", "ال", "بال", "كال", "لل")
            if conjunction or prefix
        },
        key=lambda value: (-len(value), value),
    )
)


def retrieval_token_groups(text: str) -> tuple[tuple[str, ...], ...]:
    """One group per input word: original ar-v1 key followed by prefix aliases.

    Keep originals because initial waw/fa/ba/kaf/lam may belong to the stem.
    Strip only a known prefix sequence and leave at least three Arabic letters.
    Never strip suffixes, stem roots, remove stopwords or rewrite the question.
    Groups let a matcher count one word once even if several aliases match.
    These lossy aliases find candidates; all evidence and intent gates still apply.
    """
    words = _WORDS.findall(normalize_arabic(text).casefold())
    result = []
    for word in words:
        variants = [word]
        if _ARABIC_WORD.fullmatch(word):
            for prefix in _PREFIXES:
                remainder = word[len(prefix) :]
                if word.startswith(prefix) and len(remainder) >= 3 and remainder not in variants:
                    variants.append(remainder)
        result.append(tuple(variants))
    return tuple(result)


def retrieval_tokens(text: str) -> tuple[str, ...]:
    """Flatten search groups for an index; use groups when calculating query overlap.

    Caller must avoid treating aliases as independent evidence or query words.
    This utility does not change legacy BM25, ar-v1 corpus checksums, or span gates.
    R4 matchers and V3 Quran retrieval opt in at their own integration boundary.
    """
    return tuple(alias for group in retrieval_token_groups(text) for alias in group)
