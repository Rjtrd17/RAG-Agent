import json
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select  #  Added for async database querying
from app.db.session import get_db
from app.db.models import Document, Page  # Added to pull real names & page numbers
from app.core.config import get_settings
from app.core.security import run_security_guards
from app.rag.retriever import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.generator import generate_answer
from app.rag.grounding import google_search, format_grounding_context
from app.output.followup import generate_followups
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool

# Create a schema class defining your input structure
class ChatQuery(BaseModel):
    query: str

router = APIRouter()

async def get_embedding(text: str, settings) -> list[float]:
    # Placeholder: normally calls app.ingestion.embedder
    return [0.1] * 1536

async def log_audit(db: AsyncSession, query, answer, chunks, llm, cost):
    # normally insert into audit_logs table
    pass

@router.post("/chat")
async def chat_endpoint(chat_input: ChatQuery, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = chat_input.query
    settings = get_settings()
    
    # 1. Security Guards
    sec_res = run_security_guards(query)
    if not sec_res["allowed"]:
        bg_tasks.add_task(log_audit, db, query, None, [], None, 0)
        raise HTTPException(status_code=403, detail=sec_res["reason"])
    
    safe_query = sec_res["sanitized_query"]
    
    async def event_stream():
        try:
            # 2. Embed query
            query_vec = await get_embedding(safe_query, settings)
            
            # 3. Hybrid search
            chunks = await hybrid_search(safe_query, query_vec, db, settings)
            
            # 4. Rerank
            top_chunks = await run_in_threadpool(rerank_chunks, safe_query, chunks, settings.RERANKER_TOP_K)
            
            # 5. Grounding
            grounding_results = []
            if not top_chunks or top_chunks[0].get("similarity", 0) < settings.SIMILARITY_THRESHOLD:
                grounding_results = await google_search(safe_query, settings)
            
            # 6. Stream Answer
            full_answer = ""
            async for token in generate_answer(safe_query, top_chunks, settings):
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                
            # 7. Optimized Sources Lookup (Resolves Doc Numbers to True Filenames) 
            sources = []
            if top_chunks:
                # Gather unique IDs to minimize database roundtrips
                doc_ids = list(set(c["doc_id"] for c in top_chunks if "doc_id" in c))
                page_ids = list(set(c["page_id"] for c in top_chunks if "page_id" in c))
                
                # Fetch filenames mapped to Document IDs
                doc_mapping = {}
                if doc_ids:
                    doc_stmt = select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
                    doc_result = await db.execute(doc_stmt)
                    for doc_id, filename in doc_result.all():
                        # Convert text references back to downloadable PDFs for your UI links
                        if filename.endswith('.txt'):
                            filename = filename.replace('.txt', '.pdf')
                        doc_mapping[doc_id] = filename

                # Fetch true readable page numbers mapped to Page rows
                page_mapping = {}
                if page_ids:
                    try:
                        # Checks your Page model for its row ID and structural page number column
                        page_stmt = select(Page.id, Page.page_num).where(Page.id.in_(page_ids))
                        page_result = await db.execute(page_stmt)
                        for p_id, p_num in page_result.all():
                            page_mapping[p_id] = p_num
                    except Exception:
                        # Fallback safeguard if your column layout uses different naming conventions
                        pass

                # Build the dynamic payload response matching your frontend layout
                for c in top_chunks:
                    d_id = c.get("doc_id")
                    p_id = c.get("page_id")
                    
                    sources.append({
                        "filename": doc_mapping.get(d_id, f"Document_{d_id}"),
                        "page_no": page_mapping.get(p_id, p_id)  # falls back to page_id if mapping isn't found
                    })

            yield f"data: {json.dumps({'type': 'sources', 'content': sources})}\n\n"
            
            # 8. Followups
            followups = await generate_followups(safe_query, full_answer, settings)
            yield f"data: {json.dumps({'type': 'followups', 'content': followups})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Background task
            bg_tasks.add_task(log_audit, db, safe_query, full_answer, sources, "gpt-4o-mini", 0.0)
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/chat/history")
async def chat_history(db: AsyncSession = Depends(get_db)):
    return {"history": []}