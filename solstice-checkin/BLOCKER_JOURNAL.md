# Learning & Blocker Journal: Solstice Check-In

**Assignment:** 1, independent learning and blocker log
**Tool/concept:** RabbitMQ message queues and HMAC-signed webhooks
**Time-boxed to:** _Fill in the assigned time_
**Actual time spent:** _Fill in after completing the work_

This record must describe the actual learning process. Do not replace the
placeholders with an invented story. Add entries while working, including
dead ends, resources consulted, and time lost.

## Goal

Build a small prototype in which a check-in request publishes a badge-print
job, the vendor processes it asynchronously, and a signed webhook confirms
the result.

## Resources consulted

- _Add the RabbitMQ/aio-pika documentation actually consulted._
- _Add the FastAPI or webhook-signing documentation actually consulted._

## Blockers

### Blocker 1

- **What happened:** _Describe the observed error or dead end._
- **What I tried:** _List the attempts made without direct how-to help._
- **What fixed it:** _Record the verified fix._
- **Time lost:** _Record the time._

### Blocker 2

- **What happened:** _Add another real blocker, or remove this section._
- **What I tried:** _Record the attempts._
- **What fixed it:** _Record the verified fix._
- **Time lost:** _Record the time._

## Final state

The current prototype publishes to the durable `solstice.print-jobs`
RabbitMQ queue, keeps the attendee pending until a valid signed completion
webhook arrives, and rejects duplicate scans while pending or checked in.
The state store is intentionally in memory for this simulation.

## What I would do differently

_Fill in an honest reflection based on the actual work._
