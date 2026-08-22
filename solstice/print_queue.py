"""The badge-printer vendor's MESSAGE QUEUE and worker.

>>> ADDED BY THE PIVOT. Replaces the deleted synchronous printer_api.py. <<<

New technology: Huey, a lightweight task queue, with a SQLite backend so it
needs no Redis or RabbitMQ server.

How the new model works:

  1. The kiosk calls print_badge(...) - this does NOT print anything. It
     writes a job onto the queue and returns immediately.
  2. A separate consumer process (the vendor's printer) picks jobs off the
     queue and actually prints them.
  3. When a job finishes, the worker POSTs a signed callback to the kiosk's
     webhook. Only then is the attendee checked in.

The print delay is deliberately RANDOM. Two jobs published in order will
often finish out of order - which is exactly the condition the kiosk's
duplicate protection has to survive.

Run the vendor's printer with:
    huey_consumer.py print_queue.huey -w 4 -k thread
"""

import json
import random
import time
import uuid

import requests
from huey import SqliteHuey

from config import KIOSK_WEBHOOK_URL, PRINT_QUEUE_DB, SIGNATURE_HEADER
from signing import sign

huey = SqliteHuey(filename=PRINT_QUEUE_DB)


def new_job_id():
    return "JOB-" + uuid.uuid4().hex[:8]


@huey.task()
def print_badge(job_id, attendee_id, name):
    """Runs inside the VENDOR's worker process, not the kiosk."""
    delay = random.uniform(1.0, 6.0)
    print(f"[printer] {job_id} for {attendee_id} - printing, {delay:.1f}s", flush=True)
    time.sleep(delay)

    # Occasionally a badge genuinely fails to print. The kiosk must cope.
    succeeded = random.random() > 0.12

    payload = {
        "job_id": job_id,
        "attendee_id": attendee_id,
        "name": name,
        "status": "success" if succeeded else "failed",
        "reason": "" if succeeded else "printer out of badge stock",
    }

    # Sign the EXACT bytes we are about to send - not a re-serialised copy.
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", SIGNATURE_HEADER: sign(raw)}

    try:
        requests.post(KIOSK_WEBHOOK_URL, data=raw, headers=headers, timeout=10)
        print(f"[printer] {job_id} -> {payload['status']}, callback sent", flush=True)
    except Exception as exc:
        print(f"[printer] {job_id} callback FAILED: {exc}", flush=True)
