"""Solstice Events - check-in kiosk service.

ORIGINAL SPEC (synchronous):
  Staff scan an attendee's QR code -> we call the badge-printer vendor's
  REST API and WAIT for it to report success -> only then do we mark the
  attendee checked in and show "Checked In" on screen.

  An attendee who is already checked in must not get a second badge.
"""

import requests
from flask import Flask, jsonify, request, send_from_directory

import attendees
from config import PRINTER_API_URL, PRINT_TIMEOUT_SECONDS

app = Flask(__name__, static_folder="static")


@app.route("/")
def kiosk_screen():
    return send_from_directory("static", "index.html")


@app.route("/api/attendees")
def list_attendees():
    """Everything the kiosk screen needs to draw itself."""
    return jsonify({"attendees": attendees.snapshot()})


@app.route("/api/checkin", methods=["POST"])
def checkin():
    """A QR code has been scanned."""
    payload = request.get_json(silent=True) or {}
    attendee_id = (payload.get("attendee_id") or "").strip()

    if not attendees.exists(attendee_id):
        return jsonify({"error": "unknown attendee", "attendee_id": attendee_id}), 404

    current = attendees.get(attendee_id)

    # DUPLICATE-SCAN PROTECTION
    # Already checked in means a badge has already been printed. Refuse,
    # and do not touch the printer.
    if current["status"] == "checked_in":
        return (
            jsonify(
                {
                    "result": "already_checked_in",
                    "message": f"{current['name']} is already checked in - no second badge printed.",
                    "attendee": current,
                }
            ),
            409,
        )

    # ORIGINAL SPEC: call the printer and block until it answers.
    try:
        response = requests.post(
            PRINTER_API_URL,
            json={"attendee_id": attendee_id, "name": current["name"]},
            timeout=PRINT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        record = attendees.set_status(
            attendee_id, "failed", message=f"Printer unreachable: {exc}"
        )
        return jsonify({"result": "print_failed", "attendee": record}), 502

    if result.get("status") != "success":
        record = attendees.set_status(
            attendee_id, "failed", message="Printer reported failure"
        )
        return jsonify({"result": "print_failed", "attendee": record}), 502

    # The badge is physically printed, so and only so is the attendee checked in.
    record = attendees.set_status(attendee_id, "checked_in", job_id=result.get("job_id"))
    return jsonify({"result": "checked_in", "attendee": record})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Clear all check-ins so the demo can be run again."""
    return jsonify({"attendees": attendees.reset_all()})


if __name__ == "__main__":
    app.run(port=5000, debug=False)
