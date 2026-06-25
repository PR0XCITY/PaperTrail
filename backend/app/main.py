import json
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ── IMPORTANT: No heavy imports at module level ──────────────────────────────
# All AI/ML imports (sentence_transformers, chromadb, fitz, langchain, groq)
# are deferred to first request.  This lets the server bind to $PORT instantly
# on Render's 512 MB free tier without triggering the OOM killer.

app = FastAPI(title="PaperTrail API", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "default"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Lazy imports — only loaded on first upload request
    from app.ingestion.parser import extract_text_from_pdf
    from app.ingestion.chunker import chunk_pages
    from app.ingestion.embedder import add_chunks
    from app.retrieval.bm25_store import build_bm25_index

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save upload to a temp file so PyMuPDF can open it by path
    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        pages = extract_text_from_pdf(tmp_path)
        if not pages:
            raise HTTPException(status_code=422, detail="No extractable text found in PDF.")

        chunks = chunk_pages(pages, source=file.filename)

        # ── Vector store ────────────────────────────────────────────────────
        add_chunks(COLLECTION_NAME, chunks)

        # ── BM25 index ──────────────────────────────────────────────────────
        build_bm25_index(COLLECTION_NAME, chunks)

    finally:
        os.unlink(tmp_path)

    return {
        "message": "uploaded",
        "pages": len(pages),
        "chunks": len(chunks),
    }


@app.get("/query")
def query(q: str, collection: str = COLLECTION_NAME):
    # Lazy imports — only loaded on first query request
    from app.ingestion.embedder import query_collection
    from app.generation.llm import answer_stream
    from app.retrieval.bm25_store import search_bm25
    from app.retrieval.fusion import reciprocal_rank_fusion

    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string 'q' cannot be empty.")

    # ── Vector search (top-10) ────────────────────────────────────────────────
    vec_raw = query_collection(collection, q, k=10)
    docs = vec_raw.get("documents", [[]])[0]
    mds = vec_raw.get("metadatas", [[]])[0]
    vec_chunks = [{"text": d, "metadata": m} for d, m in zip(docs, mds)]

    # ── BM25 search (top-10) ──────────────────────────────────────────────────
    bm25_chunks = search_bm25(collection, q, k=10)

    # ── RRF fusion → top-5 ────────────────────────────────────────────────────
    fused = reciprocal_rank_fusion(vec_chunks, bm25_chunks, top_n=5)

    if not fused:
        def empty():
            yield "event: done\ndata: [DONE]\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    # ── Build deduplicated sources list ───────────────────────────────────────
    seen: set[tuple] = set()
    sources: list[dict] = []
    for chunk in fused:
        md = chunk.get("metadata") or {}
        src = md.get("source", "unknown")
        page = md.get("page", 0)
        key = (src, page)
        if key not in seen:
            seen.add(key)
            sources.append({"source": src, "page": page})

    # ── SSE stream ────────────────────────────────────────────────────────────
    def event_stream():
        # 1. sources event (always first)
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        # 2. token events
        for token in answer_stream(q, fused):
            # Escape embedded newlines so each SSE message stays on one data line
            safe = token.replace("\n", "\\n")
            yield f"event: token\ndata: {safe}\n\n"

        # 3. done event
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")