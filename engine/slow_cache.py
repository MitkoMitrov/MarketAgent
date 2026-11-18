"""
Small JSON cache for Finnhub data that changes slowly (insider trades, analyst ratings,
filings, calendars...). The news site rebuilds every 30 minutes; with this cache each of
those endpoints is called at most once per TTL. A failed fetch is never cached: the last
good value (if any) is returned and the next run tries again.
"""
import json
import time
from pathlib import Path


class SlowCache:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.data = {}
        self.changed = False
        if self.path:
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    def get(self, key: str, ttl_s: float, fetch):
        """Return the cached value for key if younger than ttl_s, else fetch() and store it."""
        entry = self.data.get(key)
        if entry and time.time() - entry.get("t", 0) < ttl_s:
            return entry["v"]
        try:
            value = fetch()
        except Exception as e:
            print(f"⚠️ {key}: {e}")
            return entry["v"] if entry else None
        self.data[key] = {"t": time.time(), "v": value}
        self.changed = True
        return value

    def save(self) -> None:
        if self.path and self.changed:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, separators=(",", ":")), encoding="utf-8")
            self.changed = False
