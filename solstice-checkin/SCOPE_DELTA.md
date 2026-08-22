# Scope Delta Analysis -- Solstice Check-In Pivot

**Trigger:** Badge-printer vendor deprecating the synchronous print API,
no extension. Rebuild around: publish to vendor's message queue, receive
completion via webhook. UI must show pending until confirmed. Duplicate-
scan protection must hold even with out-of-order confirmations.

## Dropped

- `checkin_service.py`'s blocking `httpx` call to `/print-sync` and the
  wait-for-response logic built around it.
- The assumption that a check-in request's HTTP response tells you the
  final outcome. Post-pivot, the response only confirms the job was
  _accepted_, not that printing succeeded.

## Modified

- `checkin_service.py`: `POST /checkin/{attendee_id}` now returns `202
pending` immediately instead of `200 checked_in` after blocking.
- `printer_vendor.py`: `/print-sync` remains explicitly deprecated for
  historical comparison. The live path consumes `solstice.print-jobs`
  directly from RabbitMQ; no synchronous endpoint is called.

## Added

- `job_queue_rabbitmq.py`: the RabbitMQ message queue adapter. The kiosk
  publishes directly to the durable `solstice.print-jobs` queue and the
  vendor consumes it independently.
- `checkin_service.py`: `POST /webhooks/print-complete` -- the callback
  receiver, keyed on `job_id` rather than attendee or request order.
- `state.py`: `PENDING` state, `mark_pending()`, `attendee_for_job()`,
  `is_job_still_live()`.
- `webhook_utils.py`, `config.py` (`WEBHOOK_SECRET`, queue/webhook URLs).

## Regression check

- `state.py`'s `can_start_checkin()` -- the actual duplicate-scan guard --
  was **not touched**. It already rejected anything outside
  NOT_CHECKED_IN/FAILED before the pivot; PENDING just became a new value
  that guard already excludes. The focused test checks that a scan while a
  job is PENDING returns 409 before a second job is published.
- Out-of-order safety is covered by the focused test: webhook resolution is
  keyed by `job_id` via `is_job_still_live(attendee_id, job_id)`, not by which
  request arrives first, so reverse completion order is handled correctly.
- Idempotency is covered by the focused test: the same webhook payload
  delivered twice resolves the attendee once and safely no-ops the second
  time with `"status": "ignored"`.
- `backend/test_checkin.py` covers three attendees, a duplicate scan, reverse
  completion order, duplicate webhook delivery, invalid signatures, and
  publish failure recovery.

## Reliability decisions

- The RabbitMQ consumer awaits the print-and-callback handler before the
  message is acknowledged. Callback failures therefore cause redelivery.
- A publication failure moves the attendee to `failed` and returns `503`, so
  staff can retry without leaving a permanent `pending` state.
- The demo state store is intentionally in memory. A production deployment
  must replace it with shared durable storage to preserve duplicate
  protection across restarts and service replicas.

## What this cost

- Lost: immediate, synchronous confirmation. Staff (and attendees) now see
  a pending state for however long the vendor's queue takes to drain,
  which is a real UX regression worth flagging to Solstice even though the
  brief mandates it.
- Gained: the kiosk no longer blocks a staff member's scanner during a
  vendor slowdown -- multiple print jobs can be in flight without the
  check-in desk stalling, which the synchronous model couldn't offer at all.
