def build_timeline_markdown(chunks: list[dict]) -> str:
    """Extract policy_date from chunks and build timeline."""
    dates = []
    # simplified for now, normally we'd parse metadata_
    return ""

def attach_amendments_section(answer: str, chunks: list[dict]) -> str:
    """Append amendments to answer."""
    # simplified for now
    return answer

def format_response(raw_answer: str, chunks: list[dict], grounding_results: list[dict] = None) -> dict:
    """Format the final response dict."""
    sources = []
    for c in chunks:
        sources.append({
            "doc_id": c.get("doc_id"),
            "page_id": c.get("page_id")
        })
    
    res = {
        "answer": raw_answer,
        "sources": sources
    }
    if grounding_results:
        res["grounding_sources"] = grounding_results
    return res
