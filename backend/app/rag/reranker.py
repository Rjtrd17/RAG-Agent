import logging
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_reranker_model = None

def load_reranker():
    global _reranker_model
    if _reranker_model is None:
        logger.info("Loading cross-encoder model...")
        _reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker_model

def rerank_chunks(query: str, chunks: list[dict], top_k: int = 8) -> list[dict]:
    """Re-rank chunks using a local cross-encoder."""
    if not chunks:
        return []
    
    model = load_reranker()
    
    # Create pairs of (query, chunk_text)
    pairs = [[query, chunk["chunk_text"]] for chunk in chunks]
    
    # Score pairs
    scores = model.predict(pairs)
    
    # Add scores back to chunks
    for i, chunk in enumerate(chunks):
        chunk["rerank_score"] = float(scores[i])
        
    # Sort descending by score
    sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    return sorted_chunks[:top_k]
