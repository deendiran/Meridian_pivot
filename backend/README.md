# Meridian_pivot

# Northstar Inventory Sync -- Backend (Day 3)

Two services:

- **`warehouse_api.py`** -- mock stand-in for Northstar's real warehouse
  system. Returns a full stock snapshot, with counts that drift slightly
  each call so polling has something real to pick up.
- **`sync_service.py`** -- the actual deliverable. Polls the warehouse API
  every `POLL_INTERVAL_SECONDS` (default 300 = 5 min per spec), caches the
  result in memory, and exposes `/api/stock/<sku>` for the support tool
  frontend to query.

## Run it

```bash
pip install -r requirements.txt

# Terminal 1
uvicorn warehouse_api:app --port 9000 --reload

# Terminal 2 -- override the interval for local testing so you're not
# waiting 5 real minutes to see a poll happen
POLL_INTERVAL_SECONDS=10 uvicorn sync_service:app --port 8000 --reload
```

Then either:

- Open `frontend/index.html` and switch its `fetchStock()` to call
  `http://127.0.0.1:8000/api/stock/<sku>` instead of the mock data, or
- Hit the endpoints directly:

```bash
curl http://127.0.0.1:8000/api/stock/NS-40213
curl http://127.0.0.1:8000/api/stock
curl http://127.0.0.1:8000/api/sync-status
```

Try SKUs: `NS-40213`, `NS-51002` (out of stock), `NS-22190`, `NS-88410`,
`NS-70021`.

## Files that survive the Day 4 pivot unchanged

`cache.py` and the `/api/stock*` routes in `sync_service.py` are written to
not know or care whether the cache was last filled by a poll or a webhook.
Only the block marked `## POLLING (Day 3 spec)` in `sync_service.py` is
poll-specific -- that's the part Day 4 replaces.
