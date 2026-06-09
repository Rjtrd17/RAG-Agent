"""
Security guards — runs BEFORE any retrieval.
Order: keyword filter → PII detection → prompt injection detection → rate limit.
Blocked queries are logged but never processed.
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Restricted / Sensitive Keywords ──────────────────────────────────────────
# Extend this list via the Admin Panel or directly here.
RESTRICTED_KEYWORDS: list[str] = [
    "classified", "top secret", "confidential memo",
    "internal only", "officer personal", "aadhaar number",
    "private key", "sql injection", "drop table",
    "delete from", "insert into", "exec(", "eval(",
    "os.system", "__import__", "subprocess",
]

# ── Prompt Injection Patterns ─────────────────────────────────────────────────
INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"forget\s+(all\s+)?previous", re.I),
    re.compile(r"act\s+as\s+(?:a\s+)?(?:dan|jailbreak|evil|unrestricted)", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a\s+)?(?:dan|free)", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"bypass\s+(all\s+)?(?:safety|filter|restriction)", re.I),
    re.compile(r"do\s+anything\s+now", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"<\s*script", re.I),
    re.compile(r"system\s*:\s*you\s+are", re.I),
]

# ── PII Patterns (India-specific) ─────────────────────────────────────────────
PII_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),          # Aadhaar
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),              # PAN card
    re.compile(r"\b[6-9]\d{9}\b"),                       # Indian mobile
    re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}"),        # Email
    re.compile(r"\b\d{9,18}\b"),                         # Bank account
]


def check_restricted_keywords(query: str) -> Tuple[bool, str]:
    """Returns (is_blocked, reason)."""
    q_lower = query.lower()
    for kw in RESTRICTED_KEYWORDS:
        if kw.lower() in q_lower:
            return True, f"Query contains restricted keyword: '{kw}'"
    return False, ""


def check_prompt_injection(query: str) -> Tuple[bool, str]:
    """Returns (is_injection, reason)."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(query):
            return True, f"Prompt injection pattern detected: '{pattern.pattern}'"
    return False, ""


def check_pii(query: str) -> Tuple[bool, str]:
    """Returns (has_pii, masked_query_or_reason)."""
    for pattern in PII_PATTERNS:
        if pattern.search(query):
            masked = pattern.sub("[REDACTED]", query)
            return True, masked
    return False, query


def validate_query_length(query: str, max_chars: int = 1000) -> Tuple[bool, str]:
    """Returns (is_valid, reason)."""
    q = query.strip()
    if not q:
        return False, "Query cannot be empty."
    if len(q) > max_chars:
        return False, f"Query exceeds {max_chars} character limit."
    return True, ""


def run_security_guards(query: str) -> dict:
    """
    Run all security guards in order.
    Returns a result dict:
      {
        "allowed": bool,
        "reason": str,          # if blocked
        "sanitized_query": str  # if allowed (PII masked)
      }
    """
    # 1. Length check
    valid, reason = validate_query_length(query)
    if not valid:
        logger.warning(f"[SECURITY] Length check failed: {reason}")
        return {"allowed": False, "reason": reason, "sanitized_query": ""}

    # 2. Prompt injection
    is_injection, reason = check_prompt_injection(query)
    if is_injection:
        logger.warning(f"[SECURITY] Injection detected: {reason}")
        return {"allowed": False, "reason": "Prompt injection detected. Query blocked.", "sanitized_query": ""}

    # 3. Restricted keywords
    is_restricted, reason = check_restricted_keywords(query)
    if is_restricted:
        logger.warning(f"[SECURITY] Restricted keyword: {reason}")
        return {"allowed": False, "reason": "Your query contains restricted content and cannot be processed.", "sanitized_query": ""}

    # 4. PII masking (don't block, just sanitize)
    has_pii, sanitized = check_pii(query)
    if has_pii:
        logger.info(f"[SECURITY] PII detected and masked in query.")

    return {"allowed": True, "reason": "", "sanitized_query": sanitized if has_pii else query}


def add_restricted_keyword(keyword: str) -> None:
    """Dynamically add a keyword at runtime (Admin Panel use)."""
    if keyword.lower() not in [k.lower() for k in RESTRICTED_KEYWORDS]:
        RESTRICTED_KEYWORDS.append(keyword)
        logger.info(f"[SECURITY] Added restricted keyword: {keyword}")


def remove_restricted_keyword(keyword: str) -> None:
    """Dynamically remove a keyword at runtime (Admin Panel use)."""
    global RESTRICTED_KEYWORDS
    RESTRICTED_KEYWORDS = [k for k in RESTRICTED_KEYWORDS if k.lower() != keyword.lower()]
    logger.info(f"[SECURITY] Removed restricted keyword: {keyword}")


def get_restricted_keywords() -> list[str]:
    return list(RESTRICTED_KEYWORDS)
