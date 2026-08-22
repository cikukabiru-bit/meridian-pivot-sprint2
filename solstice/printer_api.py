"""Stand-in for the badge-printer vendor's SYNCHRONOUS REST API.

>>> ORIGINAL SPEC. The vendor is deprecating this endpoint. <<<

You POST a print request and the connection stays open until the badge has
actually printed - which takes a couple of seconds. The caller waits.

Run on its own port so it is clearly a separate system from our kiosk:
    python printer_api.py
"""

import random
import time
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/print", methods=["POST"])
def print_badge():
    payload = request.get_json(silent=True) or {}
    attendee_id = payload.get("attendee_id")

    if not attendee_id:
        return jsonify({"error": "attendee_id is required"}), 400

    job_id = "JOB-" + uuid.uuid4().hex[:8]
    print(f"[printer] printing badge for {attendee_id} as {job_id} ...")

    # Printing takes real time, and the caller is blocked for all of it.
    time.sleep(random.uniform(1.5, 3.0))

    print(f"[printer] {job_id} finished")
    return jsonify({"status": "success", "job_id": job_id, "attendee_id": attendee_id})


if __name__ == "__main__":
    app.run(port=5001, debug=False)
