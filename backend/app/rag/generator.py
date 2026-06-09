import logging
from typing import AsyncGenerator
from app.core.fallback import generate_with_fallback

logger = logging.getLogger(__name__)

def build_context(chunks: list[dict]) -> str:
    """Format chunks into a context string."""
    context_parts = []
    for i, chunk in enumerate(chunks[:8]): # max 8 chunks
        # In a real app we would join with document data to get filename/page
        context_parts.append(f"[{i+1}] (Source: Doc {chunk.get('doc_id')}, Page {chunk.get('page_id')})\n{chunk['chunk_text']}\n")
    return "\n".join(context_parts)

async def generate_answer(query: str, chunks: list[dict], settings) -> AsyncGenerator[str, None]:
    """Wrapper to call LLM with fallback."""
    context = build_context(chunks)
    logger.info("Starting generation with fallback chain...")
    
    async for token in generate_with_fallback(query, context, settings):
        yield token
