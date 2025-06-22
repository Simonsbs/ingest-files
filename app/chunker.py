# app/chunker.py

from tiktoken import get_encoding
from app.config import settings

# tokenizer for OpenAI / BGE-M3
enc = get_encoding("cl100k_base")


def chunk_text(text: str) -> list[str]:
    """
    Splits the input text into ~settings.chunk_size-token chunks,
    with settings.chunk_overlap-token overlap between chunks.
    """
    tokens = enc.encode(text)
    total = len(tokens)

    chunks: list[str] = []
    start = 0

    while start < total:
        end = min(start + settings.chunk_size, total)
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        start += settings.chunk_size - settings.chunk_overlap

    return chunks
