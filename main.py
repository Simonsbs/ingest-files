import os
import asyncio
import logging
import uvicorn

from fastapi import FastAPI
from app.watcher import watch_directory

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest-files")

# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SimonGPT File Ingestion",
    description="Watches a folder and ingests PDF/TXT files into the vector DB.",
    version="0.1.0"
)

@app.on_event("startup")
async def start_watcher():
    incoming_dir = os.getenv("WATCH_DIR", "/data/incoming")
    logger.info(f"📂 Watching directory: {incoming_dir}")
    asyncio.create_task(watch_directory(incoming_dir))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=False)
