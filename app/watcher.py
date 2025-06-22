# app/watcher.py

import os
import time
import asyncio
import logging
from pathlib import Path
from watchfiles import awatch

from app.processor import process_file

logger = logging.getLogger("ingest-watcher")


async def watch_directory(folder: str):
    """
    Watch a directory for new .pdf or .txt files and trigger ingestion.
    """
    async for changes in awatch(folder):
        for change_type, filepath in changes:
            path = Path(filepath)
            if path.suffix.lower() not in [".pdf", ".txt"]:
                continue

            # Debounce rapid duplicate triggers (e.g. from editors)
            await asyncio.sleep(0.5)

            try:
                logger.info(f"📥 New file detected: {path.name}")
                await process_file(path)
            except Exception as e:
                logger.exception(f"❌ Failed to process {path.name}: {e}")
