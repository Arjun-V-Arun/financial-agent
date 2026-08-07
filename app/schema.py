"""The chunk contract. Every parser produces this shape; every consumer reads it.

Defined before any parsing code so both ingestion paths converge on one
schema — which means the policy layer in M4 has a single code path.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

# --- Sensitivity labels -------------------------------------------------
# Assigned at ingestion, deterministically. Whatever isn't labelled here
# cannot be enforced later — no downstream code can recover information
# that was never captured.
PUBLIC_FINANCIAL = "PUBLIC_FINANCIAL"   # statements, balance sheets, cash flows
SEGMENT_DETAIL = "SEGMENT_DETAIL"       # geographic / product breakdowns
STRATEGY = "STRATEGY"                   # risk factors, MD&A, forward-looking
HR_COMP = "HR_COMP"                     # synthetic HR workbook — restricted

ALL_LABELS = {PUBLIC_FINANCIAL, SEGMENT_DETAIL, STRATEGY, HR_COMP}


@dataclass
class Chunk:
    chunk_id: str           # stable, unique, human-readable
    source_file: str        # filename it came from
    doc_type: str           # "10-K" | "10-Q" | "HR"
    fiscal_period: str      # "FY2025" | "Q2 FY2025"
    location: str           # "page 24" | "sheet: Revenue"
    content_type: str       # "text" | "table"
    sensitivity_label: str
    text: str

    def __post_init__(self):
        # Deny by default: an unrecognised label must not silently pass.
        if self.sensitivity_label not in ALL_LABELS:
            raise ValueError(
                f"{self.chunk_id}: unknown label {self.sensitivity_label!r}"
            )
        if not self.text.strip():
            raise ValueError(f"{self.chunk_id}: empty text")


def write_chunks(chunks: list[Chunk], path: Path) -> None:
    """One JSON object per line. Streamable, greppable, diffable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def read_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f if line.strip()]