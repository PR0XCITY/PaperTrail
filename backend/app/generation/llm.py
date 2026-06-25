from app.config import GROQ_API_KEY

# ── Lazy singleton ────────────────────────────────────────────────────────────
# The Groq client is only created when the first LLM call is made.

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _build_prompt(q, ch):
    ctx = "\n\n".join([x["text"] for x in ch])
    return f"""Answer only from context.

Context:
{ctx}

Question:
{q}

If answer does not exist, reply NOT FOUND.
"""

def answer(q, ch):
    r = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": _build_prompt(q, ch)}],
        temperature=0.1
    )
    return r.choices[0].message.content

def answer_stream(q, ch):
    """Yields token strings from Groq streaming API."""
    stream = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": _build_prompt(q, ch)}],
        temperature=0.1,
        stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta