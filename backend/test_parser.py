from app.ingestion.parser import extract_text_from_pdf
from app.ingestion.chunker import chunk_pages
from app.ingestion.embedder import (
    add_chunks,
    query_collection
)

from app.generation.llm import answer

pg = extract_text_from_pdf(
    "test.pdf"
)

ch = chunk_pages(
    pg,
    "test.pdf"
)

print(
    f"Pages: {len(pg)}"
)

print(
    f"Chunks: {len(ch)}"
)

add_chunks(
    "demo",
    ch
)

r = query_collection(
    "demo",
    "What is this project about?"
)

ctx = []

for d, m in zip(
    r["documents"][0],
    r["metadatas"][0]
):
    ctx.append({
        "text": d,
        "metadata": m
    })

a = answer(
    "What is this project about?",
    ctx
)

print("\nANSWER:\n")
print(a)