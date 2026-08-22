# Solstice Events Check-In

This module is the post-pivot deliverable for Solstice Events Co. A kiosk
publishes a badge-print request to RabbitMQ and returns `pending`. The mock
printer consumes the job, simulates printing, and calls the kiosk webhook.
The kiosk changes the attendee to `checked_in` only after a valid successful
webhook confirmation.

## Run

Install RabbitMQ, start it, and install the Python dependencies:

```text
pip install -r backend/requirements.txt
```

From `solstice-checkin/backend`, run the vendor and kiosk in separate
terminals:

```text
uvicorn printer_vendor:app --port 9100 --reload
uvicorn checkin_service:app --port 8100 --reload
```

Open `frontend/index.html` and enter at least `ATT-001`, `ATT-002`, and
`ATT-003`. Scan one of them again while it is pending or after it is checked
in to verify that no second job is published.

The default webhook URL is `http://127.0.0.1:8100/webhooks/print-complete`.
Set `RABBITMQ_URL`, `CHECKIN_WEBHOOK_URL`, and `WEBHOOK_SECRET` as environment
variables when using non-local services.

## Tests

Run the focused tests from `backend`:

```text
python -m unittest -v test_checkin.py
```

The tests cover three attendees, duplicate scans, reverse completion order,
duplicate webhook delivery, invalid signatures, and failed publication.

The attendee store is intentionally in memory for this learning simulation.
A production deployment needs shared durable storage to preserve state across
service restarts and replicas.
