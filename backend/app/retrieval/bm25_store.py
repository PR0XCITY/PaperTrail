"""
BM25 index — single global index file, filtered by document_id at query time.

All chunks from all uploaded PDFs are stored in one pickle file.
document_id metadata on each chunk enables per-document filtering.
"""
import os
import pickle
import re

from rank_bm25 import BM25Okapi
from app.config import BM25_DIR, BM25_INDEX_PATH


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-word characters."""
    return re.findall(r"\w+", text.lower())


def _chunk_key(metadata: dict) -> str:
    """Stable dedup key: document_id + page + chunk_index."""
    return (
        f"{metadata.get('document_id', '')}"
        f"::{metadata.get('page', 0)}"
        f"::{metadata.get('chunk_index', 0)}"
    )


def _load_index() -> tuple[list[str], list[dict], BM25Okapi | None]:
    """Load the existing BM25 index from disk, or return empty structures."""
    if not os.path.exists(BM25_INDEX_PATH):
        return [], [], None
    with open(BM25_INDEX_PATH, "rb") as f:
        payload = pickle.load(f)
    return payload["corpus"], payload["metadata"], payload["index"]


def _save_index(corpus: list[str], metadata: list[dict]) -> None:
    os.makedirs(BM25_DIR, exist_ok=True)
    tokenized = [_tokenize(t) for t in corpus]
    index = BM25Okapi(tokenized)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"corpus": corpus, "metadata": metadata, "index": index}, f)


# ── Write ─────────────────────────────────────────────────────────────────────

def build_bm25_index(chunks: list[dict]) -> None:
    """
    Append new chunks to the global BM25 index, then rebuild.

    Existing chunks from other PDFs are preserved.
    Duplicate chunks (same document_id + page + chunk_index) are replaced.
    """
    existing_corpus, existing_meta, _ = _load_index()

    merged: dict[str, tuple[str, dict]] = {
        _chunk_key(md): (txt, md)
        for txt, md in zip(existing_corpus, existing_meta)
    }

    for chunk in chunks:
        key = _chunk_key(chunk["metadata"])
        merged[key] = (chunk["text"], chunk["metadata"])

    all_texts = [v[0] for v in merged.values()]
    all_meta = [v[1] for v in merged.values()]
    _save_index(all_texts, all_meta)


def delete_document_bm25(document_id: str) -> int:
    """
    Remove all chunks belonging to document_id from the BM25 index.
    Returns the number of removed chunks.
    """
    corpus, meta, _ = _load_index()
    pairs = [(t, m) for t, m in zip(corpus, meta) if m.get("document_id") != document_id]
    removed = len(corpus) - len(pairs)

    if not pairs:
        if os.path.exists(BM25_INDEX_PATH):
            os.remove(BM25_INDEX_PATH)
        return removed

    texts, metas = zip(*pairs)
    _save_index(list(texts), list(metas))
    return removed


# ── Read ──────────────────────────────────────────────────────────────────────

def search_bm25(
    query: str,
    k: int = 20,
    document_id: str = None,
) -> list[dict]:
    """
    Return top-k chunks by BM25 score, optionally filtered to one document.

    Returns
    -------
    list of {"text": str, "metadata": dict, "bm25_score": float}
        Sorted by descending BM25 score.
    """
    corpus, metadatas, index = _load_index()
    if index is None:
        return []

    tokens = _tokenize(query)
    scores = index.get_scores(tokens)

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in ranked:
        md = metadatas[idx]
        if document_id and md.get("document_id") != document_id:
            continue
        results.append({
            "text": corpus[idx],
            "metadata": md,
            "bm25_score": float(score),
        })
        if len(results) >= k:
            break

    return results
