import logging

logger = logging.getLogger(__name__)

async def google_search(query: str, settings, num_results: int = 3) -> list[dict]:
    """Perform Google Custom Search for grounding."""
    if not settings.GOOGLE_SEARCH_ENABLED or not settings.GOOGLE_SEARCH_API_KEY:
        return []
        
    try:
        from googleapiclient.discovery import build
        service = build("customsearch", "v1", developerKey=settings.GOOGLE_SEARCH_API_KEY)
        res = service.cse().list(
            q=query, 
            cx=settings.GOOGLE_SEARCH_ENGINE_ID,
            num=num_results
        ).execute()
        
        items = res.get("items", [])
        return [
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", "")
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Google Search error: {e}")
        return []

def format_grounding_context(results: list[dict]) -> str:
    if not results:
        return ""
    
    parts = ["--- WEB SEARCH RESULTS ---"]
    for i, res in enumerate(results):
        parts.append(f"[{i+1}] {res['title']}\n{res['snippet']}\n{res['link']}")
    return "\n\n".join(parts)
