"""
Reciprocal Rank Fusion (RRF) for combining vector and BM25 results.

Formula:  score(d) = Σ 1 / (k + rank_i(d))
Default k=60 is the standard value from the original RRF paper.
"""


def reciprocal_rank_fusion(
    vec_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
    top_n: int = 5,
) -> list[dict]:
    """
    Fuse two ranked lists via Reciprocal Rank Fusion.

    Parameters
    ----------
    vec_results  : list of {"text": str, "metadata": dict} — vector search results in rank order
    bm25_results : list of {"text": str, "metadata": dict} — BM25 search results in rank order
    k            : RRF smoothing constant (default 60)
    top_n        : number of results to return

    Returns
    -------
    list of {"text": str, "metadata": dict}  (top_n items, best first)
    """
    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}  # text → chunk dict (for reconstruction)

    def _process(result_list: list[dict]) -> None:
        for rank, chunk in enumerate(result_list, start=1):
            key = chunk["text"]  # use text as dedup key
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            chunks[key] = chunk  # last write wins (same text = same chunk)

    _process(vec_results)
    _process(bm25_results)

    # Sort by fused score descending
    ranked_keys = sorted(scores, key=lambda t: scores[t], reverse=True)

    return [chunks[key] for key in ranked_keys[:top_n]]
