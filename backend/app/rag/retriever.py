import logging
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def bm25_page_search(query: str, db_session: AsyncSession, top_k: int = 20) -> list[dict]:
    """Perform full-text search on page content."""
    sql = text("""
        SELECT id, doc_id, page_no, raw_text, ts_rank(search_vector, plainto_tsquery('english', :query)) as rank
        FROM pages
        WHERE search_vector @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :top_k
    """)
    result = await db_session.execute(sql, {"query": query, "top_k": top_k})
    return [
        {
            "page_id": str(row.id),
            "doc_id": str(row.doc_id),
            "page_no": row.page_no,
            "raw_text": row.raw_text,
            "score": row.rank
        }
        for row in result.all()
    ]

async def semantic_chunk_search(query_embedding: list[float], db_session: AsyncSession, page_ids: list[str] = None, top_k: int = 20) -> list[dict]:
    """Perform semantic search on chunk embeddings."""
    
    # CRITICAL: Convert the float list into a PostgreSQL vector string format
    vector_str = str(query_embedding)

    if page_ids:
        sql = text("""
            SELECT id, chunk_text, doc_id, page_id, 1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
            FROM chunks
            WHERE page_id::text = ANY(:page_ids)
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
        """)
        params = {"query_vec": vector_str, "page_ids": page_ids, "top_k": top_k}
    else:
        sql = text("""
            SELECT id, chunk_text, doc_id, page_id, 1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
            FROM chunks
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
        """)
        params = {"query_vec": vector_str, "top_k": top_k}

    result = await db_session.execute(sql, params)
    return [
        {
            "chunk_id": str(row.id),
            "chunk_text": row.chunk_text,
            "doc_id": str(row.doc_id),
            "page_id": str(row.page_id),
            "similarity": row.similarity
        }
        for row in result.all()
    ]


async def hybrid_search(query: str, query_embedding: list[float], db_session: AsyncSession, settings) -> list[dict]:
    """Perform BM25 search then filter chunks based on resulting pages."""
    logger.info(f"Running BM25 search for '{query}'...")
    pages = await bm25_page_search(query, db_session, top_k=settings.BM25_TOP_PAGES)
    page_ids = [p["page_id"] for p in pages] if pages else None

    logger.info(f"Running semantic search. Restricting to {len(page_ids) if page_ids else 0} pages.")
    chunks = await semantic_chunk_search(
        query_embedding, 
        db_session, 
        page_ids=page_ids, 
        top_k=settings.SEMANTIC_TOP_CHUNKS
    )
    return chunks
