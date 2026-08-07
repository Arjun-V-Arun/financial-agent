"""PDF → Chunks.

Text extraction is clean on these born-digital filings, so plain
extract_text() suffices; no table-specific extraction path is needed.

Sensitivity labelling walks the 10-K's fixed Item structure. Markers are
anchored to line starts and progress monotonically, because a 10-K is
linear: a section can only advance, never revert. Front matter before
Item 1 is skipped so the table of contents cannot set a label.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from app import config
from app.schema import Chunk, PUBLIC_FINANCIAL, SEGMENT_DETAIL, STRATEGY

CHUNK_CHARS = 3000          # ~750 tokens
OVERLAP_CHARS = 300         # protects labels split from their values
FOOTER = re.compile(r"Apple Inc\.\s*\|\s*\d{4} Form 10-K\s*\|\s*\d+")

# Ordered sections of a 10-K. Index = position in the document.
# A page can advance the pointer but never move it backwards.
SECTIONS = [
    (re.compile(r"^Item 1\.\s+Business", re.M), PUBLIC_FINANCIAL),
    (re.compile(r"^Item 1A\.\s+Risk Factors", re.M), STRATEGY),
    (re.compile(r"^Item 5\.\s+Market for", re.M), PUBLIC_FINANCIAL),
    (re.compile(r"^Item 7\.\s+Management", re.M), STRATEGY),
    (re.compile(r"^Item 8\.\s+Financial Statements", re.M), PUBLIC_FINANCIAL),
    (re.compile(r"^Item 15\.\s+Exhibit", re.M), PUBLIC_FINANCIAL),
]

# Applied per page, independent of section state.
SEGMENT_HINT = re.compile(
    r"Segment Information and Geographic Data|net sales by reportable segment",
    re.I,
)


def fiscal_period(stem: str) -> str:
    """aapl_10k_fy2025 -> FY2025"""
    match = re.search(r"fy(\d{4})", stem.lower())
    return f"FY{match.group(1)}" if match else "UNKNOWN"


def clean(text: str) -> str:
    """Strip the repeating page footer; it pollutes every embedding."""
    return FOOTER.sub("", text).strip()


def page_texts(path: Path) -> list[tuple[int, str]]:
    """Page number and cleaned text, skipping the table of contents.

    The TOC lists every Item heading, so a single TOC page would pin the
    section pointer at the last section and freeze it there.
    """
    out = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = clean(page.extract_text() or "")
            if not text:
                continue
            if "TABLE OF CONTENTS" in text.upper():
                continue
            out.append((number, text))
    return out


def advance(text: str, position: int) -> int:
    """Return the furthest section this page reaches. Never goes backwards."""
    for index in range(len(SECTIONS) - 1, position, -1):
        pattern, _ = SECTIONS[index]
        if pattern.search(text):
            return index
    return position


def split(text: str) -> list[str]:
    """Size-based windows with overlap, preferring paragraph boundaries."""
    if len(text) <= CHUNK_CHARS:
        return [text]

    parts, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind("\n", end - 500, end)
            if boundary > start:
                end = boundary
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - OVERLAP_CHARS
    return [p for p in parts if p]


def ingest_pdf(path: Path) -> list[Chunk]:
    period = fiscal_period(path.stem)
    position = -1                      # front matter: no section reached yet
    out = []

    for page_no, text in page_texts(path):
        position = advance(text, position)
        if position < 0:
            continue                   # skip cover page and table of contents

        _, label = SECTIONS[position]
        if SEGMENT_HINT.search(text):
            label = SEGMENT_DETAIL     # per-page override, not sticky

        for index, body in enumerate(split(text), start=1):
            out.append(Chunk(
                chunk_id=f"{path.stem}_p{page_no:03d}_c{index}",
                source_file=path.name,
                doc_type="10-K",
                fiscal_period=period,
                location=f"page {page_no}",
                content_type="text",
                sensitivity_label=label,
                text=body,
            ))
    return out


def ingest_all() -> list[Chunk]:
    chunks = []
    for path in sorted(config.RAW_DIR.glob("*.pdf")):
        found = ingest_pdf(path)
        print(f"  {path.name}: {len(found)} chunks")
        chunks.extend(found)
    return chunks


if __name__ == "__main__":
    result = ingest_all()
    print(f"\nTotal: {len(result)} chunks")
    for name in (PUBLIC_FINANCIAL, SEGMENT_DETAIL, STRATEGY):
        count = sum(1 for c in result if c.sensitivity_label == name)
        print(f"  {name}: {count}")
    print(f"  longest: {max(len(c.text) for c in result)} chars")