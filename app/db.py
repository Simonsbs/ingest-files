# app/db.py

import logging
from typing import List, Dict

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import settings

logger = logging.getLogger("ingest-db")

_pool: asyncpg.Pool | None = None


async def init_db_pool() -> asyncpg.Pool:
    """
    Initialize (once) and return a global asyncpg connection pool,
    registering the pgvector extension on each new connection.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.vector_db_url,
            init=lambda conn: register_vector(conn),
            min_size=1,
            max_size=10,
            timeout=60.0,
        )
    return _pool


async def close_db_pool() -> None:
    """
    Gracefully close the global connection pool on shutdown.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_chunks(records: List[Dict]) -> None:
    """
    Insert a batch of chunk records into rag_chunks using a pooled connection.
    Each record must include:
        source_type: str
        source_id:   str
        path:        str
        language:    Optional[str]
        chunk:       str
        embedding:   List[float] or vector type
        metadata:    JSON-serializable dict
    """
    pool = await init_db_pool()

    # prepare tuples for bulk insert
    values = [
        (
            r["source_type"],
            r["source_id"],
            r["path"],
            r.get("language"),
            r["chunk"],
            r["embedding"],
            r.get("metadata", {}),
        )
        for r in records
    ]

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    """
                    INSERT INTO rag_chunks
                      (source_type, source_id, path, language, chunk, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    values,
                )
    except Exception:
        logger.exception("❌ DB insert failed")
        raise
