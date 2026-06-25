# ── Lazy singleton ────────────────────────────────────────────────────────────
# langchain_text_splitters is only imported when the first PDF needs chunking.

_splitter = None


def _get_splitter():
    global _splitter
    if _splitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
    return _splitter


def chunk_pages(pg, source):
    s = _get_splitter()
    ch = []

    for p in pg:
        sp = s.split_text(p["text"])

        for i, t in enumerate(sp):
            ch.append({
                "text": t,
                "metadata": {
                    "source": source,
                    "page": p["page_num"],
                    "chunk_index": i
                }
            })

    return ch