"""
LLM generation — Groq streaming API with:
  - Production-quality system prompt
  - Conversation history (multi-turn)
  - Query rewriting (pronoun resolution)
  - Follow-up question generation
"""
import json

from app.config import GROQ_API_KEY

_client = None

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are PaperTrail, an expert PDF research assistant. Your job is to answer questions strictly based on the retrieved context from the user's documents.

Rules you must follow:
1. Answer ONLY from the retrieved context provided. Never invent, assume, or extrapolate facts not present in the context.
2. If the context is insufficient, say exactly: "I couldn't find enough information in this document to answer that question." Then briefly describe what the context does cover.
3. When multiple chunks discuss the same concept, synthesize them into one coherent explanation — never repeat yourself.
4. Always cite page numbers inline using [p.X] notation immediately after each claim.
5. Use clear formatting: bullet points or numbered lists when listing items, bold for key terms.
6. Be precise and concise. Avoid filler phrases like "Great question!" or "Certainly!".
7. If asked about something outside the document, politely clarify that you can only answer from the uploaded content.\
"""

# ── Singleton ─────────────────────────────────────────────────────────────────

def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ── Query Rewriting ───────────────────────────────────────────────────────────

_PRONOUNS = {
    "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "he", "she", "the document", "the pdf",
    "the section", "the topic", "the concept", "aforementioned",
}


def rewrite_query(question: str, history: list[dict]) -> str:
    """
    Resolve pronouns and dangling references using conversation history.

    Uses llama-3.1-8b-instant for speed (cheap, ~50ms).
    Only triggers when the question contains pronoun-like words AND there's history.
    Returns the original question unchanged if rewriting fails.
    """
    if not history:
        return question

    words = set(question.lower().split())
    if not (words & _PRONOUNS):
        return question  # no pronouns detected — skip rewrite

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history[-6:]
    )
    prompt = (
        f"Conversation so far:\n{history_text}\n\n"
        f'Rewrite this follow-up question to be completely self-contained '
        f'(resolve all pronouns, abbreviations, and references): "{question}"\n\n'
        f"Return ONLY the rewritten question. No explanation, no quotes."
    )

    try:
        resp = _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,
        )
        rewritten = resp.choices[0].message.content.strip().strip('"').strip("'")
        return rewritten if rewritten else question
    except Exception as e:
        print(f"Query rewrite failed (using original): {e}")
        return question


# ── Context Builder ───────────────────────────────────────────────────────────

def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        page = meta.get("page", "?")
        section = meta.get("section_title", "")
        header = f"[Chunk {i} | Page {page}" + (f" | {section}" if section else "") + "]"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


# ── Streaming Answer ──────────────────────────────────────────────────────────

def answer_stream(
    question: str,
    chunks: list[dict],
    history: list[dict] = None,
):
    """
    Stream the answer token by token, then yield follow-up questions.

    Yields
    ------
    ("token",    str)       — one LLM output token
    ("followups", list[str]) — 3 suggested follow-up questions (single yield at end)
    """
    history = history or []
    context = _build_context(chunks)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject last 6 turns of conversation history
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    user_content = (
        f"Context retrieved from the PDF:\n"
        f"{'─' * 60}\n"
        f"{context}\n"
        f"{'─' * 60}\n\n"
        f"Question: {question}"
    )
    messages.append({"role": "user", "content": user_content})

    stream = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        stream=True,
    )

    full_response_parts: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_response_parts.append(delta)
            yield ("token", delta)

    # After streaming completes, generate follow-up questions
    full_response = "".join(full_response_parts)
    followups = _generate_followups(question, full_response, context)
    yield ("followups", followups)


# ── Follow-up Generator ───────────────────────────────────────────────────────

def _generate_followups(question: str, answer: str, context: str) -> list[str]:
    """Generate 3 follow-up questions based on the answer and retrieved context."""
    prompt = (
        f"The user asked: {question}\n\n"
        f"The answer given: {answer[:600]}\n\n"
        f"Context excerpt: {context[:800]}\n\n"
        f"Suggest exactly 3 concise follow-up questions the user might want to ask next "
        f"about this document. Make them specific and grounded in the context.\n\n"
        f"Respond with ONLY a JSON array of 3 strings, no other text:\n"
        f'["Question 1?", "Question 2?", "Question 3?"]'
    )

    try:
        resp = _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, list):
                return [str(q) for q in parsed[:3]]
    except Exception as e:
        print(f"Follow-up generation failed (non-fatal): {e}")

    return []