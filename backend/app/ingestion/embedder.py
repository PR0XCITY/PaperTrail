import os
import hashlib

# Set cache directories before any model-related imports so that
# sentence-transformers and HuggingFace write to /tmp (writable on Render free tier)
# and nothing is downloaded at import time.
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/tmp/st_cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/hf_cache")

from app.config import EMBED_MODEL
from app.config import CHROMA_DIR

# ── Lazy singletons ──────────────────────────────────────────────────────────
# These are NOT loaded at import time.  The model (~230 MB) and ChromaDB
# client (~50 MB) are only instantiated when the first request needs them.

_model = None
_client = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading embedding model...")
        _model = SentenceTransformer(EMBED_MODEL)
        print("Embedding model loaded")
    return _model


def get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def emb(t):
    return get_model().encode(
        t,
        show_progress_bar=False
    ).tolist()


def get_col(n):
    return get_client().get_or_create_collection(
        name=n
    )


def _chunk_id(collection: str, text: str, source: str, page: int, chunk_index: int) -> str:
    """
    Stable, unique ID derived from content + position.
    Using a hash means re-uploading the same file is idempotent (upsert),
    and different files never collide even in the same collection.
    """
    key = f"{source}::{page}::{chunk_index}::{text[:64]}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]

def add_chunks(n, ch):
    col = get_col(n)

    tx = [x["text"] for x in ch]
    em = emb(tx)
    md = [x["metadata"] for x in ch]

    ids = [
        _chunk_id(
            n,
            x["text"],
            x["metadata"].get("source", ""),
            x["metadata"].get("page", 0),
            x["metadata"].get("chunk_index", i),
        )
        for i, x in enumerate(ch)
    ]

    # upsert: safe to call multiple times — re-uploading the same file
    # is idempotent, and different files never clobber each other.
    col.upsert(
        ids=ids,
        embeddings=em,
        documents=tx,
        metadatas=md
    )

def query_collection(n, q, k=3):
    col = get_col(n)

    qe = emb([q])[0]

    # Clamp k to the number of documents actually in the collection
    total = col.count()
    k = min(k, total) if total > 0 else k

    return col.query(
        query_embeddings=[qe],
        n_results=k
    )