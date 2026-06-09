"""
Text chunking module — splits extracted text into overlapping token-counted chunks.
Uses LangChain's RecursiveCharacterTextSplitter for intelligent boundary detection
and tiktoken for accurate OpenAI-compatible token counting.
"""
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Shared tiktoken encoder — cl100k_base is used by text-embedding-3-small & GPT-4o
_encoding = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Return the number of cl100k_base tokens in *text*."""
    return len(_encoding.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """
    Split a single block of text into overlapping chunks.

    Args:
        text: The full text to split.
        chunk_size: Target maximum token count per chunk.
        overlap: Token overlap between consecutive chunks.

    Returns:
        List of dicts: [{chunk_index, chunk_text, token_count}, ...]
        chunk_index is 0-based.
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=_count_tokens,
        separators=["\n\n", "\n", ". ", " ", ""],
        strip_whitespace=True,
    )

    splits = splitter.split_text(text)

    chunks: list[dict] = []
    for idx, chunk_text_piece in enumerate(splits):
        chunks.append(
            {
                "chunk_index": idx,
                "chunk_text": chunk_text_piece,
                "token_count": _count_tokens(chunk_text_piece),
            }
        )
    return chunks


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """
    Chunk every page returned by the OCR module.

    Args:
        pages: Output from ocr.extract_text_from_pdf / extract_text_from_txt,
               each dict has {page_no, text}.
        chunk_size: Target maximum token count per chunk.
        overlap: Token overlap between consecutive chunks.

    Returns:
        Flat list of dicts:
        [{page_no, chunk_index, chunk_text, token_count}, ...]
        chunk_index is 0-based **within each page**.
    """
    all_chunks: list[dict] = []

    for page in pages:
        page_no = page["page_no"]
        text = page.get("text", "")

        page_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for chunk in page_chunks:
            all_chunks.append(
                {
                    "page_no": page_no,
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": chunk["chunk_text"],
                    "token_count": chunk["token_count"],
                }
            )

    return all_chunks
