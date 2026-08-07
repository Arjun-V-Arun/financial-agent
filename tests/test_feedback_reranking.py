"""Proves feedback changes future retrieval, not just the stored numbers.

test_feedback.py tests feedback.boosts() in isolation. That proves the
math is bounded and scoped, but not that a vote actually moves a chunk
in retrieve.search()'s output — which is the thing the assignment brief
asks to demonstrate. This wires a vote through the real ranking path.
"""
import chromadb

from app import feedback, policy as policy_mod, retrieve
from app.schema import PUBLIC_FINANCIAL

QUERY = "Apple's fiscal 2025 revenue was strong across all segments."
CHUNK_A_TEXT = QUERY                                                     # near-exact match
CHUNK_B_TEXT = "Apple's fiscal 2025 sales were strong across all segments."


def _seed_two_close_chunks(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.create_collection("filings",
                                          metadata={"hnsw:space": "cosine"})
    vectors = retrieve._model().encode([CHUNK_A_TEXT, CHUNK_B_TEXT]).tolist()
    collection.add(
        ids=["chunk-a", "chunk-b"],
        documents=[CHUNK_A_TEXT, CHUNK_B_TEXT],
        embeddings=vectors,
        metadatas=[
            {"source_file": "a.pdf", "doc_type": "10-K", "fiscal_period": "FY2025",
             "location": "page 1", "content_type": "text",
             "sensitivity_label": PUBLIC_FINANCIAL},
            {"source_file": "b.pdf", "doc_type": "10-K", "fiscal_period": "FY2025",
             "location": "page 2", "content_type": "text",
             "sensitivity_label": PUBLIC_FINANCIAL},
        ],
    )
    return tmp_path / "chroma"


def test_a_downvote_reorders_future_search_results(tmp_path, monkeypatch):
    chroma_dir = _seed_two_close_chunks(tmp_path)
    monkeypatch.setattr(retrieve.config, "CHROMA_DIR", chroma_dir)
    monkeypatch.setattr(feedback.config, "DB_PATH", tmp_path / "facts.db")
    retrieve._collection.cache_clear()
    try:
        ceo = policy_mod.load("CEO")

        # Before any feedback, chunk-a's near-exact wording ranks first.
        before = retrieve.search(QUERY, ceo, k=2)
        assert before[0].chunk_id == "chunk-a"

        # Two down-votes (-0.16) comfortably clear the ~0.05 raw score gap
        # between these two near-duplicate chunks, without hitting the
        # +/-0.24 cap.
        feedback.record(QUERY, "CEO", ["chunk-a"], -1)
        feedback.record(QUERY, "CEO", ["chunk-a"], -1)

        after = retrieve.search(QUERY, ceo, k=2)
        assert after[0].chunk_id == "chunk-b"
    finally:
        retrieve._collection.cache_clear()   # don't leak into later tests
