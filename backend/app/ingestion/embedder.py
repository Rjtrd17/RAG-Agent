"""
Embedding module — generates vector embeddings via OpenAI or Ollama.
Batches requests for throughput and respects provider-specific limits.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
import openai

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

# ── OpenAI batch size (max 2048, but 100 is a safe practical ceiling) ───
_OPENAI_BATCH_SIZE = 100


async def embed_texts(
    texts: list[str],
    settings: "Settings",
) -> list[list[float]]:
    """
    Generate embedding vectors for a list of texts.

    Dispatches to the provider configured in settings.EMBEDDING_PROVIDER:
      - 'openai'  → OpenAI text-embedding-3-small (1536 dims)
      - 'ollama'  → Local Ollama nomic-embed-text (768 dims)

    Args:
        texts: Raw text strings to embed.
        settings: Application settings (provides keys, URLs, model names).

    Returns:
        List of embedding vectors, one per input text.

    Raises:
        ValueError: If EMBEDDING_PROVIDER is not recognized.
    """
    if not texts:
        return []

    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        return await _embed_openai(texts, settings)
    elif provider == "ollama":
        return await _embed_ollama(texts, settings)
    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER: '{provider}'. "
            f"Expected 'openai' or 'ollama'."
        )


# ── OpenAI ──────────────────────────────────────────────────────


async def _embed_openai(
    texts: list[str],
    settings: "Settings",
) -> list[list[float]]:
    """Batch-embed texts using the OpenAI embeddings API."""
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), _OPENAI_BATCH_SIZE):
        batch = texts[start : start + _OPENAI_BATCH_SIZE]
        logger.info(
            "OpenAI embedding batch %d–%d of %d",
            start,
            start + len(batch) - 1,
            len(texts),
        )

        response = await client.embeddings.create(
            input=batch,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )

        # Results come sorted by index, but sort defensively
        batch_embeddings = [
            item.embedding
            for item in sorted(response.data, key=lambda d: d.index)
        ]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


# ── Ollama ──────────────────────────────────────────────────────


async def _embed_ollama(
    texts: list[str],
    settings: "Settings",
) -> list[list[float]]:
    """
    Embed texts one-by-one via the Ollama HTTP API.
    Ollama's /api/embeddings endpoint processes a single prompt per call.
    """
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    model = settings.OLLAMA_EMBEDDING_MODEL
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, text in enumerate(texts):
            if idx % 50 == 0:
                logger.info(
                    "Ollama embedding %d / %d",
                    idx,
                    len(texts),
                )

            resp = await client.post(
                f"{base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            all_embeddings.append(data["embedding"])

    return all_embeddings
