"""The attendee register for the Solstice Events check-in kiosk.

PIVOTED. The state machine gained a middle state:

    not_checked_in  ->  printing  ->  checked_in
                              \\-->  failed  -->  (scannable again)

Under the old synchronous model there was no middle state: the kiosk
blocked until the printer answered, so an attendee was either checked in
or not. Under the async model a badge can be in flight, and that gap is
where every hard problem in this assignment lives.

TWO RULES THAT MAKE DUPLICATE PROTECTION HOLD:

1. CLAIM ON PUBLISH, NOT ON CONFIRMATION.
   claim() refuses an attendee who is already `printing` as well as one
   already `checked_in`. A second scan arriving while the first badge is
   still printing is rejected, because nobody would be checked in yet and
   waiting for confirmation would let a second badge through.

2. ONLY THE CURRENT JOB MAY CONFIRM.
   Each attendee records the job_id that claimed them. confirm() ignores
   any callback whose job_id is not that one. Stale, duplicated and
   out-of-order confirmations are therefore harmless - they are simply
   dropped rather than overwriting a newer state.

Both operations happen under one lock, so a claim cannot interleave with
another claim for the same attendee.
"""

import threading
from datetime import datetime, timezone

_lock = threading.RLock()

_REGISTER = {
    "ATT-1001": {"name": "Grace Kathau", "ticket": "Full Conference"},
    "ATT-1002": {"name": "Samuel Otieno", "ticket": "Workshop Only"},
    "ATT-1003": {"name": "Leila Mwangi", "ticket": "Speaker"},
    "ATT-1004": {"name": "Tom Barasa", "ticket": "Full Conference"},
}

_BLANK = {
    "status": "not_checked_in",
    "job_id": None,
    "message": "",
    "checked_in_at": None,
}

_state = {attendee_id: dict(_BLANK) for attendee_id in _REGISTER}

# Every callback we have already applied, so a repeated delivery of the
# same job cannot be processed twice.
_settled_jobs = set()


def exists(attendee_id):
    return attendee_id in _REGISTER


def get(attendee_id):
    with _lock:
        if attendee_id not in _REGISTER:
            return None
        record = dict(_REGISTER[attendee_id])
        record.update(_state[attendee_id])
        record["attendee_id"] = attendee_id
        return record


def snapshot():
    with _lock:
        return [get(attendee_id) for attendee_id in _REGISTER]


def claim(attendee_id, job_id):
    """Try to claim an attendee for printing.

    Returns (True, record) if the claim succeeded and a job may be
    published, or (False, record) if this is a duplicate scan.
    """
    with _lock:
        current = _state[attendee_id]

        if current["status"] in ("printing", "checked_in"):
            return False, get(attendee_id)

        current.update(
            {"status": "printing", "job_id": job_id, "message": "", "checked_in_at": None}
        )
        return True, get(attendee_id)


def confirm(job_id, attendee_id, succeeded, reason=""):
    """Apply a print-completion callback.

    Returns (applied, record). applied is False when the callback is
    stale, duplicated or out of order - in which case nothing changes.
    """
    with _lock:
        if attendee_id not in _REGISTER:
            return False, None

        current = _state[attendee_id]

        # Already processed this exact job - a repeat delivery.
        if job_id in _settled_jobs:
            return False, get(attendee_id)

        # Not the job that currently owns this attendee: an out-of-order or
        # abandoned callback. Drop it rather than overwrite newer state.
        if current["job_id"] != job_id:
            return False, get(attendee_id)

        _settled_jobs.add(job_id)

        if succeeded:
            current["status"] = "checked_in"
            current["message"] = ""
            current["checked_in_at"] = datetime.now(timezone.utc).isoformat()
        else:
            # Release the attendee so staff can retry the scan.
            current["status"] = "failed"
            current["message"] = reason or "Badge did not print"
            current["job_id"] = None

        return True, get(attendee_id)


def reset_all():
    with _lock:
        for entry in _state.values():
            entry.update(dict(_BLANK))
        _settled_jobs.clear()
    return snapshot()
