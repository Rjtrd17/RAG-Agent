# 🤖 The Secretariat — Government Scheme RAG Chatbot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)

**A production-grade Retrieval-Augmented Generation (RAG) chatbot for 1000+ Government Policy PDFs.**  
Answers any citizen query in ≤ 3 seconds at ~₹0.2–0.5/query cost.

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [Document Ingestion](#-document-ingestion)
- [LLM Fallback System](#-llm-fallback-system)
- [Security](#-security)
- [API Reference](#-api-reference)
- [Running Tests](#-running-tests)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌐 Overview

**The Secretariat** is a production-ready AI-powered chatbot built to help citizens, officials, and researchers instantly retrieve accurate information from thousands of government policy documents, schemes, and circulars.

- 📄 Ingests **1000+ PDF and TXT** government documents
- ⚡ Returns answers in **≤ 3 seconds**
- 💰 Runs at **~₹0.2–0.5 per query**
- 🔒 Enterprise-grade **security** with PII redaction, rate limiting, and keyword filtering
- 🌊 **Streaming responses** — users see the first tokens within ~300ms
- 🔄 **Zero-downtime** incremental document ingestion

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────┐
│              Security Guards                     │
│  PII Detection → Keyword Filter → Rate Limiter  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           Two-Stage Hybrid Retrieval            │
│  BM25 Full-Text Search (tsvector + GIN Index)  │
│              ↓  Top-20 Pages                    │
│  Semantic Vector Search (pgvector cosine)       │
│              ↓  Top-20 Chunks                   │
│  Cross-Encoder Re-Ranker  (Top-8 Chunks)        │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Google Custom Search Grounding          │
│    (Live web context for real-time queries)     │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           LLM Fallback Chain                    │
│  1. OpenAI GPT-4o-mini  (Primary)               │
│  2. Google Gemini 1.5 Flash  (Fallback)         │
│  3. Ollama llama3  (Local Fallback)             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
         Streaming Answer + Audit Log
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend API** | FastAPI (Python 3.11+) | Async REST API with streaming |
| **Vector DB** | PostgreSQL 15 + pgvector | Semantic similarity search |
| **Full-text BM25** | PostgreSQL tsvector + GIN Index | Keyword-based page retrieval |
| **OCR** | PyMuPDF + Tesseract | Text & scanned PDF extraction |
| **Embeddings** | OpenAI `text-embedding-3-small` / Ollama `nomic-embed-text` | Document vectorization |
| **LLM Primary** | OpenAI GPT-4o-mini | Answer generation |
| **LLM Fallback 2** | Google Gemini 1.5 Flash | Secondary answer generation |
| **LLM Fallback 3** | Ollama llama3 | Local offline fallback |
| **Re-ranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Result precision boost |
| **Grounding** | Google Custom Search API | Real-time web context |
| **Security** | Presidio + SlowAPI | PII redaction + rate limiting |
| **Frontend** | React 18 + Vite | Modern chat UI |
| **Container** | Docker Compose | One-command full-stack launch |
| **ORM / Migrations** | SQLAlchemy 2.0 + Alembic | Database management |

---

## ✨ Features

### 🔍 Intelligent Retrieval
- **Two-stage hybrid search**: BM25 page-level → semantic chunk-level
- **Cross-encoder re-ranking** for maximum precision
- **Configurable thresholds**: top-k pages, chunks, similarity cutoff

### 🤖 Multi-LLM with Fallback
- Automatic failover chain: GPT-4o-mini → Gemini 1.5 Flash → Ollama llama3
- Live toggle via Admin Panel — no restart needed

### 🔒 Security-First Design
- **Presidio PII detection** — blocks/redacts Aadhaar, PAN, phone numbers
- **SlowAPI rate limiting** — 60 requests/minute per client
- **Custom keyword filter** — blocks harmful/off-topic queries
- **JWT authentication** for admin endpoints
- **All security guards run BEFORE retrieval**

### 📄 Smart Document Ingestion
- Auto-detects text vs. scanned PDFs
- **OCR pipeline** for scanned documents (Tesseract + OpenCV)
- Semantic chunking with overlap using LangChain text splitters
- Incremental ingestion — **zero downtime**, live immediately
- Processes `.pdf` and `.txt` files

### 🌊 Real-time Streaming
- Server-Sent Events (SSE) streaming
- Users see first tokens in **~300ms**
- Progress indicators and follow-up question suggestions

### 📊 Audit & Observability
- Every query and answer logged to `audit_logs` PostgreSQL table
- Full request tracing with timestamps and LLM used

---

## 📁 Project Structure

```
Version_2_AG/
├── README.md
├── .env.example                  ← Copy to .env and fill your keys
├── .gitignore
├── docker-compose.yml            ← Full stack: postgres + backend + frontend
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                  ← Database migration scripts
│   ├── app/
│   │   ├── main.py               ← FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── chat.py           ← /api/chat/stream endpoint
│   │   │   └── admin.py          ← /api/admin/* endpoints
│   │   ├── core/
│   │   │   ├── config.py         ← Pydantic settings (reads .env)
│   │   │   ├── security.py       ← PII, keyword filter, rate limit
│   │   │   ├── fallback.py       ← LLM fallback orchestrator
│   │   │   └── security_test.py  ← Security smoke tests
│   │   ├── rag/
│   │   │   ├── retriever.py      ← BM25 + semantic hybrid retriever
│   │   │   ├── reranker.py       ← Cross-encoder re-ranker
│   │   │   ├── generator.py      ← LLM answer generator
│   │   │   └── grounding.py      ← Google Custom Search grounding
│   │   ├── ingestion/
│   │   │   ├── ingest.py         ← CLI: ingest PDFs/TXTs → embeddings
│   │   │   ├── ocr.py            ← OCR pipeline (Tesseract + OpenCV)
│   │   │   ├── chunker.py        ← Semantic text chunker
│   │   │   └── embedder.py       ← Embedding generation
│   │   ├── db/                   ← SQLAlchemy models + init SQL
│   │   └── output/               ← Answer formatter + follow-up generator
│   └── tests/                    ← pytest test suite
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── components/           ← Reusable UI components
│       └── pages/                ← Chat page, Admin page
│
└── docs/
    ├── incoming/                 ← Drop new PDFs/TXTs here
    ├── processed/                ← Moved here after ingestion
    ├── ocr_output/               ← OCR text output
    └── failed/                   ← Failed ingestion files
```

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| Docker & Docker Compose | Latest | Recommended for full stack |
| PostgreSQL | 15+ | With pgvector extension |
| Tesseract OCR | 5.x | For scanned PDF support |
| Git | Any | Version control |

---

## 🚀 Quick Start

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/secretariat-rag-chatbot.git
cd secretariat-rag-chatbot

# 2. Set up environment
cp .env.example .env
# Edit .env and fill in your API keys

# 3. Start the full stack
docker compose up --build

# 4. Access the app
# Frontend:  http://localhost:5173
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

### Option B — Local Development

```bash
# ── Backend ──────────────────────────────────────────
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Set up .env
cp .env.example .env
# Fill in your API keys

# 4. Run database migrations
alembic upgrade head

# 5. Start backend
uvicorn backend.app.main:app --reload --port 8000

# ── Frontend ─────────────────────────────────────────
cd frontend
npm install
npm run dev
# Frontend available at http://localhost:5173
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# ── PostgreSQL ────────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ragchatbot
POSTGRES_USER=raguser
POSTGRES_PASSWORD=your_secure_password

# ── LLM Configuration ────────────────────────────────
LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_ORDER=1,2,3
# 1 = OpenAI GPT-4o-mini
# 2 = Google Gemini 1.5 Flash
# 3 = Ollama llama3 (local)

# ── API Keys ─────────────────────────────────────────
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# ── Embeddings ───────────────────────────────────────
EMBEDDING_PROVIDER=openai          # openai | ollama
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ── Google Search Grounding ──────────────────────────
GOOGLE_SEARCH_API_KEY=AIza...
GOOGLE_SEARCH_ENGINE_ID=...
GOOGLE_SEARCH_ENABLED=true

# ── Security ─────────────────────────────────────────
SECRET_KEY=your_jwt_secret_key
RATE_LIMIT_PER_MINUTE=60

# ── RAG Tuning ───────────────────────────────────────
BM25_TOP_PAGES=20
SEMANTIC_TOP_CHUNKS=20
RERANKER_TOP_K=8
SIMILARITY_THRESHOLD=0.35

# ── App ──────────────────────────────────────────────
APP_ENV=development
APP_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📥 Document Ingestion

### Add New Documents (Zero-Downtime)

```bash
# 1. Drop your PDF or TXT into docs/incoming/
cp new_policy.pdf docs/incoming/

# 2. Ingest a single file
python backend/app/ingestion/ingest.py --file docs/incoming/new_policy.pdf

# 3. Ingest an entire directory
python backend/app/ingestion/ingest.py --dir docs/incoming/

# 4. Run OCR-only pipeline (for scanned PDFs)
docker compose --profile ocr up

# 5. Run full OCR + Ingest pipeline
docker compose --profile pipeline up
```

The script auto-detects text vs. scanned PDFs. Chunks are embedded and live **immediately** — no restart required.

---

## 🔄 LLM Fallback System

Control the LLM fallback order via `.env` or the **Admin Panel** (`http://localhost:5173/admin`):

```
LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_ORDER=1,2,3

# Provider map:
# 1 → OpenAI GPT-4o-mini    (Best quality, ~₹0.2/query)
# 2 → Gemini 1.5 Flash      (Fallback, fast & cheap)
# 3 → Ollama llama3         (Local, zero API cost)
```

Changes take effect **immediately** via the Admin Panel toggle — no redeploy needed.

---

## 🛡️ Security

| Guard | Technology | What it blocks |
|-------|-----------|----------------|
| PII Detection | Microsoft Presidio | Aadhaar, PAN, phone numbers, emails |
| Rate Limiting | SlowAPI | >60 req/min per IP |
| Keyword Filter | Custom regex | Harmful/off-topic queries |
| JWT Auth | python-jose | Protects admin endpoints |
| Audit Log | PostgreSQL | Every query logged with timestamp |

> **Important**: All security guards run **BEFORE** retrieval. Blocked queries are logged but never processed.

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | Health check |
| `GET /` | GET | Service info |
| `POST /api/chat/stream` | POST | Stream RAG answer (SSE) |
| `GET /api/admin/config` | GET | Get LLM config (JWT required) |
| `POST /api/admin/config` | POST | Update LLM config (JWT required) |
| `GET /docs` | GET | Interactive Swagger UI |
| `GET /redoc` | GET | ReDoc API documentation |

---

## 🧪 Running Tests

```bash
# Run full test suite
pytest backend/tests/ -v

# Run security smoke tests
python -m backend.app.core.security_test

# Check pgvector index health
python backend/scripts/check_index.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ for accessible governance and citizen empowerment.

**[Report Bug](../../issues)** · **[Request Feature](../../issues)** · **[API Docs](http://localhost:8000/docs)**

</div>
