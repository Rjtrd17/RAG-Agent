"""
Async SQLAlchemy session factory using asyncpg.
Also provides a sync engine for Alembic migrations and CLI scripts.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# ── Async engine (FastAPI runtime) ──────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session, auto-closes on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Sync engine (Alembic migrations & CLI scripts) ─────────────
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=(settings.APP_ENV == "development"),
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)
