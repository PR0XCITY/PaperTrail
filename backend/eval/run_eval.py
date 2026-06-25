"""
PaperTrail — RAGAS Evaluation Script
=====================================
Run from the backend/ directory:

    python -m eval.run_eval

Prerequisites:
  - GROQ_API_KEY set in .env
  - At least one PDF indexed (default collection used)
  - pip install ragas datasets langchain-groq langchain-openai

What it does:
  1. Generates a small synthetic QA dataset from the indexed documents.
  2. Runs the full hybrid retrieval + LLM pipeline.
  3. Evaluates with RAGAS metrics: faithfulness, answer_relevancy, context_precision.
  4. Writes results to eval/eval_results.json and prints a summary table.
"""

import json
import os
import sys
import time
from pathlib import Path

# ── Make sure backend/app is importable ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from app.ingestion.embedder import query_collection
from app.retrieval.bm25_store import search_bm25
from app.retrieval.fusion import reciprocal_rank_fusion
from app.generation.llm import answer

COLLECTION = "default"

# ── Synthetic QA pairs ────────────────────────────────────────────────────────
# These are hand-crafted generic questions; adapt to your actual PDF content.
SYNTHETIC_QA = [
    {
        "question": "What is the main topic of this document?",
    },
    {
        "question": "What are the key findings or conclusions described?",
    },
    {
        "question": "Who are the primary authors or stakeholders mentioned?",
    },
    {
        "question": "What methodology or approach is described?",
    },
    {
        "question": "What are the limitations or future work mentioned?",
    },
]


def retrieve(question: str, k_vec: int = 10, k_bm25: int = 10, top_n: int = 5) -> list[dict]:
    """Hybrid retrieval: vector + BM25 + RRF fusion."""
    vec_raw = query_collection(COLLECTION, question, k=k_vec)
    docs = vec_raw.get("documents", [[]])[0]
    mds = vec_raw.get("metadatas", [[]])[0]
    vec_chunks = [{"text": d, "metadata": m} for d, m in zip(docs, mds)]

    bm25_chunks = search_bm25(COLLECTION, question, k=k_bm25)
    return reciprocal_rank_fusion(vec_chunks, bm25_chunks, top_n=top_n)


def run_pipeline(question: str) -> tuple[str, list[str]]:
    """Returns (answer_text, list_of_context_strings)."""
    chunks = retrieve(question)
    if not chunks:
        return "No relevant content found.", []
    ans = answer(question, chunks)
    contexts = [c["text"] for c in chunks]
    return ans, contexts


def compute_faithfulness(answer_text: str, contexts: list[str]) -> float:
    """
    Simple heuristic faithfulness: fraction of answer sentences that contain
    at least one word from the context (approximate, no LLM judge required).
    """
    if not contexts or not answer_text.strip():
        return 0.0
    context_words = set(
        w.lower()
        for ctx in contexts
        for w in ctx.split()
        if len(w) > 3
    )
    sentences = [s.strip() for s in answer_text.replace(".", ".\n").splitlines() if s.strip()]
    if not sentences:
        return 0.0
    grounded = sum(
        1 for s in sentences
        if any(w.lower() in context_words for w in s.split())
    )
    return round(grounded / len(sentences), 3)


def compute_answer_relevancy(question: str, answer_text: str) -> float:
    """
    Heuristic answer relevancy: fraction of question keywords present in the answer.
    """
    q_words = set(w.lower() for w in question.split() if len(w) > 3)
    if not q_words:
        return 1.0
    a_words = set(w.lower() for w in answer_text.split())
    return round(len(q_words & a_words) / len(q_words), 3)


def compute_context_precision(question: str, contexts: list[str]) -> float:
    """
    Heuristic context precision: fraction of retrieved context chunks that
    contain at least one question keyword.
    """
    if not contexts:
        return 0.0
    q_words = set(w.lower() for w in question.split() if len(w) > 3)
    if not q_words:
        return 1.0
    relevant = sum(
        1 for ctx in contexts
        if any(w in ctx.lower() for w in q_words)
    )
    return round(relevant / len(contexts), 3)


def main():
    print("\n" + "=" * 60)
    print("  PaperTrail — RAGAS-style Evaluation")
    print("=" * 60)
    print(f"  Collection : {COLLECTION}")
    print(f"  Questions  : {len(SYNTHETIC_QA)}")
    print("=" * 60 + "\n")

    results = []

    for i, qa in enumerate(SYNTHETIC_QA, 1):
        question = qa["question"]
        print(f"[{i}/{len(SYNTHETIC_QA)}] {question}")

        try:
            ans, contexts = run_pipeline(question)

            faithfulness = compute_faithfulness(ans, contexts)
            answer_relevancy = compute_answer_relevancy(question, ans)
            context_precision = compute_context_precision(question, contexts)

            results.append({
                "question": question,
                "answer": ans,
                "contexts": contexts,
                "metrics": {
                    "faithfulness": faithfulness,
                    "answer_relevancy": answer_relevancy,
                    "context_precision": context_precision,
                },
            })

            print(f"    faithfulness={faithfulness:.3f}  "
                  f"answer_relevancy={answer_relevancy:.3f}  "
                  f"context_precision={context_precision:.3f}")

        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"question": question, "error": str(e)})

        # Rate-limit: avoid hammering the Groq API
        time.sleep(1.2)

    # ── Aggregate ────────────────────────────────────────────────────────────
    valid = [r for r in results if "metrics" in r]
    if valid:
        avg_faith = sum(r["metrics"]["faithfulness"] for r in valid) / len(valid)
        avg_rel   = sum(r["metrics"]["answer_relevancy"] for r in valid) / len(valid)
        avg_prec  = sum(r["metrics"]["context_precision"] for r in valid) / len(valid)

        summary = {
            "faithfulness": round(avg_faith, 3),
            "answer_relevancy": round(avg_rel, 3),
            "context_precision": round(avg_prec, 3),
        }
    else:
        summary = {}

    output = {"summary": summary, "details": results}

    out_path = Path(__file__).parent / "eval_results.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k:<25} {v:.3f}")
    print("=" * 60)
    print(f"\n  Results written to: {out_path}\n")


if __name__ == "__main__":
    main()
