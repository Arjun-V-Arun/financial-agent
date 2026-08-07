"""Semantic search over the chunk index.

allowed_labels is REQUIRED. There is deliberately no way to search
without declaring what the caller may see — an optional filter is a
filter someone forgets. Restricted chunks are excluded by the query
itself, so they never enter the model's context.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from app import config
from app.embed import COLLECTION, MODEL_NAME


@dataclass
class Hit:
    chunk_id: str
    text: str
    score: float          # cosine similarity, 1.0 = identical
    source_file: str
    location: str
    fiscal_period: str
    sensitivity_label: str


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    """Loaded once per process; ~1s to construct, so never per query."""
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_collection(COLLECTION)


def search(query: str, allowed_labels: list[str], k: int = 5) -> list[Hit]:
    """Return the k most similar chunks the caller is permitted to see."""
    if not allowed_labels:
        return []                      # deny by default: no grants, no results

    vector = _model().encode([query]).tolist()

    result = _collection().query(
        query_embeddings=vector,
        n_results=k,
        where={"sensitivity_label": {"$in": allowed_labels}},
    )

    hits = []
    for chunk_id, text, distance, meta in zip(
        result["ids"][0],
        result["documents"][0],
        result["distances"][0],
        result["metadatas"][0],
    ):
        hits.append(Hit(
            chunk_id=chunk_id,
            text=text,
            score=round(1 - distance, 3),
            source_file=meta["source_file"],
            location=meta["location"],
            fiscal_period=meta["fiscal_period"],
            sensitivity_label=meta["sensitivity_label"],
        ))
    return hits


if __name__ == "__main__":
    from app.schema import ALL_LABELS

    for query in [
        "What was total net sales in fiscal 2025?",
        "How many people work in Engineering?",
    ]:
        print(f"\n{'=' * 70}\nQ: {query}")
        for hit in search(query, sorted(ALL_LABELS), k=3):
            print(f"  {hit.score}  [{hit.sensitivity_label}] "
                  f"{hit.source_file} {hit.location}")
            print(f"         {hit.text[:90].replace(chr(10), ' ')}")