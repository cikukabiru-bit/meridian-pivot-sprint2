"""The attendee register for the Solstice Events check-in kiosk.

Holds who is expected at the conference and what state each person's
check-in is in.

DESIGN NOTE: this module owns the state machine and nothing else. It does
not know how badges get printed. That is deliberate - the printing method
changes at the pivot, and this file should barely move.
"""

import threading
from datetime import datetime, timezone

_lock = threading.RLock()

# Who is expected at the conference.
_REGISTER = {
    "ATT-1001": {"name": "Grace Kathau", "ticket": "Full Conference"},
    "ATT-1002": {"name": "Samuel Otieno", "ticket": "Workshop Only"},
    "ATT-1003": {"name": "Leila Mwangi", "ticket": "Speaker"},
    "ATT-1004": {"name": "Tom Barasa", "ticket": "Full Conference"},
}

# Check-in state, one entry per attendee.
#   status: not_checked_in | checked_in | failed
_state = {
    attendee_id: {
        "status": "not_checked_in",
        "job_id": None,
        "message": "",
        "checked_in_at": None,
    }
    for attendee_id in _REGISTER
}


def exists(attendee_id):
    return attendee_id in _REGISTER


def get(attendee_id):
    """Full record for one attendee: who they are plus their check-in state."""
    with _lock:
        if attendee_id not in _REGISTER:
            return None
        record = dict(_REGISTER[attendee_id])
        record.update(_state[attendee_id])
        record["attendee_id"] = attendee_id
        return record


def snapshot():
    """Every attendee, for the kiosk screen."""
    with _lock:
        return [get(attendee_id) for attendee_id in _REGISTER]


def set_status(attendee_id, status, job_id=None, message=""):
    """Move an attendee to a new state."""
    with _lock:
        entry = _state[attendee_id]
        entry["status"] = status
        entry["message"] = message
        if job_id is not None:
            entry["job_id"] = job_id
        if status == "checked_in":
            entry["checked_in_at"] = datetime.now(timezone.utc).isoformat()
        return get(attendee_id)


def reset_all():
    """Put every attendee back to not checked in - for repeatable demos."""
    with _lock:
        for entry in _state.values():
            entry.update(
                {
                    "status": "not_checked_in",
                    "job_id": None,
                    "message": "",
                    "checked_in_at": None,
                }
            )
    return snapshot()
