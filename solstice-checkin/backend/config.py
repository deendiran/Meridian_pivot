"""
Central configuration for the Solstice check-in service.

The check-in service has no polling loop after the pivot. Webhook and broker
settings are shared by the kiosk service and the mock printer vendor.
"""

import os

# URL the mock vendor calls after a print job completes.
CHECKIN_WEBHOOK_URL = os.getenv(
    "CHECKIN_WEBHOOK_URL", "http://127.0.0.1:8100/webhooks/print-complete"
)

# Shared secret used to sign and verify printer webhook payloads. In a real
# integration this is issued when the webhook is registered, never hardcoded.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-shared-secret-change-me")
