# app/processor.py

import json
import logging
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from fastapi import HTTPException

from app.config import settings
from app.chunker import chunk_text
from app.db import insert_chunks

logger = logging.getLogger("ingest-processor")

# Build URLs from settings
ROUTER_URL = settings.router_url.rstrip("/")
LLM_TOKEN_URL = ROUTER_URL.replace("/v1/embeddings", "/v1/token")
LLM_API_KEY = settings.llm_router_api_key.get_secret_value()


async def process_file(path: Path) -> None:
    """
    Load, chunk, embed, and persist a single file.
    """
    ext = path.suffix.lower()
    content = load_text_file(path) if ext == ".txt" else load_pdf_file(path)

    if not content.strip():
        logger.warning(f"⚠️ Empty file: {path.name}")
        return

    chunks = chunk_text(content)

    # Step 0: fetch JWT token
    token = await fetch_token(LLM_TOKEN_URL, LLM_API_KEY)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Call LLM Router to embed chunks
    vectors = await fetch_embeddings(chunks, ROUTER_URL, headers)

    # Step 2: Prepare and save to vector DB
    records = [
        {
            "source_type": "pdf" if ext == ".pdf" else "text",
            "source_id": path.name,
            "path": str(path),
            "language": None,
            "chunk": chunks[i],
            "embedding": vec["embedding"],
            "metadata": {"index": i},
        }
        for i, vec in enumerate(vectors)
    ]

    await insert_chunks(records)
    logger.info(f"✅ Ingested {len(records)} chunks from: {path.name}")


async def fetch_token(token_url: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=settings.token_timeout) as client:
        resp = await client.post(token_url, json={"api_key": api_key})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(f"❌ Token fetch failed: {e}")
            raise HTTPException(502, f"Token fetch error: {e}") from e

        data = resp.json()
        token = data.get("access_token")
        if not token:
            logger.error(f"No access_token in token response: {data}")
            raise HTTPException(502, "Token response missing access_token")
        return token


async def fetch_embeddings(chunks: list[str], embed_url: str, headers: dict) -> list[dict]:
    async with httpx.AsyncClient(timeout=settings.embed_timeout) as client:
        payload = {"input": chunks}
        logger.info(f"🔗 Requesting embeddings for {len(chunks)} chunks…")
        resp = await client.post(embed_url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(f"❌ Embedding request failed: {e}")
            raise HTTPException(502, f"Embedding request failed: {e}") from e

        body = resp.json()
        data = body.get("data")
        if data is None:
            logger.error(f"No 'data' in embedding response: {body}")
            raise HTTPException(500, "Embedding response missing 'data'")
        return data


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_pdf_file(path: Path) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)
