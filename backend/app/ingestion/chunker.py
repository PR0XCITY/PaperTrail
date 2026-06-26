"""
Chunker — splits PDF pages into overlapping text chunks with full metadata.
Lazy import: RecursiveCharacterTextSplitter is only loaded on first use.
"""
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

_splitter = None


def _get_splitter():
    global _splitter
    if _splitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    return _splitter


def chunk_pages(pages: list[dict], document_id: str, document_name: str) -> list[dict]:
    """
    Split PDF pages into chunks, attaching full provenance metadata to each.

    Parameters
    ----------
    pages         : output of extract_text_from_pdf()
    document_id   : UUID assigned at upload time
    document_name : original filename

    Returns
    -------
    list of {
        "text":     str,
        "metadata": {
            "document_id":   str,
            "document_name": str,
            "source":        str,   # alias for document_name (backward compat)
            "page":          int,
            "section_title": str,
            "chunk_index":   int,
        }
    }
    """
    splitter = _get_splitter()
    chunks = []

    for page in pages:
        page_num = page["page_num"]
        text = page["text"]
        headings = page.get("headings", [])
        section_title = headings[0] if headings else ""

        split_texts = splitter.split_text(text)

        for i, t in enumerate(split_texts):
            chunks.append({
                "text": t,
                "metadata": {
                    "document_id":   document_id,
                    "document_name": document_name,
                    "source":        document_name,  # backward compat with citation UI
                    "page":          page_num,
                    "section_title": section_title,
                    "chunk_index":   i,
                },
            })

    return chunks