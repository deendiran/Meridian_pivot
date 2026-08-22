"""
Central config for the sync service.

POLL_INTERVAL_SECONDS defaults to the spec'd 5 minutes, but can be overridden
via env var so you're not sitting around for 5 minutes every time you want to
see a poll happen during development:

    POLL_INTERVAL_SECONDS=10 uvicorn sync_service:app --reload
"""

import os

WAREHOUSE_BASE_URL = os.getenv("WAREHOUSE_BASE_URL", "http://127.0.0.1:9000")
POLL_INTERVAL_SECONDS = int(
    os.getenv("POLL_INTERVAL_SECONDS", 300)
)  # 5 min per spec -- DEPRECATED as of Day 4, see SCOPE_DELTA.md

# Day 4: shared secret used to sign/verify webhook payloads. In a real
# integration this is issued by Northstar when you register the webhook
# endpoint with them -- never hardcode it, and never log it.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-shared-secret-change-me")
