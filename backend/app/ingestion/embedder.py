"""
Embedder — vector embeddings via sentence-transformers + ChromaDB persistence.

All heavy imports are lazy: nothing loads at import time.
Cache dirs are redirected to /tmp so Render's ephemeral FS works.
"""
import os
import hashlib

os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/tmp/st_cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/hf_cache")

from app.config import EMBED_MODEL, CHROMA_DIR, CHROMA_COLLECTION

_model = None
_client = None


# ── Singletons ────────────────────────────────────────────────────────────────

def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        print("Loading embedding model...")
        _model = TextEmbedding(model_name=f"sentence-transformers/{EMBED_MODEL}")
        print("Embedding model loaded")
    return _model


def get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


# ── Public embedding API ──────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns a list of float vectors."""
    return [vec.tolist() for vec in get_model().embed(texts)]


# ── Collection helper ─────────────────────────────────────────────────────────

def get_col(name: str = None):
    return get_client().get_or_create_collection(name=name or CHROMA_COLLECTION)


# ── Stable chunk ID ───────────────────────────────────────────────────────────

def _chunk_id(document_id: str, text: str, page: int, chunk_index: int) -> str:
    key = f"{document_id}::{page}::{chunk_index}::{text[:64]}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


# ── Write ─────────────────────────────────────────────────────────────────────

def add_chunks(chunks: list[dict], collection_name: str = None) -> None:
    """
    Upsert chunks into ChromaDB.
    Re-uploading the same document is idempotent (same IDs → upsert replaces).
    """
    col = get_col(collection_name)

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    metadatas = [c["metadata"] for c in chunks]

    ids = [
        _chunk_id(
            c["metadata"].get("document_id", ""),
            c["text"],
            c["metadata"].get("page", 0),
            c["metadata"].get("chunk_index", i),
        )
        for i, c in enumerate(chunks)
    ]

    col.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


# ── Read ──────────────────────────────────────────────────────────────────────

def query_collection(
    query: str,
    k: int = 20,
    document_id: str = None,
    collection_name: str = None,
) -> dict:
    """
    Vector search with optional document_id filter.

    Parameters
    ----------
    query         : query text
    k             : number of results to return (clamped to collection size)
    document_id   : if set, only return chunks from this document
    collection_name: defaults to CHROMA_COLLECTION

    Returns
    -------
    ChromaDB query result dict with "documents", "metadatas", "distances" keys.
    """
    col = get_col(collection_name)

    query_embedding = embed_texts([query])[0]

    total = col.count()
    if total == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    actual_k = min(k, total)
    kwargs: dict = dict(
        query_embeddings=[query_embedding],
        n_results=actual_k,
        include=["documents", "metadatas", "distances"],
    )
    if document_id:
        kwargs["where"] = {"document_id": document_id}

    return col.query(**kwargs)


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_document(document_id: str, collection_name: str = None) -> int:
    """
    Remove all chunks belonging to document_id from ChromaDB.
    Returns the number of deleted chunks.
    """
    col = get_col(collection_name)
    results = col.get(where={"document_id": document_id}, include=[])
    ids = results.get("ids", [])
    if ids:
        col.delete(ids=ids)
    return len(ids)