"""ORIGINAL SPEC (Day 3): pull stock from the warehouse every 5 minutes.

We ASK the warehouse for the full stock list on a timer, and overwrite the
cache with whatever comes back.

>>> THIS IS THE MODULE THE DAY 4 PIVOT REMOVES. <<<
The client is switching off this feed. Nothing else in the service depends
on this file existing.
"""

import csv
import io
import threading
import time

import requests

import stock_cache
from config import WAREHOUSE_CSV_URL, POLL_INTERVAL_SECONDS


def _parse_csv(text):
    """Turn the warehouse's CSV into a list of clean stock rows."""
    rows = []
    for raw in csv.DictReader(io.StringIO(text)):
        if not raw.get("product_id"):
            continue  # skip blank lines
        rows.append(
            {
                "product_id": raw["product_id"].strip(),
                "product_name": raw["product_name"].strip(),
                "category": raw["category"].strip(),
                "size": raw["size"].strip(),
                "stock_quantity": int(raw["stock_quantity"] or 0),
                "availability": raw["availability"].strip(),
                "restock_date": raw["restock_date"].strip() or None,
            }
        )
    return rows


def poll_once():
    """One full refresh: ask the warehouse, replace the cache."""
    response = requests.get(WAREHOUSE_CSV_URL, timeout=30)
    response.raise_for_status()
    rows = _parse_csv(response.text)
    count = stock_cache.replace_all(rows, source="poll")
    print(f"[poller] refreshed {count} items from the warehouse")
    return count


def _loop():
    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            poll_once()
        except Exception as exc:
            # A failed poll must not kill the service - we keep serving the
            # last known good cache and try again next cycle.
            print("[poller] refresh FAILED, keeping previous cache:", exc)


def start():
    """Refresh immediately, then keep refreshing on a timer in the background."""
    try:
        poll_once()
    except Exception as exc:
        print("[poller] initial refresh FAILED, cache is empty:", exc)

    threading.Thread(target=_loop, daemon=True).start()
    print(f"[poller] will poll every {POLL_INTERVAL_SECONDS} seconds")
