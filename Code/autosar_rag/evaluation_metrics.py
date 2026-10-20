"""Small, dependency-free helpers for transparent benchmark scoring.

Keyword coverage is a diagnostic proxy only. It is not factual accuracy and
must never be labelled as such.
"""

from __future__ import annotations

import re
from typing import Any, Dict


def _tokens(value: str) -> list[str]:
    # Underscores and punctuation are separators, so `PduR_LdComTransmit` can
    # match the same identifier with spaces while still preserving token order.
    return re.findall(r"[a-z0-9]+", str(value or "").casefold())


def check_must_include(answer: str, must_include_str: str) -> Dict[str, Any]:
    """Score required phrases conservatively; do not credit scattered words.

    A criterion matches only when its normalized phrase or ordered token
    sequence occurs in the answer. Empty criteria are unscored, not awarded 100%.
    """
    terms = [term.strip() for term in str(must_include_str or "").split("|") if term.strip()]
    if not terms:
        return {"score": None, "matched": [], "missing": [], "total_terms": 0, "scored": False}

    answer_tokens = _tokens(answer)
    matched, missing = [], []
    for term in terms:
        term_tokens = _tokens(term)
        token_match = bool(term_tokens) and any(
            answer_tokens[index:index + len(term_tokens)] == term_tokens
            for index in range(0, len(answer_tokens) - len(term_tokens) + 1)
        )
        if token_match:
            matched.append(term)
        else:
            missing.append(term)

    score = len(matched) / len(terms)
    return {
        "score": round(score, 4),
        "matched": matched,
        "missing": missing,
        "total_terms": len(terms),
        "scored": True,
    }
