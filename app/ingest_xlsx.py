"""XLSX → Chunks.

Sheet classification derived from inspecting the real files:
  - 2 columns with one long cell  -> NOTE  (full narrative disclosure)
  - >=3 columns, >=4 rows         -> TABLE (tabular financial data)
  - name ends (Tables)/(Policies) -> duplicate subset of the base note

Large tables are split into row windows, each repeating the header line,
so every chunk is interpretable on its own after retrieval.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app import config
from app.schema import (
    Chunk, PUBLIC_FINANCIAL, SEGMENT_DETAIL, HR_COMP,
)

NOTE_MIN_CHARS = 400        # below this, a 2-col sheet is a stub
TABLE_MIN_ROWS = 4
TABLE_WINDOW_ROWS = 15      # rows per chunk for large tables
DUPLICATE_SUFFIXES = ("(tables)", "(policies)")


def fiscal_period(period_end: str) -> str:
    """Apple's FY ends late September. A quarter ending Dec 2024 is Q1 FY2025."""
    year, month = int(period_end[:4]), int(period_end[5:7])
    if month <= 3:
        return f"Q2 FY{year}"
    if month <= 7:
        return f"Q3 FY{year}"
    if month <= 9:
        return f"Q4 FY{year}"
    return f"Q1 FY{year + 1}"      # Oct-Dec belongs to the NEXT fiscal year


def label_for(title: str) -> str:
    """Deterministic, rule-based. An access decision must be auditable."""
    lowered = title.lower()
    if "segment" in lowered or "geographic" in lowered:
        return SEGMENT_DETAIL
    return PUBLIC_FINANCIAL


def sheet_title(df: pd.DataFrame, fallback: str) -> str:
    """The real title lives in A1; sheet names are truncated and collide."""
    if df.empty:
        return fallback
    value = df.iloc[0, 0]
    return fallback if pd.isna(value) else str(value).strip()


def row_to_line(row) -> str:
    cells = [str(v).strip() for v in row if not pd.isna(v)]
    return " | ".join(cells)


def table_lines(df: pd.DataFrame) -> list[str]:
    return [line for line in (row_to_line(r) for r in df.itertuples(index=False))
            if line]


def chunks_from_sheet(df, name, title, src, doc_type, period, label, index_no):
    """Classify one sheet and emit one or more chunks."""
    rows, cols = df.shape
    longest = max((len(str(v)) for v in df.values.flatten()), default=0)
    # Sheet position guarantees uniqueness; the slug is for readability only.
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())[-30:].strip("_")
    slug = f"s{index_no:02d}_{slug}"

    def make(body: str, content_type: str, suffix: str = "") -> Chunk:
        return Chunk(
            chunk_id=f"{src.stem}_{slug}{suffix}",
            source_file=src.name,
            doc_type=doc_type,
            fiscal_period=period,
            location=f"sheet: {title[:60]}{suffix}",
            content_type=content_type,
            sensitivity_label=label,
            text=f"{title}\n\n{body}",
        )

    # NOTE: narrative disclosure held in a single long cell
    if cols == 2 and longest >= NOTE_MIN_CHARS:
        body = max((str(v) for v in df.values.flatten()), key=len)
        return [make(body, "text")] if body.strip() else []

    # TABLE: split into row windows, repeating the header each time
    if cols >= 3 and rows >= TABLE_MIN_ROWS:
        lines = table_lines(df)
        if not lines:
            return []
        header, data = lines[0], lines[1:]
        if len(data) <= TABLE_WINDOW_ROWS:
            return [make("\n".join(lines), "table")]

        out = []
        for i in range(0, len(data), TABLE_WINDOW_ROWS):
            window = data[i:i + TABLE_WINDOW_ROWS]
            part = i // TABLE_WINDOW_ROWS + 1
            body = "\n".join([header] + window)
            out.append(make(body, "table", f"_p{part}"))
        return out

    return []


HR_TITLES = {
    "Headcount": (
        "Employee headcount, attrition and open roles by function and region "
        "(internal HR data, restricted)"
    ),
    "Compensation Bands": (
        "Employee salary bands, equity grants and bonus targets by function "
        "(internal compensation data, restricted)"
    ),
}


def ingest_workbook(path: Path) -> list[Chunk]:
    is_hr = "hr_" in path.name
    doc_type = "HR" if is_hr else "10-Q"
    period = "FY2023-FY2025" if is_hr else fiscal_period(path.stem[-10:])

    book = pd.ExcelFile(path)
    out = []
    for index_no, name in enumerate(book.sheet_names):
        if name.lower().strip().endswith(DUPLICATE_SUFFIXES):
            continue
        df = book.parse(name, header=None)
        # HR sheets are pure numbers; a descriptive title gives the
        # embedding something a natural-language query can match.
        title = HR_TITLES.get(name) if is_hr else None
        title = title or sheet_title(df, name)
        label = HR_COMP if is_hr else label_for(title)
        out.extend(
            chunks_from_sheet(df, name, title, path, doc_type, period,
                              label, index_no)
        )
    return out


def ingest_all() -> list[Chunk]:
    paths = sorted(config.RAW_DIR.glob("*.xlsx")) + \
            sorted(config.SYNTHETIC_DIR.glob("*.xlsx"))
    chunks = []
    for p in paths:
        found = ingest_workbook(p)
        print(f"  {p.name}: {len(found)} chunks")
        chunks.extend(found)
    return chunks


if __name__ == "__main__":
    result = ingest_all()
    print(f"\nTotal: {len(result)} chunks")
    hr = sum(1 for c in result if c.sensitivity_label == HR_COMP)
    seg = sum(1 for c in result if c.sensitivity_label == SEGMENT_DETAIL)
    longest = max(len(c.text) for c in result)
    print(f"  HR_COMP: {hr}   SEGMENT_DETAIL: {seg}   rest: PUBLIC_FINANCIAL")
    print(f"  longest chunk: {longest} chars")