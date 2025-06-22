# app/watcher.py

import asyncio
import logging
from pathlib import Path

from watchfiles import awatch

from app.config import settings
from app.processor import process_file

logger = logging.getLogger("ingest-watcher")

# Optional: limit concurrent file‐processing tasks
# you can add `max_concurrent_tasks: int = Field(default=5, env="MAX_CONCURRENT_TASKS")`
# to your Settings if you want to make this configurable.
MAX_CONCURRENT = getattr(settings, "max_concurrent_tasks", 5)
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def watch_directory(folder: str | None = None) -> None:
    """
    Watch a directory (defaults to settings.watch_dir) for new .pdf or .txt files,
    debounce rapid duplicate events, and schedule processing with concurrency control.
    """
    watch_dir = Path(folder or settings.watch_dir)
    if not watch_dir.is_dir():
        logger.error(f"Watch directory not found: {watch_dir}")
        raise RuntimeError(f"Invalid watch directory: {watch_dir}")

    logger.info(f"📂 Watching directory: {watch_dir}")
    async for changes in awatch(str(watch_dir)):
        for change_type, filepath in changes:
            path = Path(filepath)
            if path.suffix.lower() not in (".pdf", ".txt"):
                continue

            # debounce editor/temp-file noise
            await asyncio.sleep(0.5)

            # schedule processing under semaphore
            await _semaphore.acquire()
            asyncio.create_task(_process(path))


async def _process(path: Path) -> None:
    try:
        logger.info(f"📥 New file detected: {path.name}")
        await process_file(path)
    except Exception as e:
        logger.exception(f"❌ Failed to process {path.name}: {e}")
    finally:
        _semaphore.release()
