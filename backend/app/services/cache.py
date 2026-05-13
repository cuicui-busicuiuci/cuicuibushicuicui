import threading
import time
from typing import Any


class MemoryCache:
    def __init__(self, cleanup_interval: int = 60):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._start_cleanup_thread()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int):
        expires_at = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expires_at)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def _cleanup_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]

    def _start_cleanup_thread(self):
        def _cleanup_loop():
            while True:
                time.sleep(self._cleanup_interval)
                self._cleanup_expired()

        thread = threading.Thread(target=_cleanup_loop, daemon=True)
        thread.start()


cache = MemoryCache()
