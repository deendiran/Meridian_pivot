"""
Warehouse Push Simulator -- Day 4/5.

Stands in for Northstar's warehouse system now that it pushes instead of
waiting to be polled. Signs each payload with the shared secret exactly the
way sync_service.py's receiver expects, and POSTs it.

Usage:
    # Send one event
    python simulate_warehouse_push.py --once

    # Keep sending random stock changes every few seconds, like a live feed
    python simulate_warehouse_push.py --loop --interval 4
"""

import argparse
import json
import random
import time

import httpx

from webhook_utils import sign_payload
from config import WEBHOOK_SECRET

SYNC_SERVICE_URL = "http://127.0.0.1:8000/webhooks/stock-update"

_CATALOG = {
    "NS-40213": "Cast Iron Skillet 10in",
    "NS-51002": "Insulated Travel Mug",
    "NS-22190": "Organic Cotton Tote",
    "NS-88410": "Bamboo Cutting Board",
    "NS-70021": "Ceramic Pour-Over Set",
}


def send_event(sku: str, count: int) -> None:
    payload = {"sku": sku, "name": _CATALOG[sku], "count": count}
    raw_body = json.dumps(payload).encode()
    signature = sign_payload(raw_body, WEBHOOK_SECRET)

    resp = httpx.post(
        SYNC_SERVICE_URL,
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-256": signature,
        },
        timeout=5.0,
    )
    print(f"-> {sku}={count}  [{resp.status_code}] {resp.json()}")


def random_event() -> tuple[str, int]:
    sku = random.choice(list(_CATALOG))
    count = random.randint(0, 150)
    return sku, count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Send a single random event and exit"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Keep sending events until stopped"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=4.0,
        help="Seconds between events in --loop mode",
    )
    parser.add_argument(
        "--sku", help="Send an event for a specific SKU instead of a random one"
    )
    parser.add_argument("--count", type=int, help="Stock count to send with --sku")
    args = parser.parse_args()

    if args.sku:
        if args.count is None:
            parser.error("--sku requires --count")
        send_event(args.sku, args.count)
        return

    if args.loop:
        print(
            f"Simulating warehouse push events every {args.interval}s. Ctrl+C to stop."
        )
        try:
            while True:
                sku, count = random_event()
                send_event(sku, count)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
        return

    # default: --once behavior even if flag omitted
    sku, count = random_event()
    send_event(sku, count)


if __name__ == "__main__":
    main()
