# Gov Scheme RAG Chatbot — Walkthrough

I have successfully built the complete architecture for the RAG chatbot! The solution spans a FastAPI backend with PostgreSQL `pgvector`, a robust local ingestion pipeline, multi-LLM fallback logic, security guardrails, and a premium React/Vite frontend.

## 🏗️ Project Architecture Overview

The system is split into two primary pipelines:

1. **Ingestion Pipeline** (Offline Pre-Computation)
   - Reads PDFs/TXTs from `docs/incoming/`.
   - Uses `PyMuPDF` for fast text extraction and `Tesseract OCR` for scanned images.
   - Chunks text logically, generates embeddings, and inserts them into PostgreSQL with `pgvector` index.
   - Also populates a full-text search `tsvector` index for BM25 keyword matching at the page level.

2. **Query Pipeline** (Real-Time API)
   - **Security First**: Runs Presidio PII masking, prompt injection regex, and a custom restricted-keyword filter.
   - **Hybrid Search**: First performs a fast BM25 search to get top pages, then a semantic vector search within those pages.
   - **Re-Ranking**: Uses a local cross-encoder (`ms-marco-MiniLM-L-6-v2`) to re-score chunks to reduce hallucination.
   - **Fallback Chain**: Tries `GPT-4o-mini` → `Gemini 1.5 Flash` → `Ollama`.
   - **Grounding**: If chunks yield low confidence, it performs a live Google Search.
   - **Streaming Output**: Connects to the React frontend via Server-Sent Events (SSE).

## 🚀 How to Run the Project

### 1. Configure the Environment
1. Copy the environment template: `cp .env.example .env`
2. Open `.env` and fill in your API keys:
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY`
   - `GOOGLE_SEARCH_API_KEY` (if grounding enabled)

### 2. Start the Database and Infrastructure
You can run the full stack (DB, Backend, Frontend) using Docker Compose:
```bash
docker compose up --build -d
```
> This will start the `pgvector` database, the backend API on port `8000`, and the React frontend on port `5173`.

### 3. Ingest Your Documents
Drop your government policy PDFs or TXT files into the `docs/incoming/` folder.
To process them, run the ingestion script from inside the backend container (or locally if you installed `requirements.txt`):
```bash
# Ingest all files in the directory
#docker exec -it ragchatbot_backend python app/ingestion/ingest.py --dir ./docs/incoming

# OCR only (PDF → txt, PDF moves to processed/failed)
docker-compose run --rm ocr

# Ingest only (txt → embeddings, txt moves to processed/failed)
docker-compose run --rm ingest

# Both sequentially — recommended
docker-compose run --rm pipeline

# docker-compose run --rm ingest
# docker exec -it ragchatbot_backend alembic upgrade head
# docker exec -it ragchatbot_backend env PYTHONPATH=. python app/ingestion/ingest.py --dir ./docs/incoming

# Or ingest a single file (Zero-Downtime update)
docker exec -it ragchatbot_backend python app/ingestion/ingest.py --file ./docs/incoming/new_policy.pdf
```

### 4. Interact with the Chatbot
Open your browser and navigate to:
[http://localhost:5173](http://localhost:5173)

You will see the premium glassmorphic UI where you can test out queries.

## 🛡️ Security Testing

You can verify the security guards by running the smoke tests locally:
```bash
docker exec -it ragchatbot_backend python -m app.core.security_test
```
You can also run the full test suite with:
```bash
docker exec -it ragchatbot_backend pytest tests/
```

## 🔄 LLM Fallback Chain
By default, the `.env` has `LLM_FALLBACK_ORDER=1,2,3` configured:
1. **OpenAI** (Primary)
2. **Gemini** (Fallback 1)
3. **Ollama** (Fallback 2, Requires local Ollama running)

If the OpenAI API rate limits you, it will instantly failover to Gemini, ensuring zero downtime for the user.

# remove old build
docker compose down --remove-orphans
docker rmi version_2_ag-pipeline
docker builder prune -f

# run new Build
docker compose down          # stop + remove containers first
docker compose build --no-cache

# bring up DB + app services
docker compose up -d

# then trigger the pipeline whenever you drop PDFs in incoming/
docker compose run --rm pipeline
# Or run steps individually
docker compose --profile ocr run --rm ocr        # OCR only
docker compose --profile ingest run --rm ingest  # embed only

# Activate Virtual Environment (FAST API)
uvicorn app.main:app --app-dir backend --reload --port 7860

# when changes ingest.py
docker compose build pipeline

# SQlArchamry running or table creation
docker compose run --rm pipeline alembic upgrade head

# Logs
docker compose logs -f web

# SQL start
docker exec -it ragchatbot_postgres psql -U raguser -d ragchatbot
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops); # for index (run only once)
CREATE INDEX ON pages USING gin (search_vector); # for index (run only once)