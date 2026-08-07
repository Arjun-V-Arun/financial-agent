"""Chunks -> Chroma vector index.

Metadata travels with every vector, which is what makes RBAC enforceable
at retrieval: a restricted chunk is never fetched, so it never enters the
model's context. Filtering happens in the query, not after.

Embeddings are computed locally (MiniLM) so the index rebuilds with no
API key, no rate limit, and no cost.
"""
from __future__ import annotations

import shutil

import chromadb
from sentence_transformers import SentenceTransformer

from app import config
from app.schema import read_chunks

MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION = "filings"
BATCH = 100


def build() -> None:
    chunks = read_chunks(config.CHUNKS_PATH)
    print(f"Loaded {len(chunks)} chunks")

    # Rebuild from scratch: the index is derived state, never repaired.
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)

    print(f"Loading {MODEL_NAME} (first run downloads ~80MB)...")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(chunks), BATCH):
        batch = chunks[start:start + BATCH]
        vectors = model.encode(
            [c.text for c in batch],
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=[c.chunk_id for c in batch],
            embeddings=vectors,
            documents=[c.text for c in batch],
            metadatas=[{
                "source_file": c.source_file,
                "doc_type": c.doc_type,
                "fiscal_period": c.fiscal_period,
                "location": c.location,
                "content_type": c.content_type,
                "sensitivity_label": c.sensitivity_label,
            } for c in batch],
        )
        print(f"  indexed {min(start + BATCH, len(chunks))}/{len(chunks)}")

    print(f"\nCollection '{COLLECTION}' holds {collection.count()} vectors")


if __name__ == "__main__":
    build()