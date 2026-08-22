"""
RabbitMQ-backed message queue (real broker version).

Both the publisher (checkin_service.py) and consumer (printer_vendor.py)
connect independently to the same RabbitMQ broker. They never call each
other directly to publish a job; only the completion webhook is an HTTP call,
matching the pivot brief.

Run RabbitMQ first:
    sudo service rabbitmq-server start
    # or: rabbitmq-server (foreground)
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1/")
QUEUE_NAME = "solstice.print-jobs"


@dataclass
class PrintJob:
    job_id: str
    attendee_id: str


class RabbitMQQueue:
    def __init__(self):
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._queue: Optional[AbstractQueue] = None

    async def connect(self) -> None:
        # connect_robust auto-reconnects on dropped connections -- worth
        # having even in a demo, since it's the difference between "the
        # queue silently stops working" and "it recovers" in production.
        self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        # durable=True: survives a broker restart. Both publisher and
        # consumer declare it so startup order between the two services
        # doesn't matter.
        self._queue = await self._channel.declare_queue(QUEUE_NAME, durable=True)

    async def publish(self, job: PrintJob) -> None:
        if self._channel is None:
            raise RuntimeError("RabbitMQ queue is not connected")
        body = json.dumps(
            {"job_id": job.job_id, "attendee_id": job.attendee_id}
        ).encode()
        await self._channel.default_exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=QUEUE_NAME,
        )

    def start_worker(self, handler: Callable[[PrintJob], Awaitable[None]]) -> None:
        asyncio.create_task(self._consume(handler))

    async def _consume(self, handler: Callable[[PrintJob], Awaitable[None]]) -> None:
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():  # acks on success, requeues on exception
                    data = json.loads(message.body)
                    job = PrintJob(
                        job_id=data["job_id"], attendee_id=data["attendee_id"]
                    )
                    await handler(job)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()


queue = RabbitMQQueue()
