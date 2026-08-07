"""Ingestion entrypoint: both source formats -> artifacts/chunks.jsonl.

Thin by design. Because both parsers emit the same Chunk shape, combining
them needs no format-specific logic, and every downstream milestone reads
one file with one schema.
"""
from __future__ import annotations

from collections import Counter

from app import config, ingest_pdf, ingest_xlsx
from app.schema import write_chunks


def main() -> None:
    print("PDF sources:")
    pdf_chunks = ingest_pdf.ingest_all()

    print("\nXLSX sources:")
    xlsx_chunks = ingest_xlsx.ingest_all()

    chunks = pdf_chunks + xlsx_chunks

    ids = Counter(c.chunk_id for c in chunks)
    collisions = [cid for cid, n in ids.items() if n > 1]
    if collisions:
        raise ValueError(
            f"{len(collisions)} duplicate chunk_id(s), first: {collisions[0]}"
        )

    write_chunks(chunks, config.CHUNKS_PATH)

    print(f"\nWrote {len(chunks)} chunks to {config.CHUNKS_PATH}")
    print("\nBy sensitivity label:")
    for label, count in Counter(c.sensitivity_label for c in chunks).most_common():
        print(f"  {label:<20} {count}")
    print("\nBy document type:")
    for doc, count in Counter(c.doc_type for c in chunks).most_common():
        print(f"  {doc:<20} {count}")


if __name__ == "__main__":
    main()