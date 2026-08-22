"""
Webhook signature verification -- Day 4.

Standard pattern (this is how Stripe, GitHub, etc. do it): the sender
computes an HMAC-SHA256 over the *raw* request body using a secret both
sides know, and puts it in a header. We recompute the same HMAC on our side
and compare. If they don't match, either the secret is wrong or the payload
was tampered with in transit -- either way, reject it.

Critical detail that cost real debugging time while learning this: you must
verify against the raw bytes of the body, not the parsed/re-serialized JSON.
Dict key ordering and whitespace differences between the sender's JSON
encoder and yours will produce a different HMAC even for "the same" data.
"""

import hashlib
import hmac


def sign_payload(raw_body: bytes, secret: str) -> str:
    """Used by the sender (our mock warehouse push simulator) to produce the
    signature header value."""
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def verify_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """Used by the receiver (sync_service) to check an incoming webhook.

    Uses hmac.compare_digest rather than `==` -- a plain string comparison
    leaks timing information about how many leading bytes matched, which is
    a real (if narrow) attack surface for guessing a valid signature.
    """
    if not signature_header:
        return False
    expected = sign_payload(raw_body, secret)
    return hmac.compare_digest(expected, signature_header)
