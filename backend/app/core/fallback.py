"""
LLM Fallback Chain
Order: 1=OpenAI GPT-4o-mini, 2=Gemini 1.5 Flash, 3=Ollama llama3
Controlled entirely by .env LLM_FALLBACK_ORDER and LLM_FALLBACK_ENABLED.
"""
import logging
from typing import AsyncGenerator, Optional
import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert government scheme assistant. Answer the user's question "
    "using the provided context.\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. Your complete answer MUST be well-structured and between 1200 to 3000 words total.\n"
    "2. Break down the details clearly using Markdown bold headers: "
    "**Objective**, **History and Background**, "
    "**Comparison with other policies with graphical timeline**, "
    "and **Bureaucrats involved in this policy making**.\n"
    "3. When bureaucrats or related policies are mentioned, format them as "
    "clickable markdown links.\n"
    "4. Be concise and factual. Remove conversational filler words.\n"
    "5. Always provide information — never say 'I have no information' or 'no data available'. "
    "Use Google-grounded knowledge if context is thin.\n\n"
    "Context:\n{context}"
)


async def call_openai(prompt: str, context: str, api_key: str, model: str = "gpt-4o-mini") -> AsyncGenerator[str, None]:
    """Stream response from OpenAI GPT-4o-mini."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    system = SYSTEM_PROMPT.format(context=context)
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.3,
            max_tokens=2500,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        logger.error(f"[OpenAI] Error: {e}")
        raise


async def call_gemini(prompt: str, context: str, api_key: str) -> AsyncGenerator[str, None]:
    """Stream response from Google Gemini 1.5 Flash."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    system = SYSTEM_PROMPT.format(context=context)
    full_prompt = f"{system}\n\nUser Question: {prompt}"
    try:
        response = model.generate_content(full_prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"[Gemini] Error: {e}")
        raise


async def call_ollama(prompt: str, context: str, base_url: str, model: str = "llama3") -> AsyncGenerator[str, None]:
    """Stream response from local Ollama."""
    import json
    system = SYSTEM_PROMPT.format(context=context)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{base_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
    except Exception as e:
        logger.error(f"[Ollama] Error: {e}")
        raise


async def generate_with_fallback(
    prompt: str,
    context: str,
    settings,
) -> AsyncGenerator[str, None]:
    """
    Attempt LLMs in fallback_order. Yields streamed tokens.
    Falls back to next LLM on any error.
    """
    order = settings.fallback_order if settings.LLM_FALLBACK_ENABLED else [settings.LLM_PRIMARY]

    for llm_id in order:
        try:
            logger.info(f"[Fallback] Trying LLM id={llm_id}")
            if llm_id == 1:
                async for token in call_openai(prompt, context, settings.OPENAI_API_KEY):
                    yield token
                return
            elif llm_id == 2:
                async for token in call_gemini(prompt, context, settings.GEMINI_API_KEY):
                    yield token
                return
            elif llm_id == 3:
                async for token in call_ollama(prompt, context, settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL):
                    yield token
                return
        except Exception as e:
            logger.warning(f"[Fallback] LLM id={llm_id} failed: {e}. Trying next.")
            continue

    # All LLMs failed — yield a grounded fallback message
    logger.error("[Fallback] All LLMs failed.")
    yield (
        "⚠️ I was unable to reach the AI service at this moment. "
        "Please try again in a few seconds. Your query has been logged."
    )
