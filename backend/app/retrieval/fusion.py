"""
Reciprocal Rank Fusion (RRF) for combining vector and BM25 results.

Formula:  score(d) = Σ  1 / (k + rank_i(d))
Default k=60 is the standard value from the original RRF paper.

Uses MD5 hash of text as the dedup key to avoid raw-string collisions
while keeping the approach lightweight (no DB lookup required).
"""
import hashlib


def _text_key(text: str) -> str:
    """Stable hash key for a chunk — avoids dict key explosion on long texts."""
    return hashlib.md5(text.encode()).hexdigest()


def reciprocal_rank_fusion(
    vec_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
    top_n: int = 20,
) -> list[dict]:
    """
    Fuse two ranked lists via Reciprocal Rank Fusion.

    Parameters
    ----------
    vec_results  : vector search results in rank order
    bm25_results : BM25 search results in rank order
    k            : RRF smoothing constant (default 60)
    top_n        : number of results to return

    Returns
    -------
    list of chunk dicts with an added "rrf_score" key, best first.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}

    def _process(result_list: list[dict]) -> None:
        for rank, chunk in enumerate(result_list, start=1):
            key = _text_key(chunk["text"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            chunks[key] = chunk  # last write wins — same text ≡ same chunk

    _process(vec_results)
    _process(bm25_results)

    # Attach final RRF scores before returning
    for key, chunk in chunks.items():
        chunk = dict(chunk)  # shallow copy so we don't mutate the input
        chunk["rrf_score"] = scores[key]
        chunks[key] = chunk

    ranked_keys = sorted(scores, key=lambda t: scores[t], reverse=True)
    return [chunks[key] for key in ranked_keys[:top_n]]
