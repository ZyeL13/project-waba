import os
import logging
import db

logger = logging.getLogger("indexer")

async def index_file(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Gagal membaca {filepath}: {e}")
        return

    await db.execute_write("DELETE FROM file_index WHERE filepath = ?", (filepath,))
    await db.execute_write(
        "INSERT INTO file_index (filepath, content) VALUES (?, ?)",
        (filepath, content)
    )
    logger.info(f"Indexed {filepath} ({len(content)} chars)")

async def remove_index(filepath: str):
    await db.execute_write("DELETE FROM file_index WHERE filepath = ?", (filepath,))
    logger.info(f"Removed from index: {filepath}")
