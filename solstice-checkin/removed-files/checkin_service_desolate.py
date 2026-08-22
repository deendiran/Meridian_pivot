"""
Kiosk Check-In Service -- post-pivot (async via message queue + webhook)
--------------------------------------------------------------------------
Vendor deprecated the synchronous print API with no extension. Staff still
scan a QR code, but now: we publish a print job onto the vendor's queue and
return immediately with a PENDING state. "Checked In" only appears once the
vendor's webhook confirms the print actually completed -- and confirmations
can now arrive out of order, so the webhook handler resolves state by
job_id, not by request order.

    Terminal 1: uvicorn printer_vendor:app --port 9100 --reload
    Terminal 2: uvicorn checkin_service:app --port 8100 --reload

--------------------------------------------------------------------------
NOTE: state.py is UNCHANGED from the pre-pivot version. The duplicate-scan
guard (can_start_checkin) didn't need to change at all -- it already
rejected anything not in NOT_CHECKED_IN/FAILED, which holds regardless of
whether the print call underneath is sync or async.
--------------------------------------------------------------------------
"""

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from config import WEBHOOK_SECRET
from job_queue_rabbitmq import queue, PrintJob
from state import store
from webhook_utils import verify_signature

app = FastAPI(title="Solstice Kiosk Check-In (post-pivot, async via RabbitMQ)")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
async def connect_queue():
    await queue.connect()


@app.on_event("shutdown")
async def disconnect_queue():
    await queue.close()


@app.post("/checkin/{attendee_id}", status_code=202)
async def checkin(attendee_id: str):
    # Same duplicate-scan guard as pre-pivot, unchanged -- this is what
    # keeps duplicate protection correct under the new async model. A scan
    # while PENDING is rejected here, before a second job is ever published.
    if not store.can_start_checkin(attendee_id):
        current = store.get_state(attendee_id)
        raise HTTPException(
            status_code=409,
            detail=f"Attendee {attendee_id} is already {current.value}; badge not reprinted.",
        )

    job_id = str(uuid.uuid4())
    store.mark_pending(attendee_id, job_id)

    # Publish directly to the shared RabbitMQ broker and return immediately
    # -- no HTTP call to the vendor's own server needed for this step.
    await queue.publish(PrintJob(job_id=job_id, attendee_id=attendee_id))

    return {"attendee_id": attendee_id, "status": "pending", "job_id": job_id}


@app.post("/webhooks/print-complete")
async def print_complete(request: Request):
    """Vendor calls this once a queued print job finishes. Must be correct
    even if:
      - this confirmation arrives before an earlier-published job's does
        (out-of-order -- resolved by keying on job_id, not arrival order)
      - the same confirmation is delivered twice (idempotency -- resolved
        by is_job_still_live returning False the second time, since the
        job's already been resolved and cleared from the live-job map)
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Signature-256", "")
    if not verify_signature(raw_body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    job_id = payload["job_id"]
    attendee_id = payload["attendee_id"]
    result_status = payload["status"]

    if not store.is_job_still_live(attendee_id, job_id):
        # Stale or duplicate delivery -- already resolved (or superseded).
        # Safe no-op, not an error: at-least-once delivery is normal for
        # real message queues/webhooks, the receiver has to tolerate it.
        return {"status": "ignored", "reason": "job already resolved or unknown"}

    if result_status == "success":
        store.mark_checked_in(attendee_id)
    else:
        store.mark_failed(attendee_id)

    return {"status": "recorded", "attendee_id": attendee_id, "job_id": job_id}


@app.get("/status/{attendee_id}")
def status(attendee_id: str):
    return {"attendee_id": attendee_id, "status": store.get_state(attendee_id).value}


@app.get("/health")
def health():
    return {"status": "ok"}
