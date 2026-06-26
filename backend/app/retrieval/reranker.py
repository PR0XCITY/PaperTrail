"""
Optional cross-encoder reranker.

Enabled only when the environment variable ENABLE_RERANKER=1 is set.
On Render free tier (512 MB RAM) leave this disabled.
Locally, set ENABLE_RERANKER=1 for better retrieval quality.

Falls back gracefully to RRF-ranked order if the model fails to load.
"""
import os

_reranker = None
_enabled = os.getenv("ENABLE_RERANKER", "0") == "1"


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        print("Loading reranker model (cross-encoder/ms-marco-MiniLM-L-6-v2)...")
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        print("Reranker loaded")
    return _reranker


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Rerank chunks using cross-encoder scores.

    If ENABLE_RERANKER is not set, returns chunks[:top_n] (RRF order).

    Parameters
    ----------
    query  : the (possibly rewritten) user question
    chunks : fused candidates from reciprocal_rank_fusion()
    top_n  : number of final chunks to return

    Returns
    -------
    list of chunk dicts, sorted by rerank_score desc (or rrf_score if disabled).
    Each returned chunk has a "rerank_score" key when reranking is active.
    """
    if not _enabled or not chunks:
        return chunks[:top_n]

    try:
        reranker = _get_reranker()
        pairs = [(query, c["text"]) for c in chunks]
        scores = reranker.predict(pairs)

        ranked = sorted(
            zip(chunks, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        result = []
        for chunk, score in ranked[:top_n]:
            chunk = dict(chunk)
            chunk["rerank_score"] = float(score)
            result.append(chunk)
        return result

    except Exception as e:
        print(f"Reranker failed (falling back to RRF order): {e}")
        return chunks[:top_n]
