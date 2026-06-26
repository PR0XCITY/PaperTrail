"""
PaperTrail API — production FastAPI application.

Routes
------
GET  /health                     — liveness probe
GET  /documents                  — list all indexed documents
POST /upload                     — ingest a PDF, returns document_id
DELETE /documents/{document_id}  — remove a document from all indexes
POST /query                      — hybrid RAG query (SSE streaming response)
"""
import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_cache"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/hf_cache"

from app.config import CHROMA_COLLECTION, DOC_REGISTRY_PATH, DEBUG
from app.models import QueryRequest


# ── Document Registry ─────────────────────────────────────────────────────────
# Lightweight JSON file: {document_id: {id, name, pages, chunks, created_at}}

def _load_registry() -> dict:
    if os.path.exists(DOC_REGISTRY_PATH):
        try:
            with open(DOC_REGISTRY_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_registry(registry: dict) -> None:
    with open(DOC_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    async def _warm_up():
        try:
            print("Warming up embedding model in background...")
            from app.ingestion.embedder import get_model
            get_model()
            print("Embedding model ready ✓")
        except Exception as e:
            print(f"Warm-up failed (non-fatal): {e}")

    asyncio.create_task(_warm_up())
    yield
    print("PaperTrail shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="PaperTrail API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    from app.ingestion.embedder import _model
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "version": "2.0.0",
    }


@app.get("/documents")
def list_documents():
    """Return all documents currently in the index."""
    registry = _load_registry()
    return {"documents": list(registry.values())}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Ingest a PDF.
    Returns document_id, name, page count, and chunk count.
    """
    from app.ingestion.parser import extract_text_from_pdf
    from app.ingestion.chunker import chunk_pages
    from app.ingestion.embedder import add_chunks
    from app.retrieval.bm25_store import build_bm25_index

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    document_id = str(uuid.uuid4())
    document_name = file.filename

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # ── Parse ──────────────────────────────────────────────────────────
        try:
            pages = extract_text_from_pdf(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF parsing failed: {e}")

        if not pages:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No extractable text found. The PDF may be scanned or image-based "
                    "and requires OCR, which is not currently supported."
                ),
            )

        # ── Chunk ──────────────────────────────────────────────────────────
        try:
            chunks = chunk_pages(pages, document_id=document_id, document_name=document_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chunking failed: {e}")

        # ── Embed + Store ──────────────────────────────────────────────────
        try:
            add_chunks(chunks, collection_name=CHROMA_COLLECTION)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding/indexing failed: {e}")

        # ── BM25 index (non-fatal failure) ─────────────────────────────────
        try:
            build_bm25_index(chunks)
        except Exception as e:
            print(f"BM25 index build warning (non-fatal): {e}")

    finally:
        os.unlink(tmp_path)

    # ── Registry ───────────────────────────────────────────────────────────
    registry = _load_registry()
    registry[document_id] = {
        "document_id": document_id,
        "name": document_name,
        "pages": len(pages),
        "chunks": len(chunks),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(registry)

    return {
        "message": "uploaded",
        "document_id": document_id,
        "name": document_name,
        "pages": len(pages),
        "chunks": len(chunks),
    }


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Remove a document from ChromaDB, BM25, and the registry."""
    from app.ingestion.embedder import delete_document as chroma_delete
    from app.retrieval.bm25_store import delete_document_bm25

    registry = _load_registry()
    if document_id not in registry:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        chroma_delete(document_id, collection_name=CHROMA_COLLECTION)
    except Exception as e:
        print(f"ChromaDB delete warning: {e}")

    try:
        delete_document_bm25(document_id)
    except Exception as e:
        print(f"BM25 delete warning: {e}")

    del registry[document_id]
    _save_registry(registry)

    return {"message": "deleted", "document_id": document_id}


@app.post("/query")
def query(req: QueryRequest):
    """
    Hybrid RAG query with document isolation, conversation memory,
    query rewriting, and streaming SSE response.

    SSE event types emitted:
      sources   — list of {document_id, source, page, section}
      token     — one LLM output token
      followups — list of 3 suggested follow-up question strings
      done      — signals end of stream
    """
    from app.ingestion.embedder import query_collection
    from app.generation.llm import answer_stream, rewrite_query
    from app.retrieval.bm25_store import search_bm25
    from app.retrieval.fusion import reciprocal_rank_fusion
    from app.retrieval.reranker import rerank
    from app.generation.memory import get_history, add_turn

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # document_id=None means search all documents
    document_id = None if req.search_all else req.document_id
    session_id = req.session_id

    # ── Conversation history ────────────────────────────────────────────────
    history = get_history(session_id)

    # ── Query rewriting ─────────────────────────────────────────────────────
    rewritten_q = rewrite_query(question, history)
    if DEBUG and rewritten_q != question:
        print(f"[DEBUG] Query rewrite: {question!r} → {rewritten_q!r}")

    # ── Vector retrieval ────────────────────────────────────────────────────
    try:
        vec_raw = query_collection(
            rewritten_q, k=20,
            document_id=document_id,
            collection_name=CHROMA_COLLECTION,
        )
        docs = vec_raw.get("documents", [[]])[0]
        mds = vec_raw.get("metadatas", [[]])[0]
        dists = vec_raw.get("distances", [[]])[0]
        vec_chunks = [
            {"text": d, "metadata": m, "vec_score": round(1.0 - dist, 4)}
            for d, m, dist in zip(docs, mds, dists)
        ]
    except Exception as e:
        print(f"Vector retrieval error: {e}")
        vec_chunks = []

    # ── BM25 retrieval ──────────────────────────────────────────────────────
    try:
        bm25_chunks = search_bm25(rewritten_q, k=20, document_id=document_id)
    except Exception as e:
        print(f"BM25 retrieval error: {e}")
        bm25_chunks = []

    # ── Fuse (RRF) → top-20 ────────────────────────────────────────────────
    fused = reciprocal_rank_fusion(vec_chunks, bm25_chunks, top_n=20)

    # ── Rerank → top-5 ─────────────────────────────────────────────────────
    final_chunks = rerank(rewritten_q, fused, top_n=5)

    if DEBUG:
        print(
            f"[DEBUG] vec={len(vec_chunks)}, bm25={len(bm25_chunks)}, "
            f"fused={len(fused)}, final={len(final_chunks)}"
        )
        for i, c in enumerate(final_chunks):
            md = c.get("metadata", {})
            print(
                f"[DEBUG]  chunk {i+1}: page={md.get('page')}, "
                f"rrf={c.get('rrf_score', 0):.4f}, "
                f"rerank={c.get('rerank_score', 'N/A')}"
            )

    # ── No results ──────────────────────────────────────────────────────────
    if not final_chunks:
        def _empty():
            msg = (
                "I couldn't find enough information in this document to answer that question. "
                "Try rephrasing, or make sure the relevant PDF is selected."
            )
            yield f"event: token\ndata: {msg}\n\n"
            yield "event: done\ndata: [DONE]\n\n"
        return StreamingResponse(_empty(), media_type="text/event-stream")

    # ── Build sources ───────────────────────────────────────────────────────
    seen: set = set()
    sources: list[dict] = []
    for chunk in final_chunks:
        md = chunk.get("metadata") or {}
        key = (md.get("document_id", ""), md.get("page", 0))
        if key not in seen:
            seen.add(key)
            sources.append({
                "document_id": md.get("document_id", ""),
                "source":      md.get("document_name", md.get("source", "unknown")),
                "page":        md.get("page", 0),
                "section":     md.get("section_title", ""),
            })

    # ── Stream ──────────────────────────────────────────────────────────────
    def event_stream():
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        full_answer: list[str] = []
        for event_type, data in answer_stream(rewritten_q, final_chunks, history):
            if event_type == "token":
                full_answer.append(data)
                safe = data.replace("\n", "\\n")
                yield f"event: token\ndata: {safe}\n\n"
            elif event_type == "followups" and data:
                yield f"event: followups\ndata: {json.dumps(data)}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

        # Store turn in memory after stream ends
        assembled = "".join(full_answer)
        add_turn(session_id, "user", question)
        add_turn(session_id, "assistant", assembled[:1200])

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Frontend Static Files ─────────────────────────────────────────────────────

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not built")