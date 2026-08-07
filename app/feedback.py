"""Persistent retrieval feedback used to rerank future searches.

Votes are scoped to both the normalized question and role. They can change
the order of chunks that RBAC already permits, but can never add a restricted
chunk to the candidate set.
"""
from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

from app import config

BOOST_PER_VOTE = 0.08
MAX_BOOST = 0.24

SCHEMA = """
CREATE TABLE IF NOT EXISTS retrieval_feedback (
    id         INTEGER PRIMARY KEY,
    query_key  TEXT NOT NULL,
    role       TEXT NOT NULL,
    chunk_id   TEXT NOT NULL,
    vote       INTEGER NOT NULL CHECK (vote IN (-1, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_lookup
    ON retrieval_feedback (query_key, role, chunk_id);
"""


def _query_key(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().casefold())


def record(question: str, role: str, chunk_ids: Iterable[str], vote: int) -> int:
    """Store one vote for every cited chunk and return the number recorded."""
    if vote not in (-1, 1):
        raise ValueError("vote must be -1 or 1")

    unique_ids = sorted(set(chunk_ids))
    if not unique_ids:
        return 0

    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO retrieval_feedback (query_key, role, chunk_id, vote) "
            "VALUES (?, ?, ?, ?)",
            [(_query_key(question), role, chunk_id, vote)
             for chunk_id in unique_ids],
        )
    return len(unique_ids)


def boosts(question: str, role: str) -> dict[str, float]:
    """Return bounded score adjustments for a previously rated question."""
    if not config.DB_PATH.exists():
        return {}

    with sqlite3.connect(config.DB_PATH) as conn:
        conn.executescript(SCHEMA)
        rows = conn.execute(
            "SELECT chunk_id, SUM(vote) FROM retrieval_feedback "
            "WHERE query_key = ? AND role = ? GROUP BY chunk_id",
            (_query_key(question), role),
        ).fetchall()

    return {
        chunk_id: max(-MAX_BOOST, min(MAX_BOOST, total * BOOST_PER_VOTE))
        for chunk_id, total in rows
    }