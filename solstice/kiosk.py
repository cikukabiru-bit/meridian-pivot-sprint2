"""Solstice Events - check-in kiosk service.

PIVOTED SPEC (asynchronous):
  Staff scan a QR code -> we PUBLISH a print request onto the vendor's
  message queue and return immediately with "printing". The vendor's
  worker prints the badge and then calls our webhook back. Only when that
  signed confirmation arrives is the attendee shown as Checked In.

  Duplicate-scan protection holds under this model because an attendee is
  claimed at publish time, not at confirmation time - see attendees.py.

The synchronous call to the vendor's REST API has been removed entirely,
along with printer_api.py. Nothing here waits on a printer any more.
"""

import json

from flask import Flask, jsonify, request, send_from_directory

import attendees
from config import KIOSK_PORT, SIGNATURE_HEADER
from print_queue import new_job_id, print_badge
from signing import is_valid

app = Flask(__name__, static_folder="static")


@app.route("/")
def kiosk_screen():
    return send_from_directory("static", "index.html")


@app.route("/api/attendees")
def list_attendees():
    """Everything the kiosk screen needs to draw itself, including who is
    mid-print. The screen polls this so pending states resolve on their own."""
    return jsonify({"attendees": attendees.snapshot()})


@app.route("/api/checkin", methods=["POST"])
def checkin():
    """A QR code has been scanned."""
    payload = request.get_json(silent=True) or {}
    attendee_id = (payload.get("attendee_id") or "").strip()

    if not attendees.exists(attendee_id):
        return jsonify({"error": "unknown attendee", "attendee_id": attendee_id}), 404

    job_id = new_job_id()
    claimed, record = attendees.claim(attendee_id, job_id)

    # DUPLICATE-SCAN PROTECTION
    # Refused for anyone already checked in OR still printing. Nothing is
    # published to the queue, so no second badge can ever be produced.
    if not claimed:
        already = "already checked in" if record["status"] == "checked_in" else "already being printed"
        return (
            jsonify(
                {
                    "result": "duplicate_scan",
                    "message": f"{record['name']} is {already} - no second badge queued.",
                    "attendee": record,
                }
            ),
            409,
        )

    # PIVOTED: publish to the vendor's queue and return at once. The kiosk
    # never waits for the printer.
    print_badge(job_id, attendee_id, record["name"])

    return jsonify({"result": "printing", "job_id": job_id, "attendee": record}), 202


@app.route("/webhook/print-complete", methods=["POST"])
def print_complete():
    """The vendor tells us a print job has finished.

    This endpoint is open to the internet, so nothing here is trusted until
    the signature proves the message came from the vendor and was not
    altered in transit.
    """
    raw_body = request.get_data()
    claimed_signature = request.headers.get(SIGNATURE_HEADER)

    if not is_valid(raw_body, claimed_signature):
        print("[kiosk] REJECTED callback - bad or missing signature", flush=True)
        return jsonify({"error": "invalid signature"}), 401

    try:
        message = json.loads(raw_body)
    except ValueError:
        return jsonify({"error": "malformed body"}), 400

    job_id = message.get("job_id")
    attendee_id = message.get("attendee_id")
    succeeded = message.get("status") == "success"

    applied, record = attendees.confirm(
        job_id, attendee_id, succeeded, message.get("reason", "")
    )

    if not applied:
        # Stale, duplicate or out-of-order. Accepted so the vendor stops
        # retrying, but deliberately ignored.
        print(f"[kiosk] IGNORED callback {job_id} for {attendee_id} - not the current job", flush=True)
        return jsonify({"result": "ignored", "reason": "stale or duplicate callback"}), 200

    print(f"[kiosk] {attendee_id} -> {record['status']} via {job_id}", flush=True)
    return jsonify({"result": record["status"], "attendee": record}), 200


@app.route("/api/reset", methods=["POST"])
def reset():
    """Clear all check-ins so the demo can be run again."""
    return jsonify({"attendees": attendees.reset_all()})


if __name__ == "__main__":
    app.run(port=KIOSK_PORT, debug=False)
