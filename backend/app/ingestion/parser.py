import fitz

def extract_text_from_pdf(fp):
    d = fitz.open(fp)

    p = []

    for i, pg in enumerate(d):
        t = pg.get_text("text").strip()

        if t:
            p.append({
                "page_num": i + 1,
                "text": t
            })

    d.close()

    return p