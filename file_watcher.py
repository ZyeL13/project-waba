# file_watcher.py
import os
import asyncio
import logging

logger = logging.getLogger("file_watcher")

class FileWatcher:
    def __init__(self, directory: str, callback, interval: float = 10.0):
        self.directory = directory
        self.callback = callback          # async function(filepath)
        self.interval = interval
        self._last_mtimes = {}            # filepath -> mtime
        self._running = False

    async def start(self):
        self._running = True
        os.makedirs(self.directory, exist_ok=True)
        # inisialisasi mtimes dari file yang sudah ada
        for fname in os.listdir(self.directory):
            fpath = os.path.join(self.directory, fname)
            if os.path.isfile(fpath):
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
                logger.debug(f"Registered {fpath}")
        while self._running:
            try:
                await self._scan()
            except Exception as e:
                logger.exception(f"Error scanning: {e}")
            await asyncio.sleep(self.interval)

    async def _scan(self):
        seen = set()
        for fname in os.listdir(self.directory):
            fpath = os.path.join(self.directory, fname)
            if not os.path.isfile(fpath):
                continue
            seen.add(fpath)
            mtime = os.path.getmtime(fpath)
            last = self._last_mtimes.get(fpath)
            if last is None or mtime > last:
                logger.info(f"Perubahan terdeteksi: {fpath}")
                self._last_mtimes[fpath] = mtime
                if self.callback:
                    await self.callback(fpath)
        # hapus file yang sudah tidak ada
        removed = set(self._last_mtimes.keys()) - seen
        for fpath in removed:
            del self._last_mtimes[fpath]
            logger.info(f"File dihapus: {fpath}")
            # callback mungkin untuk menghapus dari index (opsional)

    async def stop(self):
        self._running = False
