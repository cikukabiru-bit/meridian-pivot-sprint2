"""The cache - our local copy of the warehouse's stock levels.

DESIGN NOTE (important for the Scope Delta Analysis):

This module knows how to STORE stock and ANSWER QUESTIONS about it.
It deliberately knows NOTHING about where the data came from.

That separation is why the Day 4 pivot from polling to webhooks does not
touch this file at all. Whatever fetches the data - a poller, a webhook
receiver, a manual import - simply calls the functions below.
"""

import threading
from datetime import datetime, timezone

# A lock, because the poller writes from a background thread while the web
# server reads from another. Without it two threads could touch the same
# dictionary at once and corrupt it.
_lock = threading.Lock()

# The cache itself: {(product_id, size): row}
_stock = {}

_last_updated = None
_last_source = None


def _key(product_id, size):
    """Build a lookup key that ignores case and stray spaces."""
    return (str(product_id).strip().upper(), str(size).strip().upper())


def replace_all(rows, source="unknown"):
    """Replace the whole cache. Used by a full refresh."""
    global _last_updated, _last_source
    with _lock:
        _stock.clear()
        for row in rows:
            _stock[_key(row["product_id"], row["size"])] = row
        _last_updated = datetime.now(timezone.utc)
        _last_source = source
    return len(_stock)


def apply_update(row, source="unknown"):
    """Update ONE item. Used from Day 4, when webhooks push single changes."""
    global _last_updated, _last_source
    with _lock:
        _stock[_key(row["product_id"], row["size"])] = row
        _last_updated = datetime.now(timezone.utc)
        _last_source = source
    return len(_stock)


def get(product_id, size):
    """Look up one product in one size. Returns None if not cached."""
    with _lock:
        return _stock.get(_key(product_id, size))


def search(term):
    """Find products whose name contains the search term."""
    term = str(term).strip().lower()
    with _lock:
        return sorted(
            (r for r in _stock.values() if term in r["product_name"].lower()),
            key=lambda r: (r["product_name"], str(r["size"])),
        )


def stats():
    """How healthy is the cache right now?"""
    with _lock:
        return {
            "items_cached": len(_stock),
            "last_updated": _last_updated.isoformat() if _last_updated else None,
            "last_source": _last_source,
        }
