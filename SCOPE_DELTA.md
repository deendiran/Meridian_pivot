# Scope Delta Analysis -- Day 4 Pivot

**Trigger:** Client (Northstar) killed the polling method with no extension,
48-hour deadline to switch to a webhook push model. No negotiation back to
the original spec.

## Dropped

- `sync_service.py`: the `poll_warehouse()` function, the `AsyncIOScheduler`
  job, and the `lifespan` startup/shutdown hooks that ran it.
- The 5-minute interval as a concept entirely -- there is no scheduled
  anything in the post-pivot service. Updates arrive whenever the warehouse
  sends them.
- The sync service's dependency on `apscheduler`. It's still in
  `requirements.txt` for now (Day 3's `warehouse_api.py` mock still exists
  for reference) but is no longer imported by the live code path.

## Modified

- `sync_service.py`'s `/api/sync-status` response: `mode` now reports
  `"webhook"` instead of `"polling"`, and dropped the `interval_seconds`
  field (meaningless once there's no interval).
- `warehouse_api.py`'s `/warehouse/stock` route: left in place but marked
  deprecated in a code comment -- nothing calls it anymore.
- `frontend/script.js`: `fetchStock()` switched from reading mock data to
  calling the real `/api/stock/<sku>` endpoint. The sync indicator now polls
  `/api/sync-status` every 5s and reflects whatever `mode` the backend
  actually reports, instead of a hardcoded "Polling" label.

## Added

- `webhook_utils.py`: HMAC-SHA256 sign/verify functions.
- `sync_service.py`: `POST /webhooks/stock-update` receiver -- verifies the
  `X-Signature-256` header against the raw request body before touching the
  cache, rejects with 401 on mismatch, upserts a single SKU on success.
- `simulate_warehouse_push.py`: stands in for the warehouse's real push
  integration, since we don't have access to it. Signs and sends events the
  same way a real integration would.
- `config.py`: `WEBHOOK_SECRET`.

## Regression check

- `cache.py` was **not touched**. Both the old poller and the new webhook
  handler write through the same `StockCache` interface (`replace_all` vs.
  `upsert`), so the cache's behavior for readers is identical.
- `/api/stock/<sku>` and `/api/stock` routes in `sync_service.py` are
  **unchanged, line for line**, from the Day 3 version. Verified by running
  the same `curl` calls from the Day 3 README against the Day 4 service and
  confirming identical response shapes.
- The frontend's result-card rendering, recent-lookups list, and error
  states required no changes -- only the data-fetching layer underneath
  them changed.

## What this cost

- Lost: near-real-time-but-not-instant averaging (polling always returns
  data at most 5 minutes stale; webhook is push-instant but only as
  reliable as the sender's delivery -- if Northstar's webhook fails to
  fire, there's no fallback poll to catch it eventually). This is a real
  trade-off worth flagging back to the client, not just a code change.
- Gained: signature verification, which the polling model never needed
  (we were the ones initiating every request, so there was nothing to
  authenticate). This is net-new complexity the pivot introduced, not
  something we could reuse from Day 3.
