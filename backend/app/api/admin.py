from fastapi import APIRouter
from app.core.config import get_settings
from app.core.security import get_restricted_keywords, add_restricted_keyword, remove_restricted_keyword

router = APIRouter()

@router.get("/config")
def get_config():
    settings = get_settings()
    return {
        "LLM_FALLBACK_ENABLED": settings.LLM_FALLBACK_ENABLED,
        "LLM_FALLBACK_ORDER": settings.LLM_FALLBACK_ORDER,
        "LLM_PRIMARY": settings.LLM_PRIMARY
    }

@router.post("/config")
def update_config(config: dict):
    # In a real app we'd update DB or .env, for now just update memory settings if possible
    # settings = get_settings()
    return {"status": "updated"}

@router.get("/keywords")
def list_keywords():
    return {"keywords": get_restricted_keywords()}

@router.post("/keywords")
def add_keyword(data: dict):
    if "keyword" in data:
        add_restricted_keyword(data["keyword"])
    return {"status": "added"}

@router.delete("/keywords/{keyword}")
def delete_keyword(keyword: str):
    remove_restricted_keyword(keyword)
    return {"status": "removed"}
