from langchain_text_splitters import RecursiveCharacterTextSplitter

s = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

def chunk_pages(pg, source):
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