"""Settings for the Northstar inventory sync service."""

# The warehouse's stock feed (Google Sheet "Products" tab, published as CSV).
WAREHOUSE_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vS_ZcEVPEFVxf9feb1Ka4NaG_mXEiMhygk2ZCjC3oGFJoRIqXvPGAv3yNZjjRXPBr23dr7DwyHpNBcp"
    "/pub?gid=37354951&single=true&output=csv"
)

# Original spec: poll every 5 minutes.
POLL_INTERVAL_SECONDS = 300

# Shared secret for verifying webhook messages (used from Day 4 onward).
# NOTE: hard-coded for the prototype. In production this belongs in an
# environment variable or a secret store, never in committed source.
WEBHOOK_SECRET = "northstar-shared-secret-9f3k2m8x"
