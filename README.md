# Meridian Pivot — Sprint 2

Solo build by **Diana Anne**, 22 August 2026.

A one-week industry simulation compressed into a single working day: learn an
unfamiliar tool alone, build to a spec, then absorb a non-negotiable mid-sprint
pivot without losing what already worked.

---

## Deliverables

| Assignment | Deliverable | Where |
| --- | --- | --- |
| 1 | Unfamiliar-tool prototype — webhook signature verification | `server.py`, `send.py` |
| 1 | Learning & Blocker Journal | `LEARNING_JOURNAL.md` |
| 2 | Pivoted deliverable — Solstice Events check-in kiosk | `solstice/` |
| 2 | Scope Delta Analysis | `solstice/SCOPE_DELTA_ANALYSIS.md` |
| 3 | Adaptability Index | **Not in this repository.** Submitted directly to the instructor — the sprint rules require it to stay confidential, and this repository is public. |

Prior work from earlier in the sprint, retained as evidence: a Northstar Retail
inventory sync service that polls a warehouse feed and caches stock
(`app.py`, `stock_cache.py`, `warehouse_poller.py`, `config.py`).

---

## The pivot, in one line

The badge-printer vendor deprecated its **synchronous** print API. The kiosk was
rebuilt to publish print jobs onto the vendor's **message queue** and receive
signed **webhook** callbacks, while still guaranteeing no attendee gets two
badges — even when confirmations arrive out of order.

Read the diff: `git show 6c2c2ef --stat`

---

## Setup

Requires Python 3.12+ and git.

```powershell
git clone https://github.com/cikukabiru-bit/meridian-pivot-sprint2.git
cd meridian-pivot-sprint2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install flask requests huey
```

On Windows, call `.\.venv\Scripts\python.exe` directly rather than activating —
PowerShell blocks the activation script by default.

---

## Running the check-in kiosk (Assignment 2)

Three things run at once. Open two PowerShell windows in `solstice/`.

**Window 1 — the kiosk**

```powershell
..\.venv\Scripts\python.exe kiosk.py
```

**Window 2 — the vendor's printer, draining the queue**

```powershell
..\.venv\Scripts\huey_consumer.exe print_queue.huey -w 4 -k thread
```

**Then open** http://127.0.0.1:5000

### What to try

| Action | Expected |
| --- | --- |
| Scan QR on any attendee | Locks instantly to amber **Printing badge…** — the kiosk does not wait for the printer |
| Scan the same person again while amber | `DUPLICATE SCAN BLOCKED` — no second job queued |
| Wait a few seconds | Turns green **Checked In** when the signed callback arrives |
| Scan several people quickly | They confirm in a different order than you clicked — and all end correct |
| Scan someone showing **Print failed** | Allowed — a failed print releases the attendee to be retried |

Roughly one print in eight fails on purpose, so the failure path is real and
exercised rather than assumed.

### Acceptance tests

With both windows running:

```powershell
..\.venv\Scripts\python.exe test_pivot.py
```

16 tests covering pending state, duplicate protection before and after
confirmation, forged and unsigned callbacks, stale out-of-order callbacks, and
unknown attendees. All passing as of 22 August 2026.

---

## Running the Assignment 1 prototype

```powershell
# window 1
.\.venv\Scripts\python.exe server.py
# window 2
.\.venv\Scripts\python.exe send.py
```

Edit `MODE` in `send.py` to `good`, `tampered`, `wrongsig` or `nosig`.

| MODE | Expected |
| --- | --- |
| `good` | 200 `received` |
| `tampered` | 401 — body altered, original signature kept |
| `wrongsig` | 401 |
| `nosig` | 401, cleanly rejected rather than crashed |

---

## Architecture

```
                  ┌──────────────┐
   staff scan ──► │   kiosk.py   │ ──► claim attendee (attendees.py)
                  └──────┬───────┘         │
                         │ publish         │ status: printing
                         ▼                 │
                ┌────────────────┐         │
                │ print_queue.py │  Huey + SQLite
                │  (vendor's Q)  │
                └────────┬───────┘
                         │ worker prints, then signs
                         ▼
      /webhook/print-complete ──► verify signature (signing.py)
                                       │
                                       ▼
                              status: checked_in
```

`attendees.py` owns all state and knows nothing about how badges are printed.
That separation is why the pivot changed dispatch without rewriting the state
machine's meaning — see the Scope Delta Analysis.

---

## Known limitations

Documented deliberately rather than hidden. Full reasoning in
`solstice/SCOPE_DELTA_ANALYSIS.md`.

- Attendee state is in memory and lost on restart
- The shared signing secret is hard-coded; it belongs in an environment variable
- The kiosk screen polls every second rather than using server-sent events
- No replay-window check on callbacks beyond the job-id ledger
- The printer vendor is simulated locally
