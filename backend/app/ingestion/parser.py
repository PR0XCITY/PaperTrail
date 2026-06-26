"""
PDF parser — extracts text and headings from each page via PyMuPDF.
Lazy import: fitz (~15 MB) is only loaded when the first PDF is processed.
"""


def extract_text_from_pdf(fp: str) -> list[dict]:
    """
    Parse a PDF file and return a list of page dicts.

    Returns
    -------
    list of {
        "page_num":  int,   1-indexed
        "text":      str,   full page text (stripped)
        "headings":  list[str]  up to 3 candidate headings detected on the page
    }
    Empty pages (no extractable text) are silently skipped.
    """
    import fitz  # lazy import — PyMuPDF

    doc = fitz.open(fp)
    pages = []

    for i, page in enumerate(doc):
        raw = page.get_text("text")
        text = raw.strip()
        if not text:
            continue  # skip image-only / blank pages

        headings = _extract_headings(text)
        pages.append({
            "page_num": i + 1,
            "text": text,
            "headings": headings,
        })

    doc.close()
    return pages


def _extract_headings(text: str) -> list[str]:
    """
    Heuristic heading detector.
    A heading candidate is a line that is:
      - Short (4–80 characters)
      - Either ALL CAPS or Title Cased (≤ 8 words)
      - Not a lone number or punctuation
    Returns up to 3 headings per page.
    """
    headings = []
    for line in text.split("\n"):
        line = line.strip()
        if not (4 <= len(line) <= 80):
            continue
        if line.replace(".", "").replace(",", "").isdigit():
            continue  # skip page numbers / numeric lines
        words = line.split()
        is_upper = line.isupper() and len(words) <= 10
        is_title = line.istitle() and len(words) <= 8
        if is_upper or is_title:
            headings.append(line)
        if len(headings) == 3:
            break
    return headings