"""
Simulated message queue -- the actual new technology this pivot is about.

No real broker is reachable in this environment, so this stands in for
what would be RabbitMQ, AWS SQS, or Redis Streams in production: a
publish() that hands a job off asynchronously, and a background worker
loop that consumes jobs independently of whoever published them. The
important property being demonstrated -- and the whole reason the client
wants this instead of a synchronous call -- is that publish() returns
immediately and does NOT wait for the job to be processed.

Lives on the vendor side (printer_vendor.py owns the queue), matching the
brief: "publish a print request onto the vendor's message queue."
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Awaitable


@dataclass
class PrintJob:
    job_id: str
    attendee_id: str


class MessageQueue:
    def __init__(self):
        self._queue: asyncio.Queue[PrintJob] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def publish(self, job: PrintJob) -> None:
        """Hand a job off and return immediately -- this is the async
        behavior the sync version didn't have. The publisher never blocks
        on processing."""
        await self._queue.put(job)

    def start_worker(self, handler: Callable[[PrintJob], Awaitable[None]]) -> None:
        """Starts the background consumer loop. `handler` does the actual
        work (simulated printing) and is responsible for firing the webhook
        callback once done -- the queue itself doesn't know about webhooks,
        it only knows about moving jobs from publisher to consumer."""
        self._worker_task = asyncio.create_task(self._run(handler))

    async def _run(self, handler: Callable[[PrintJob], Awaitable[None]]) -> None:
        while True:
            job = await self._queue.get()
            asyncio.create_task(
                handler(job)
            )  # process concurrently, don't serialize print jobs
            self._queue.task_done()

    def stop_worker(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()


queue = MessageQueue()
