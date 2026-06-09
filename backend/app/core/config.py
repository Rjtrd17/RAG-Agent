"""
Core configuration — all settings loaded from .env via pydantic-settings.
Never import secrets directly; always use `get_settings()`.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
import urllib.parse

class Settings(BaseSettings):
    # To this (it checks the app directory, then falls back to the container root directory):
    model_config = SettingsConfigDict(env_file=[".env", "/app/.env", "../.env"], extra="ignore")

    # ── PostgreSQL ────────────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ragchatbot"
    POSTGRES_USER: str = "raguser"
    POSTGRES_PASSWORD: str = ""

    @property
    def DATABASE_URL(self) -> str:
        safe_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        safe_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── LLM Fallback ─────────────────────────────────────────
    LLM_PRIMARY: int = 1
    LLM_FALLBACK_ENABLED: bool = True
    LLM_FALLBACK_ORDER: str = "1,2,3"

    @property
    def fallback_order(self) -> List[int]:
        return [int(x.strip()) for x in self.LLM_FALLBACK_ORDER.split(",")]

    # ── API Keys ─────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── Embeddings ────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "openai"          # openai | ollama
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── Google Search Grounding ───────────────────────────────
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_ENGINE_ID: str = ""
    GOOGLE_SEARCH_ENABLED: bool = True

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = "813af81e3c0a7713e7172aefe8e593e861476ede77caca6dc7d7eaa4e8769bd5"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── RAG Tuning ────────────────────────────────────────────
    BM25_TOP_PAGES: int = 20
    SEMANTIC_TOP_CHUNKS: int = 20
    RERANKER_TOP_K: int = 8
    SIMILARITY_THRESHOLD: float = 0.35

    # ── Audit ────────────────────────────────────────────────
    AUDIT_LOG_ENABLED: bool = True

    # ── App ──────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
