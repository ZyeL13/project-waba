# queue_worker.py
import asyncio
import time
import logging
from typing import Any, Callable, List, Dict

logger = logging.getLogger("queue_worker")

queue = asyncio.Queue(maxsize=1000)

BATCH_SIZE = 50
FLUSH_INTERVAL = 5   # detik

# Fungsi batch append yang akan diinjeksi dari main (atau di‑test)
SheetsClient: Callable[[List[Dict[str, Any]]], asyncio.Future] | None = None

def schedule_write(data: Dict[str, Any]):
    """Masukkan data ke antrian, drop jika penuh."""
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        logger.warning("Queue penuh, data diabaikan: %s", data)

async def sheets_worker():
    batch = []
    last_flush = time.monotonic()
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=FLUSH_INTERVAL)
            batch.append(item)
        except asyncio.TimeoutError:
            pass

        now = time.monotonic()
        if batch and (len(batch) >= BATCH_SIZE or (now - last_flush) >= FLUSH_INTERVAL):
            if call_batch_append:
                try:
                    await call_batch_append(batch)
                except Exception as e:
                    logger.exception("Gagal mengirim batch ke Sheets: %s", e)
            batch = []
            last_flush = now
