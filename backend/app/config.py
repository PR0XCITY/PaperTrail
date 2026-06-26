from dotenv import load_dotenv
import os

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Embedding ─────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 700
CHUNK_OVERLAP = 150

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_DIR = "./chroma_store"
CHROMA_COLLECTION = "papertrail_docs"  # single collection, filtered by document_id

# ── Document Registry ─────────────────────────────────────────────────────────
DOC_REGISTRY_PATH = "./doc_registry.json"

# ── BM25 ──────────────────────────────────────────────────────────────────────
BM25_DIR = "./bm25_store"
BM25_INDEX_PATH = "./bm25_store/all_docs.pkl"

# ── Cache dirs (writable on Render free tier) ─────────────────────────────────
TRANSFORMERS_CACHE = "/tmp/hf_cache"
ST_CACHE = "/tmp/st_cache"

# ── Feature Flags ─────────────────────────────────────────────────────────────
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "0") == "1"
DEBUG = os.getenv("PAPERTRAIL_DEBUG", "0") == "1"