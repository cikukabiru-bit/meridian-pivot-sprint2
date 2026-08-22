"""Webhook signature signing and verification.

Carried over almost unchanged from the Assignment 1 solo prototype. The
unfamiliar tool learned on Days 1-2 became load-bearing infrastructure
after the pivot, which is why it was chosen.

Both sides hold the same secret, which is never transmitted. The sender
fingerprints the exact bytes it is sending; the receiver repeats the
calculation on the exact bytes it received and compares. Any change to
the message changes the fingerprint completely.
"""

import hashlib
import hmac

from config import WEBHOOK_SECRET


def sign(raw_body: bytes) -> str:
    """Produce the signature for a message we are about to send."""
    return hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()


def is_valid(raw_body: bytes, claimed_signature: str) -> bool:
    """Is this claimed signature genuine for these exact bytes?"""
    if not claimed_signature:
        return False
    # compare_digest, not ==, so the comparison takes the same time whether
    # it fails on the first character or the last. A plain == leaks timing
    # information an attacker can use to guess a signature one byte at a time.
    return hmac.compare_digest(sign(raw_body), claimed_signature)
