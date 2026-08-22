"""Acceptance tests for the pivoted (asynchronous) check-in kiosk.

Run the kiosk and the vendor's queue consumer first, then:
    python test_pivot.py

Covers every requirement in the client handout.
"""

import json
import time

import requests

from config import KIOSK_WEBHOOK_URL, SIGNATURE_HEADER
from signing import sign

BASE = "http://127.0.0.1:5000"
passed = failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


def scan(attendee_id):
    return requests.post(f"{BASE}/api/checkin", json={"attendee_id": attendee_id})


def state():
    return {a["attendee_id"]: a for a in requests.get(f"{BASE}/api/attendees").json()["attendees"]}


def send_callback(payload, signature=None):
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signature != "OMIT":
        headers[SIGNATURE_HEADER] = signature if signature else sign(raw)
    return requests.post(KIOSK_WEBHOOK_URL, data=raw, headers=headers)


print("Resetting demo...")
requests.post(f"{BASE}/api/reset")

print("\n1. A scan returns immediately and reports a pending state")
start = time.time()
first = scan("ATT-1001")
elapsed = time.time() - start
check("responds 202 Accepted", first.status_code == 202, first.status_code)
check("status is 'printing', not 'checked_in'", first.json()["attendee"]["status"] == "printing")
check(f"returns fast ({elapsed:.2f}s, kiosk does not wait for the printer)", elapsed < 1.0)
job_id = first.json()["job_id"]

print("\n2. Duplicate scan WHILE STILL PRINTING is blocked")
dup = scan("ATT-1001")
check("responds 409 Conflict", dup.status_code == 409, dup.status_code)
check("no second job queued", dup.json()["attendee"]["job_id"] == job_id)

print("\n3. Three attendees check in via webhook confirmation")
scan("ATT-1002")
scan("ATT-1003")
deadline = time.time() + 25
while time.time() < deadline:
    current = state()
    if all(current[a]["status"] in ("checked_in", "failed") for a in ("ATT-1001", "ATT-1002", "ATT-1003")):
        break
    time.sleep(0.5)
current = state()
for attendee in ("ATT-1001", "ATT-1002", "ATT-1003"):
    check(f"{attendee} settled ({current[attendee]['status']})",
          current[attendee]["status"] in ("checked_in", "failed"))

print("\n4. Duplicate scan AFTER check-in is blocked")
settled = [a for a in ("ATT-1001", "ATT-1002", "ATT-1003") if state()[a]["status"] == "checked_in"]
if settled:
    again = scan(settled[0])
    check("responds 409 Conflict", again.status_code == 409, again.status_code)
else:
    check("responds 409 Conflict", False, "no attendee reached checked_in to test with")

print("\n5. A forged callback is rejected")
bad = send_callback(
    {"job_id": "JOB-forged", "attendee_id": "ATT-1004", "status": "success"},
    signature="0" * 64,
)
check("responds 401 Unauthorized", bad.status_code == 401, bad.status_code)
check("ATT-1004 was not checked in", state()["ATT-1004"]["status"] == "not_checked_in")

print("\n6. A callback with no signature at all is rejected, not crashed")
missing = send_callback({"job_id": "JOB-x", "attendee_id": "ATT-1004", "status": "success"}, signature="OMIT")
check("responds 401 Unauthorized", missing.status_code == 401, missing.status_code)

print("\n7. A correctly signed but STALE callback is ignored (out-of-order safety)")
if settled:
    victim = settled[0]
    replay = send_callback(
        {
            "job_id": "JOB-stale999",
            "attendee_id": victim,
            "name": state()[victim]["name"],
            "status": "failed",
            "reason": "a late confirmation from an abandoned job",
        }
    )
    check("accepted with 200 so the vendor stops retrying", replay.status_code == 200, replay.status_code)
    check("marked as ignored", replay.json().get("result") == "ignored", replay.json())
    check(f"{victim} is still checked_in, not overwritten", state()[victim]["status"] == "checked_in")
else:
    check("stale callback ignored", False, "no checked_in attendee to test with")

print("\n8. An unknown attendee is rejected")
unknown = scan("ATT-9999")
check("responds 404 Not Found", unknown.status_code == 404, unknown.status_code)

print(f"\n{'=' * 46}\n  {passed} passed, {failed} failed\n{'=' * 46}")
