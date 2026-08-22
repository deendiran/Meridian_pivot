# The Meridian Pivot -- Power Learn Project Sprint

Two independent client scenarios, same repo, same underlying exercise:
build against an original spec, absorb a non-negotiable mid-sprint pivot,
document what changed.

| Module                   | Client               | Original spec                     | Pivot                                   |
| ------------------------ | -------------------- | --------------------------------- | --------------------------------------- |
| `backend/` + `frontend/` | Northstar Retail Co. | Poll a warehouse API every 5 min  | Webhook push                            |
| `solstice-checkin/`      | Solstice Events Co.  | Synchronous badge-print REST call | Async: message queue + webhook callback |

Both are post-pivot as of this version.

## Run everything

Each module needs **two backend processes** running simultaneously (a mock
vendor + the actual service), plus its frontend opened in a browser.

### Northstar (inventory sync)

```bash
cd backend
pip install -r requirements.txt

# Terminal 1 -- the actual deliverable
uvicorn sync_service:app --port 8000 --reload

# Terminal 2 -- simulates the warehouse pushing stock changes
python simulate_warehouse_push.py --loop --interval 4
```

Open `frontend/index.html`. Try SKUs directly (`NS-SKILLET-10IN`,
`NS-MUG-TRAVEL`, `NS-TOTE-COTTON`, `NS-BOARD-BAMBOO`,
`NS-POUROVER-CERAMIC`) or search by name (`skillet`, `tote`, `ceramic`).

### Solstice (check-in kiosk)

```bash
# One-time setup
sudo apt-get install -y rabbitmq-server
pip install -r solstice-checkin/backend/requirements.txt

# Terminal 1 -- start the broker
sudo service rabbitmq-server start
# if that's blocked (common in containers), run in foreground instead:
# rabbitmq-server

cd solstice-checkin/backend

# Terminal 2 -- mock badge-printer vendor (queue consumer + webhook sender)
uvicorn printer_vendor:app --port 9100 --reload

# Terminal 3 -- the actual deliverable
uvicorn checkin_service:app --port 8100 --reload
```

Open `solstice-checkin/frontend/index.html`. Enter an attendee code (e.g.
`ATT-001`) and watch the status ring go from pending to checked-in. Scan
the same code again while it's still pending to see the duplicate-scan
guard reject it.

No RabbitMQ available? Swap `job_queue_rabbitmq` for `job_queue_inmemory`
in the two `import` lines in `checkin_service.py` and `printer_vendor.py`
-- same interface, zero external dependencies, useful for quick local
iteration.

## Project layout

```
meridian-pivot/
├── README.md                       (this file)
├── SCOPE_DELTA.md                  Northstar: what changed in the pivot
├── BLOCKER_JOURNAL.md              Northstar: Day 1-2 log (template)
├── ADAPTABILITY_INDEX.md           Northstar: confidential peer review (template)
│
├── backend/                        Northstar service
│   ├── sync_service.py             webhook receiver + query + search routes
│   ├── webhook_utils.py            HMAC sign/verify
│   ├── simulate_warehouse_push.py  stands in for Northstar's push integration
│   ├── warehouse_api.py            mock warehouse (poll route deprecated)
│   ├── cache.py                    shared in-memory cache + search()
│   ├── config.py, requirements.txt, README.md
│
├── frontend/                       Northstar UI
│   ├── index.html, styles.css
│   └── script.js                   SKU lookup + name search + live sync badge
│
└── solstice-checkin/
    ├── SCOPE_DELTA.md               what changed in this pivot
    ├── BLOCKER_JOURNAL.md           Day 1-2 log (template)
    ├── ADAPTABILITY_INDEX.md        confidential peer review (template)
    │
    ├── backend/
    │   ├── checkin_service.py       publish-and-return-pending + webhook receiver
    │   ├── checkin_service_PRE_PIVOT.py   kept for the record, unused
    │   ├── printer_vendor.py        mock vendor: queue consumer + webhook sender
    │   ├── job_queue_rabbitmq.py    real broker version (aio-pika) -- currently wired in
    │   ├── job_queue_inmemory.py    zero-infra fallback, same interface
    │   ├── state.py                 attendee state machine, unchanged by the pivot
    │   ├── webhook_utils.py, config.py, requirements.txt
    │
    └── frontend/
        ├── index.html, styles.css
        └── script.js                 status ring + pending-state polling
```

## Message queue: real broker vs. in-memory

Both implementations exist and share the same `publish()` / `start_worker()`
interface, so switching is a one-line import change in `checkin_service.py`
and `printer_vendor.py`. `job_queue_rabbitmq.py` is currently wired in and
has been tested against an actual running RabbitMQ broker -- not just
written, verified: job published from `checkin_service`, consumed
independently by `printer_vendor`, webhook fired back, attendee resolved to
`checked_in`, queue drained to zero messages after processing.

## Assignment deliverable map (per module)

| Assignment                              | Northstar               | Solstice                                 |
| --------------------------------------- | ----------------------- | ---------------------------------------- |
| 1: mini-prototype + Blocker Journal     | `BLOCKER_JOURNAL.md`    | `solstice-checkin/BLOCKER_JOURNAL.md`    |
| 2: refactored deliverable + Scope Delta | code + `SCOPE_DELTA.md` | code + `solstice-checkin/SCOPE_DELTA.md` |
| 3: Adaptability Index                   | `ADAPTABILITY_INDEX.md` | `solstice-checkin/ADAPTABILITY_INDEX.md` |
