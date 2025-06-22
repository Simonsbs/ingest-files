# app/db.py

import asyncpg
from pgvector.asyncpg import register_vector
import logging
from typing import List

logger = logging.getLogger("ingest-db")


async def insert_chunks(dsn: str, records: List[dict]):
    """
    Insert a list of chunk records into the rag_chunks table.
    Each record must include: source_type, source_id, path, chunk, embedding.
    """
    conn = await asyncpg.connect(dsn)
    await register_vector(conn)

    try:
        await conn.executemany("""
            INSERT INTO rag_chunks (source_type, source_id, path, language, chunk, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, [
            (
                r["source_type"],
                r["source_id"],
                r["path"],
                r.get("language"),  # optional
                r["chunk"],
                r["embedding"],
                r.get("metadata", {})
            )
            for r in records
        ])
    except Exception as e:
        logger.exception(f"❌ DB insert failed: {e}")
        raise
    finally:
        await conn.close()
