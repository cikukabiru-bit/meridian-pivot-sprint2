"""Settings for the Solstice Events check-in kiosk.

PIVOTED to the asynchronous print model. The vendor's synchronous
PRINTER_API_URL has been decommissioned and removed from this file.
"""

# The vendor's message queue, backed by a SQLite file both processes share.
PRINT_QUEUE_DB = "print_queue.db"

# Where the vendor calls us back when a print job finishes.
KIOSK_WEBHOOK_URL = "http://127.0.0.1:5000/webhook/print-complete"

# Shared secret used to sign and verify those callbacks.
# NOTE: hard-coded for the prototype. In production this belongs in an
# environment variable or a secret store, never in committed source.
WEBHOOK_SECRET = "solstice-printer-secret-4d7b1e9a"

# Header the vendor puts the signature in.
SIGNATURE_HEADER = "X-Solstice-Signature"

KIOSK_PORT = 5000
