"""
Badge Printer Vendor (mock) -- post-pivot, async via RabbitMQ.

The vendor deprecated the synchronous /print-sync endpoint (kept below only
for reference / Scope Delta comparison -- nothing calls it anymore). Print
requests now arrive via a shared RabbitMQ queue rather than a direct HTTP
call from the kiosk -- this service consumes independently and calls back
to the kiosk's webhook once each job actually finishes.

    Start RabbitMQ first (once): sudo service rabbitmq-server start
    uvicorn printer_vendor:app --port 9100 --reload
"""

import asyncio
import json
import random

import httpx
from fastapi import FastAPI

from config import CHECKIN_WEBHOOK_URL, WEBHOOK_SECRET
from job_queue_rabbitmq import queue, PrintJob
from webhook_utils import sign_payload

app = FastAPI(title="Badge Printer Vendor (mock, async via RabbitMQ)")


async def process_print_job(job: PrintJob) -> None:
    """The vendor's own processing -- happens independently of whoever
    published the job. Deliberately randomized duration so that jobs
    published close together can and do complete out of order, which is
    exactly the condition the kiosk's webhook handler has to be correct
    under."""
    await asyncio.sleep(random.uniform(0.5, 3.0))

    status = "failed" if random.random() < 0.08 else "success"
    payload = {"job_id": job.job_id, "attendee_id": job.attendee_id, "status": status}

    raw_body = json.dumps(payload).encode()
    signature = sign_payload(raw_body, WEBHOOK_SECRET)

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(
                CHECKIN_WEBHOOK_URL,
                content=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature-256": signature,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"[vendor] callback delivery failed for job {job.job_id}: {exc}")
            raise


@app.on_event("startup")
async def start_consumer():
    await queue.connect()
    queue.start_worker(process_print_job)


@app.on_event("shutdown")
async def stop_consumer():
    await queue.close()


## ── DEPRECATED as of switching to RabbitMQ -- publishing now goes direct
## to the broker from checkin_service.py, no HTTP hop through the vendor's
## own server needed for that step anymore. Kept for reference only. ──────
@app.post("/queue/print-jobs", status_code=202, deprecated=True)
async def publish_print_job_DEPRECATED(payload: dict):
    """DEPRECATED -- was used when the queue was simulated in-memory inside
    this process (job_queue_inmemory.py) and checkin_service had no other
    way to hand off a job. With a real broker, checkin_service publishes
    directly to RabbitMQ instead."""
    return {"error": "deprecated -- publish directly to RabbitMQ instead"}


## ────────────────────────────────────────────────────────────────────────


## ── DEPRECATED as of the original pivot -- kept for Scope Delta comparison
@app.post("/print-sync")
async def print_badge_sync_DEPRECATED(payload: dict):
    """DEPRECATED. Nothing in the post-pivot kiosk service calls this
    anymore -- see SCOPE_DELTA.md. Left in place only so the pre-pivot
    behavior stays reproducible for the record."""
    attendee_id = payload.get("attendee_id", "unknown")
    await asyncio.sleep(random.uniform(0.5, 1.5))
    if random.random() < 0.08:
        return {"attendee_id": attendee_id, "status": "failed", "reason": "paper jam"}
    return {"attendee_id": attendee_id, "status": "success"}


## ────────────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok"}
