import logging
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)

async def generate_followups(query: str, answer: str, settings) -> list[str]:
    """Generate 3 follow-up questions."""
    defaults = [
        "What are the eligibility criteria for this scheme?",
        "What amendments have been made to this policy?",
        "How does this compare to similar government schemes?"
    ]
    
    if not settings.OPENAI_API_KEY:
        return defaults
        
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = f"Given this Q&A, generate 3 relevant follow-up questions. Return ONLY a JSON array of strings.\nQ: {query}\nA: {answer}"
        
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = resp.choices[0].message.content
        data = json.loads(content)
        # assuming response looks like {"questions": ["q1", "q2", "q3"]} or similar
        for k, v in data.items():
            if isinstance(v, list):
                return v[:3]
        return defaults
    except Exception as e:
        logger.error(f"Followup generation error: {e}")
        return defaults
