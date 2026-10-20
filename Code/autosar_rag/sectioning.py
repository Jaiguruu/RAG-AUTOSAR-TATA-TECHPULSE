"""Dependency-free section boundary detection for AUTOSAR document text.

This parser is deliberately heuristic: it recognizes likely numbered section
headings and long all-caps headings, but is not a full AUTOSAR document grammar.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Tuple

# Prefer explicit numbered section headings and long all-caps headings. This is
# intentionally conservative: it is a heuristic, not a complete AUTOSAR parser.
SECTION_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)+\s+[A-Z][^\n]{2,110}|"
    r"\d+\s+[A-Z][^\n]{2,110}|"
    r"[A-Z][A-Z0-9 /_()\-]{5,100})\s*$"
)


def section_segments(text: str) -> Iterator[Tuple[int, str, str | None]]:
    """Yield (page-relative start, text, local heading) without losing newlines."""
    lines = text.splitlines(keepends=True)
    if not lines:
        if text:
            yield 0, text, None
        return

    segment_start = 0
    cursor = 0
    current_heading: str | None = None
    buffer: list[str] = []
    for line in lines:
        candidate = line.strip()
        is_heading = bool(candidate and SECTION_HEADING_RE.match(candidate))
        if is_heading and buffer:
            prior = "".join(buffer)
            if prior.strip():
                yield segment_start, prior, current_heading
            segment_start = cursor
            buffer = []
            current_heading = candidate
        elif is_heading and not buffer:
            current_heading = candidate
            segment_start = cursor
        buffer.append(line)
        cursor += len(line)

    tail = "".join(buffer)
    if tail.strip():
        yield segment_start, tail, current_heading

