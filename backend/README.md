# Meridian_pivot

# Northstar Inventory Sync -- Backend (Day 4/5)

The post-pivot workflow uses the service and its push simulator:

- **`sync_service.py`** -- the actual post-pivot deliverable. Receives signed
  stock-update webhooks, caches each update in memory, and exposes
  `/api/stock/<sku>` for the support tool frontend to query.
- **`simulate_warehouse_push.py`** -- signs and sends mock warehouse events
  to the webhook receiver.
- **`warehouse_api.py`** -- retained as a deprecated Day 3 polling reference;
  it is not part of the live post-pivot workflow.

## Run it

```bash
pip install -r requirements.txt

# Terminal 1 -- the actual deliverable
uvicorn sync_service:app --port 8000 --reload

# Terminal 2 -- simulate warehouse push events
python simulate_warehouse_push.py --loop --interval 4
```

Open the repository's `frontend/index.html`, or hit the endpoints directly:

```bash
curl http://127.0.0.1:8000/api/stock/NS-40213
curl http://127.0.0.1:8000/api/stock
curl http://127.0.0.1:8000/api/sync-status
```

Try SKUs after sending events: `NS-40213`, `NS-51002`, `NS-22190`,
`NS-88410`, and `NS-70021`.

## Files that survive the Day 4 pivot unchanged

`cache.py` and the `/api/stock*` routes in `sync_service.py` do not know or
care whether the cache was last filled by a poll or a webhook. The polling
loop and its scheduler were removed in the Day 4 pivot; updates now arrive
through `POST /webhooks/stock-update` and are authenticated with
`X-Signature-256`.
