import os
import asyncio
import logging

logger = logging.getLogger("file_watcher")

class FileWatcher:
    def __init__(self, directory: str, on_change=None, on_delete=None, interval: float = 10.0):
        self.directory = directory
        self.on_change = on_change
        self.on_delete = on_delete
        self.interval = interval
        self._last_mtimes = {}
        self._running = False

    async def start(self):
        self._running = True
        os.makedirs(self.directory, exist_ok=True)
        for fname in os.listdir(self.directory):
            fpath = os.path.join(self.directory, fname)
            if os.path.isfile(fpath):
                self._last_mtimes[fpath] = os.path.getmtime(fpath)
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
                if self.on_change:
                    await self.on_change(fpath)
        removed = set(self._last_mtimes.keys()) - seen
        for fpath in removed:
            del self._last_mtimes[fpath]
            logger.info(f"File dihapus: {fpath}")
            if self.on_delete:
                await self.on_delete(fpath)

    async def stop(self):
        self._running = False
