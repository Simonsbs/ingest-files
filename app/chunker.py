# app/chunker.py

import tiktoken

# Target chunk size
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Use tokenizer compatible with OpenAI/BGE-M3
enc = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str) -> list[str]:
    """
    Splits the input text into ~500-token chunks with slight overlap.
    Returns a list of chunk strings.
    """
    tokens = enc.encode(text)
    total = len(tokens)

    chunks = []
    start = 0

    while start < total:
        end = min(start + CHUNK_SIZE, total)
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks
