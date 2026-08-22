import asyncio
import json
import unittest

from fastapi import HTTPException
from starlette.requests import Request

import checkin_service
from state import AttendeeStore
from webhook_utils import sign_payload


def make_request(raw_body: bytes, signature: str) -> Request:
    async def receive():
        return {"type": "http.request", "body": raw_body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhooks/print-complete",
        "headers": [(b"x-signature-256", signature.encode())],
    }
    return Request(scope, receive)


def completion_request(job_id: str, attendee_id: str, status: str) -> Request:
    raw_body = json.dumps(
        {"job_id": job_id, "attendee_id": attendee_id, "status": status}
    ).encode()
    return make_request(
        raw_body, sign_payload(raw_body, checkin_service.WEBHOOK_SECRET)
    )


class CheckinTests(unittest.TestCase):
    def test_three_attendees_duplicate_and_out_of_order_completion(self):
        published = []

        async def publish(job):
            published.append(job)

        original_store = checkin_service.store
        original_publish = checkin_service.queue.publish
        checkin_service.store = AttendeeStore()
        checkin_service.queue.publish = publish

        async def scenario():
            responses = [
                await checkin_service.checkin("ATT-001"),
                await checkin_service.checkin("ATT-002"),
                await checkin_service.checkin("ATT-003"),
            ]
            with self.assertRaises(HTTPException) as duplicate:
                await checkin_service.checkin("ATT-002")
            self.assertEqual(duplicate.exception.status_code, 409)

            for response in responses:
                self.assertEqual(response["status"], "pending")
            self.assertEqual([job.attendee_id for job in published], [
                "ATT-001",
                "ATT-002",
                "ATT-003",
            ])

            for job in reversed(published):
                result = await checkin_service.print_complete(
                    completion_request(job.job_id, job.attendee_id, "success")
                )
                self.assertEqual(result["status"], "recorded")

            duplicate_result = await checkin_service.print_complete(
                completion_request(published[0].job_id, published[0].attendee_id, "success")
            )
            self.assertEqual(duplicate_result["status"], "ignored")
            self.assertTrue(all(
                checkin_service.store.get_state(attendee).value == "checked_in"
                for attendee in ("ATT-001", "ATT-002", "ATT-003")
            ))

        try:
            asyncio.run(scenario())
        finally:
            checkin_service.store = original_store
            checkin_service.queue.publish = original_publish


    def test_publish_failure_releases_pending_attendee(self):
        async def publish(job):
            raise RuntimeError("broker unavailable")

        original_store = checkin_service.store
        original_publish = checkin_service.queue.publish
        checkin_service.store = AttendeeStore()
        checkin_service.queue.publish = publish

        async def scenario():
            with self.assertRaises(HTTPException) as failure:
                await checkin_service.checkin("ATT-FAIL")
            self.assertEqual(failure.exception.status_code, 503)
            self.assertEqual(checkin_service.store.get_state("ATT-FAIL").value, "failed")

        try:
            asyncio.run(scenario())
        finally:
            checkin_service.store = original_store
            checkin_service.queue.publish = original_publish


    def test_invalid_webhook_signature_is_rejected(self):
        original_store = checkin_service.store
        checkin_service.store = AttendeeStore()
        raw_body = b'{"job_id":"job-1","attendee_id":"ATT-001","status":"success"}'

        async def scenario():
            with self.assertRaises(HTTPException) as failure:
                await checkin_service.print_complete(make_request(raw_body, "invalid"))
            self.assertEqual(failure.exception.status_code, 401)

        try:
            asyncio.run(scenario())
        finally:
            checkin_service.store = original_store
