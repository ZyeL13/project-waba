# rate_limiter.py
import asyncio
import time
from typing import Dict, List

class SlidingWindowLimiter:
    def __init__(self):
        self._windows: Dict[str, List[float]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def allow(self, user_id: str, max_requests: int = 5, window: float = 1.0) -> bool:
        # Buat lock khusus user jika belum ada
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()

        async with self._locks[user_id]:
            now = time.monotonic()
            timestamps = self._windows.get(user_id, [])

            # Buang timestamp di luar jendela waktu
            timestamps = [t for t in timestamps if now - t < window]

            if len(timestamps) >= max_requests:
                self._windows[user_id] = timestamps  # tetap simpan list yang sudah dibersihkan
                return False

            timestamps.append(now)
            self._windows[user_id] = timestamps
            return True

    async def cleanup_stale(self, max_idle_seconds: float = 300):
        """Bersihkan user yang tidak aktif lebih dari max_idle_seconds"""
        now = time.monotonic()
        stale = []
        for uid, lock in self._locks.items():
            async with lock:
                timestamps = self._windows.get(uid, [])
                if timestamps and now - timestamps[-1] > max_idle_seconds:
                    stale.append(uid)
        for uid in stale:
            del self._locks[uid]
            if uid in self._windows:
                del self._windows[uid]
