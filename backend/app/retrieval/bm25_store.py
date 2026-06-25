"""
BM25 index builder and searcher.

Each collection gets a pickle file at ./bm25_store/<collection>.pkl
containing {"corpus": [str], "metadata": [dict], "index": BM25Okapi}.

Uploading multiple PDFs into the same collection is safe: the new chunks
are APPENDED to the existing corpus before rebuilding the index, so no
document's BM25 data is lost. Re-uploading the same file is idempotent
because chunks are deduplicated by (source, page, chunk_index) key.
"""

import os
import pickle
import re

from rank_bm25 import BM25Okapi

BM25_DIR = "./bm25_store"


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-word characters."""
    return re.findall(r"\w+", text.lower())


def _index_path(collection_name: str) -> str:
    return os.path.join(BM25_DIR, f"{collection_name}.pkl")


def _chunk_key(metadata: dict) -> str:
    """Stable dedup key matching the one in embedder.py."""
    return f"{metadata.get('source','')}::{metadata.get('page',0)}::{metadata.get('chunk_index',0)}"


def build_bm25_index(collection_name: str, chunks: list[dict]) -> None:
    """
    Append new chunks to the BM25 index for a collection, then rebuild.

    Existing chunks from other PDFs are preserved. Duplicate chunks
    (same source + page + chunk_index) are replaced with the new version.

    Parameters
    ----------
    collection_name : str
    chunks : list of {"text": str, "metadata": dict}
    """
    os.makedirs(BM25_DIR, exist_ok=True)

    path = _index_path(collection_name)

    # Load existing corpus if present
    existing_corpus: list[str] = []
    existing_meta: list[dict] = []
    if os.path.exists(path):
        with open(path, "rb") as f:
            payload = pickle.load(f)
        existing_corpus = payload.get("corpus", [])
        existing_meta = payload.get("metadata", [])

    # Build a dict of existing chunks keyed by dedup key
    merged: dict[str, tuple[str, dict]] = {
        _chunk_key(md): (txt, md)
        for txt, md in zip(existing_corpus, existing_meta)
    }

    # Upsert new chunks (overwrites same-keyed entries)
    for chunk in chunks:
        key = _chunk_key(chunk["metadata"])
        merged[key] = (chunk["text"], chunk["metadata"])

    # Reconstruct flat lists
    all_texts = [v[0] for v in merged.values()]
    all_meta  = [v[1] for v in merged.values()]

    tokenized = [_tokenize(t) for t in all_texts]
    index = BM25Okapi(tokenized)

    payload = {"corpus": all_texts, "metadata": all_meta, "index": index}
    with open(path, "wb") as f:
        pickle.dump(payload, f)


def search_bm25(collection_name: str, query: str, k: int = 10) -> list[dict]:
    """
    Return top-k chunks by BM25 score.

    Parameters
    ----------
    collection_name : str
    query : str
    k : int

    Returns
    -------
    list of {"text": str, "metadata": dict}
        Sorted by descending BM25 score.
    """
    path = _index_path(collection_name)
    if not os.path.exists(path):
        return []

    with open(path, "rb") as f:
        payload = pickle.load(f)

    index: BM25Okapi = payload["index"]
    corpus: list[str] = payload["corpus"]
    metadatas: list[dict] = payload["metadata"]

    tokens = _tokenize(query)
    scores = index.get_scores(tokens)

    # Pair with indices, sort descending
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for idx, _score in ranked[:k]:
        results.append({"text": corpus[idx], "metadata": metadatas[idx]})

    return results
