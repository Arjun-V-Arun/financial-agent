"""Semantic search over the chunk index.

allowed_labels is REQUIRED. There is deliberately no way to search
without declaring what the caller may see — an optional filter is a
filter someone forgets. Restricted chunks are excluded by the query
itself, so they never enter the model's context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from app import config, feedback
from app.embed import COLLECTION, MODEL_NAME

# Embedding similarity alone favors generic table structure over the specific
# year asked about, so a chunk for the wrong fiscal period can outrank the
# right one by a few hundredths. A small deterministic nudge for chunks whose
# period is literally named in the query fixes that without overriding
# semantic ranking for topical (non-period-specific) questions.
PERIOD_MATCH_BOOST = 0.05
_PERIOD_RE = re.compile(r"\bQ([1-4])\s*FY\s*(\d{4})\b|\bFY\s*(\d{4})\b", re.IGNORECASE)


def _mentioned_periods(query: str) -> set[str]:
    """Fiscal periods named in the query, normalized to match chunk metadata."""
    periods = set()
    for quarter, qyear, year in _PERIOD_RE.findall(query):
        periods.add(f"Q{quarter} FY{qyear}" if quarter else f"FY{year}")
    return periods


@dataclass
class Hit:
    chunk_id: str
    text: str
    score: float          # cosine similarity, 1.0 = identical
    source_file: str
    location: str
    fiscal_period: str
    sensitivity_label: str
    feedback_boost: float = 0.0
    period_boost: float = 0.0


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    """Loaded once per process; ~1s to construct, so never per query."""
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_collection(COLLECTION)


def search(query: str, policy, k: int = 5) -> list[Hit]:
    """Return the k most similar chunks this policy permits.

    Takes a Policy, not a label list: the caller cannot construct a
    permissive filter by hand, and every call site is forced to name
    whose access it is acting under.
    """
    vector = _model().encode([query]).tolist()

    result = _collection().query(
        query_embeddings=vector,
        n_results=max(k * 3, k),
        where=policy.chroma_filter(),
    )

    learned_boosts = feedback.boosts(query, policy.role)
    mentioned_periods = _mentioned_periods(query)
    hits = []
    for chunk_id, text, distance, meta in zip(
        result["ids"][0],
        result["documents"][0],
        result["distances"][0],
        result["metadatas"][0],
    ):
        if not policy.permits_period(meta["fiscal_period"]):
            continue                   # second layer: period isn't a Chroma filter
        period = meta["fiscal_period"]
        period_boost = PERIOD_MATCH_BOOST if any(
            p in period or period in p for p in mentioned_periods
        ) else 0.0
        hits.append(Hit(
            chunk_id=chunk_id,
            text=text,
            score=round(1 - distance, 3),
            source_file=meta["source_file"],
            location=meta["location"],
            fiscal_period=period,
            sensitivity_label=meta["sensitivity_label"],
            feedback_boost=learned_boosts.get(chunk_id, 0.0),
            period_boost=period_boost,
        ))
    hits.sort(key=lambda hit: hit.score + hit.feedback_boost + hit.period_boost,
              reverse=True)
    return hits[:k]


if __name__ == "__main__":
    from app import policy as policy_mod

    question = "How many people work in Engineering?"
    for role in policy_mod.roles():
        pol = policy_mod.load(role)
        print(f"\n{'=' * 70}\n{role}: {question}")
        hits = search(question, pol, k=3)
        if not hits:
            print("  (no permitted results)")
        for h in hits:
            print(f"  {h.score}  [{h.sensitivity_label}] {h.source_file} {h.location}")