"""
In-memory stock cache.

Kept deliberately simple (a dict + a timestamp) since the spec doesn't call
for persistence -- this is the thing Day 3's poller writes to and the query
endpoint reads from. Isolating it in its own module means Day 4's webhook
handler can write to the exact same cache without touching the query
endpoint at all, which is the whole point of the pivot going cleanly.
"""

from datetime import datetime, timezone
from typing import Optional


class StockCache:
    def __init__(self):
        self._data: dict[str, dict] = {}
        self._last_updated: Optional[datetime] = None

    def replace_all(self, items: list[dict]) -> None:
        """Full-refresh write, used by the Day 3 poller (warehouse API returns
        the whole snapshot each time, not a diff)."""
        self._data = {item["sku"]: item for item in items}
        self._last_updated = datetime.now(timezone.utc)

    def upsert(self, item: dict) -> None:
        """Single-item write, used by the Day 4 webhook handler once we're
        reacting to individual push events instead of full snapshots."""
        self._data[item["sku"]] = item
        self._last_updated = datetime.now(timezone.utc)

    def get(self, sku: str) -> Optional[dict]:
        return self._data.get(sku.upper())

    def get_all(self) -> list[dict]:
        return list(self._data.values())

    def search(self, query: str) -> list[dict]:
        """Case-insensitive substring match against product name OR sku,
        so 'skillet' finds NS-SKILLET-10IN and 'ns-tote' also works."""
        q = query.strip().lower()
        if not q:
            return []
        return [
            item
            for item in self._data.values()
            if q in item["name"].lower() or q in item["sku"].lower()
        ]

    @property
    def last_updated(self) -> Optional[datetime]:
        return self._last_updated


# Single shared instance imported by both the poller and the API routes.
cache = StockCache()
