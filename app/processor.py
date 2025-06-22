# app/processor.py

import os
import json
import fitz  # PyMuPDF
import httpx
import logging
from pathlib import Path
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector
from app.chunker import chunk_text
from app.db import insert_chunks
from fastapi import HTTPException

load_dotenv()
logger = logging.getLogger("ingest-processor")

VECTOR_DB_URL = os.getenv("VECTOR_DB_URL")
ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8080/v1/embeddings")
LLM_API_KEY = os.getenv("LLM_ROUTER_API_KEY")

if not LLM_API_KEY:
    logger.error("LLM_ROUTER_API_KEY not set in .env")
    raise RuntimeError("Missing LLM_ROUTER_API_KEY in environment")

# Build token URL from embeddings URL
LLM_TOKEN_URL = ROUTER_URL.rstrip("/").replace("/v1/embeddings", "/v1/token")


async def process_file(path: Path):
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
    async with httpx.AsyncClient(timeout=10.0) as auth_client:
        resp = await auth_client.post(
            LLM_TOKEN_URL,
            json={"api_key": LLM_API_KEY}
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(f"❌ Token fetch failed: {e}")
            raise HTTPException(502, f"Token fetch error: {e}") from e

        token = resp.json().get("access_token")
        if not token:
            msg = f"No access_token in token response: {resp.text}"
            logger.error(msg)
            raise HTTPException(502, msg)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Call LLM Router to embed chunks
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {"input": chunks}
        logger.info(f"🔗 Requesting embeddings for {len(chunks)} chunks via router…")
        response = await client.post(ROUTER_URL, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(f"❌ Embedding request failed: {e}")
            raise

        data = response.json().get("data")
        if data is None:
            msg = f"No 'data' in embedding response: {response.text}"
            logger.error(msg)
            raise HTTPException(500, msg)

        vectors = data

    # Step 2: Save to vector DB, JSON-encoding metadata
    records = []
    for i, vec in enumerate(vectors):
        records.append({
            "source_type": "pdf" if ext == ".pdf" else "text",
            "source_id": path.name,
            "path": str(path),
            "chunk": chunks[i],
            "embedding": vec["embedding"],
            # serialize metadata dict to JSON string
            "metadata": json.dumps({"index": i})
        })

    await insert_chunks(VECTOR_DB_URL, records)
    logger.info(f"✅ Ingested {len(records)} chunks from: {path.name}")


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_pdf_file(path: Path) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)
