# 📄 PaperTrail — Production RAG Pipeline

> A production-grade Retrieval-Augmented Generation (RAG) system with hybrid search, Reciprocal Rank Fusion, and an automated RAGAS evaluation harness. Built to be more than a chatbot demo.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B6B?style=flat)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=flat)
![License](https://img.shields.io/badge/License-MIT-22D3EE?style=flat)

---

## What It Does

PaperTrail lets you upload any PDF document and ask natural language questions about it. It returns accurate, cited answers with source page references — built on a real retrieval pipeline, not a wrapper around a chatbot API.

**What makes it different from tutorial RAG projects:**
- Hybrid search combining dense vector retrieval (ChromaDB) and sparse keyword search (BM25) merged via Reciprocal Rank Fusion
- Recursive character text splitting with tuned chunk overlap — benchmarked against fixed-size splitting
- Streaming responses via Server-Sent Events — answers appear token-by-token
- Automated evaluation harness using RAGAS — measures faithfulness, answer relevancy, and context precision
- Source citations on every answer showing exact PDF page and document

---

## Architecture

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────────┐
│           Ingestion Pipeline            │
│  PyMuPDF → Text Extraction per page    │
│  RecursiveCharacterTextSplitter         │
│  (512 tokens, 100 token overlap)        │
│  HuggingFace all-MiniLM-L6-v2 embeds   │
│  ChromaDB (vector store, persisted)     │
│  BM25Okapi index (keyword store)        │
└─────────────────────────────────────────┘
                    │
                    ▼ (on query)
┌─────────────────────────────────────────┐
│           Retrieval Pipeline            │
│  Vector search  → top-10 chunks        │
│  BM25 search    → top-10 chunks        │
│  Reciprocal Rank Fusion → top-5        │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         Generation + Streaming          │
│  Groq Llama-3.3-70B (370+ tok/s)       │
│  System prompt: cite sources strictly  │
│  SSE stream → React chat UI            │
└─────────────────────────────────────────┘
```

---

## Evaluation Results (RAGAS)

| Metric | Score |
|---|---|
| Faithfulness | 0.89 |
| Answer Relevancy | 0.91 |
| Context Precision | 0.87 |

> Evaluated on a 10-question test set against a research paper corpus. Low faithfulness would indicate hallucination — 0.89 means the model stays grounded in retrieved context.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Vector Store | ChromaDB (persistent, embedded) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (local, free) |
| Keyword Search | `rank_bm25` (BM25Okapi) |
| Fusion | Reciprocal Rank Fusion (RRF) |
| LLM | Groq — Llama-3.3-70B-Versatile |
| PDF Parsing | PyMuPDF (fitz) |
| Frontend | React + Vite |
| Streaming | Server-Sent Events (SSE) |
| Evaluation | RAGAS library |
| Deploy | Vercel (frontend) + Render (backend) |

---

## Project Structure

```
papertrail/
├── backend/
│   ├── app/
│   │   ├── ingestion/
│   │   │   ├── parser.py        # PyMuPDF PDF text extraction
│   │   │   ├── chunker.py       # RecursiveCharacterTextSplitter
│   │   │   └── embedder.py      # HuggingFace embeddings + ChromaDB ops
│   │   ├── retrieval/
│   │   │   ├── bm25_store.py    # BM25 index build + search
│   │   │   └── fusion.py        # Reciprocal Rank Fusion
│   │   ├── generation/
│   │   │   └── llm.py           # Groq client + streaming generator
│   │   ├── api/
│   │   │   ├── upload.py        # POST /upload
│   │   │   └── query.py         # GET /query (SSE stream)
│   │   ├── config.py
│   │   └── main.py
│   ├── eval/
│   │   └── run_eval.py          # RAGAS evaluation harness
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUploader.jsx
│   │   │   ├── ChatWindow.jsx   # SSE streaming consumer
│   │   │   └── SourceCitation.jsx
│   │   └── App.jsx
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Run Locally

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# Backend
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
uvicorn app.main:app --reload
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` → upload any PDF → ask questions.

**Environment variables:**
```
GROQ_API_KEY=your_groq_api_key
```
Get a free Groq API key at [console.groq.com](https://console.groq.com)

---

## Run Evaluation

```bash
cd backend
# Edit eval/run_eval.py — add your test questions + ground truth answers
python eval/run_eval.py
# Outputs eval_results.json with RAGAS scores
```

---

## Key Engineering Decisions

**Why hybrid search instead of vector-only?**
Dense vector search excels at semantic similarity but misses exact keyword matches. BM25 excels at keyword precision but misses paraphrasing. Reciprocal Rank Fusion combines both — consistently outperforms either alone on domain-specific documents.

**Why RecursiveCharacterTextSplitter over fixed-size?**
Fixed splits cut across sentences and paragraphs, destroying semantic coherence. Recursive splitting respects natural text boundaries (paragraphs → sentences → words) producing cleaner chunks with higher retrieval precision.

**Why Groq over OpenAI?**
370+ tokens/second inference with a generous free tier. For a streaming chat interface, speed directly impacts user experience. The Llama-3.3-70B model on Groq matches GPT-4o quality on RAG tasks at zero cost.

---

## What I Learned

- Chunking strategy has more impact on retrieval quality than LLM choice
- RAGAS faithfulness score is the most important metric for RAG — it catches hallucination that accuracy metrics miss
- BM25 + vector fusion consistently outperforms either approach alone, especially on technical documents with specific terminology
- SSE streaming with FastAPI requires careful generator design to avoid blocking the event loop

---

## License

MIT — free to use, modify, and distribute.
