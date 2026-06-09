# AGENTS.md — Government Scheme RAG Chatbot

## Project Overview
A production-grade Retrieval-Augmented Generation (RAG) chatbot for 1000+ government policy PDFs and TXT files.
Answers any query in ≤ 3 seconds at ~₹0.2–0.5/query cost.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11+) |
| Vector DB | PostgreSQL 15 + pgvector extension |
| Full-text (BM25) | PostgreSQL tsvector + GIN index |
| OCR | PyMuPDF (text PDFs) + Tesseract (scanned PDFs) |
| Embeddings | OpenAI `text-embedding-3-small` OR Ollama `nomic-embed-text` |
| LLM Primary | OpenAI GPT-4o-mini |
| LLM Fallback 2 | Google Gemini 1.5 Flash |
| LLM Fallback 3 | Ollama llama3 (local) |
| Re-ranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local, no cost) |
| Grounding | Google Custom Search API |
| Security | Presidio (PII), SlowAPI (rate limit), custom keyword filter |
| Frontend | React + Vite |
| Container | Docker Compose |

---

## Architectural Conventions

1. **All config via `.env`** — Never hardcode secrets. Use `pydantic-settings`.
2. **Ingestion is fully decoupled** from the query API. Run `ingest.py` independently.
3. **LLM fallback order** is controlled by `LLM_FALLBACK_ORDER=1,2,3` in `.env`.
4. **Global fallback switch**: `LLM_FALLBACK_ENABLED=true/false`.
5. **Every query and answer** is logged to the `audit_logs` PostgreSQL table.
6. **Security guards run BEFORE retrieval** — blocked queries are logged but never processed.
7. **Streaming enabled** by default — user sees first tokens within ~300ms.
8. **Two-stage search**: BM25 page-level → semantic chunk-level → cross-encoder re-rank.

---

## Key Directories

```
Version_2_AG/
├── AGENTS.md             ← You are here
├── .env.example          ← Copy to .env and fill values
├── docker-compose.yml    ← Full stack launch
├── backend/
│   ├── app/
│   │   ├── main.py       ← FastAPI entrypoint
│   │   ├── api/          ← Route handlers
│   │   ├── core/         ← Config, security, fallback
│   │   ├── rag/          ← Retriever, reranker, generator, grounding
│   │   ├── ingestion/    ← ingest.py CLI + OCR + chunker + embedder
│   │   ├── db/           ← SQLAlchemy models + Alembic
│   │   └── output/       ← Formatter + follow-up generator
│   └── tests/
├── frontend/             ← React + Vite UI
└── docs/
    ├── incoming/         ← Drop new PDFs/TXTs here
    └── processed/        ← Moved here after ingestion
```

---

## Verification Commands

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run database migrations
alembic upgrade head

# Ingest all documents (first time)
python backend/app/ingestion/ingest.py --dir ./docs/incoming

# Ingest a single new PDF (incremental, zero downtime)
python backend/app/ingestion/ingest.py --file ./docs/incoming/new_policy.pdf

# Start full stack via Docker
docker compose up --build

# Start backend only (dev)
uvicorn backend.app.main:app --reload --port 8000

# Run tests
pytest backend/tests/ -v

# Run security guard smoke tests
python -m backend.app.core.security_test

# Check pgvector index health
python backend/scripts/check_index.py
```

---

## Adding New Documents (Zero-Downtime Process)

1. Drop PDF or TXT into `docs/incoming/`
2. Run: `python backend/app/ingestion/ingest.py --file docs/incoming/<filename>`
3. Script auto-detects text vs. scanned PDF, runs OCR if needed
4. Chunks are embedded and appended to pgvector — live immediately
5. No restart required

---

## LLM Fallback Configuration

Edit `.env`:
```
LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_ORDER=1,2,3
# 1 = OpenAI GPT-4o-mini
# 2 = Gemini 1.5 Flash  
# 3 = Ollama llama3 (local)
```

Or change live from the Admin Panel UI at `http://localhost:5173/admin`.
