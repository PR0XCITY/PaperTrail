import json
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/st_cache"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/hf_cache"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs after server binds to port — Render won't kill it for slow startup.
    Warms up the embedding model so the first upload request doesn't OOM.
    """
    import asyncio

    async def warm_up():
        try:
            print("Warming up embedding model...")
            from app.ingestion.embedder import get_model
            get_model()  # downloads + loads model into memory
            print("Embedding model ready")
        except Exception as e:
            print(f"Warm-up failed (non-fatal): {e}")

    # Run warm-up in background — don't block server startup
    asyncio.create_task(warm_up())
    yield
    print("Shutting down")


app = FastAPI(title="PaperTrail API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "default"


@app.get("/health")
def health():
    from app.ingestion.embedder import _model
    return {
        "status": "ok",
        "model_loaded": _model is not None
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    from app.ingestion.parser import extract_text_from_pdf
    from app.ingestion.chunker import chunk_pages
    from app.ingestion.embedder import add_chunks
    from app.retrieval.bm25_store import build_bm25_index

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        pages = extract_text_from_pdf(tmp_path)
        if not pages:
            raise HTTPException(status_code=422, detail="No extractable text found in PDF.")

        chunks = chunk_pages(pages, source=file.filename)
        add_chunks(COLLECTION_NAME, chunks)
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
    from app.ingestion.embedder import query_collection
    from app.generation.llm import answer_stream
    from app.retrieval.bm25_store import search_bm25
    from app.retrieval.fusion import reciprocal_rank_fusion

    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string 'q' cannot be empty.")

    vec_raw = query_collection(collection, q, k=10)
    docs = vec_raw.get("documents", [[]])[0]
    mds = vec_raw.get("metadatas", [[]])[0]
    vec_chunks = [{"text": d, "metadata": m} for d, m in zip(docs, mds)]

    bm25_chunks = search_bm25(collection, q, k=10)
    fused = reciprocal_rank_fusion(vec_chunks, bm25_chunks, top_n=5)

    if not fused:
        def empty():
            yield "event: done\ndata: [DONE]\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

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

    def event_stream():
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
        for token in answer_stream(q, fused):
            safe = token.replace("\n", "\\n")
            yield f"event: token\ndata: {safe}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")