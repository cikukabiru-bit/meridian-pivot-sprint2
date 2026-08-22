# Scope Delta Analysis

**Assignment 2 · Meridian Pivot Sprint · Diana Anne**
**Client:** Solstice Events Co. — conference check-in kiosk
**Date of pivot:** 22 August 2026
**Repository:** https://github.com/cikukabiru-bit/meridian-pivot-sprint2

---

## 1. What changed, and what it cost

**The client's message:** the badge-printer vendor is deprecating the
synchronous print API. The kiosk must publish print requests onto the vendor's
message queue and expose a webhook to receive completion callbacks. The UI can
no longer confirm check-in on button press — it must show a pending state until
confirmation arrives. Duplicate-scan protection must still hold, even though
confirmations may arrive out of order. **No deadline extension.**

The pivot was not cosmetic. It inverted control flow: the kiosk stopped being
the party that *waits for an answer* and became the party that *is called back*.
Everything downstream of that inversion had to change.

### Dropped

| Removed | Why | Evidence |
| --- | --- | --- |
| `printer_api.py` — the vendor's synchronous REST print API | Endpoint decommissioned by the vendor | File **deleted** in commit `6c2c2ef` (−40 lines), not commented out or left running |
| The blocking `requests.post()` call to the printer inside `/api/checkin` | Nothing may wait on the printer any more | Removed from `kiosk.py` |
| `PRINTER_API_URL`, `PRINT_TIMEOUT_SECONDS` | Dead configuration for a dead endpoint | Removed from `config.py` |
| "Confirm on button press" UI behaviour | Check-in is no longer known at press time | `static/index.html` — the request handler no longer sets a final state |
| The two-state model (`not_checked_in` / `checked_in`) | Insufficient: a badge can now be in flight | Replaced in `attendees.py` |

**Regression check:** after removal, the full acceptance suite `test_pivot.py`
passes **16 of 16**, including all three original requirements (three test
attendees check in successfully; duplicate scan blocked; unknown attendee
rejected). No functionality present before the pivot was lost. No code path to
the deleted synchronous API remains — `printer_api.py` is absent from the
working tree and from `HEAD`, and no module imports it.

### Modified

| Changed | From | To |
| --- | --- | --- |
| `attendees.py` state machine | 2 states | 3 states: `not_checked_in → printing → checked_in`, plus `failed` returning to scannable |
| Duplicate protection trigger | Blocked only `checked_in` | Blocks `printing` **and** `checked_in` — the attendee is claimed at publish time |
| `/api/checkin` response | `200 OK` with the final answer | `202 Accepted` with a pending answer |
| Kiosk screen | Drew once per action | Polls `/api/attendees` every second, because outcomes now arrive by a route the browser never sees |
| `config.py` | Printer URL and timeout | Queue database, webhook callback URL, shared signing secret |

### Added

| New | Purpose |
| --- | --- |
| `print_queue.py` | The vendor's message queue and worker, built on **Huey** with a SQLite backend — the "new technology" for this pivot. Chosen because it is a genuine queue library that needs no Redis or RabbitMQ server, which was decisive given the compressed timeline. |
| `/webhook/print-complete` on the kiosk | Receives signed completion callbacks from the vendor |
| `signing.py` | HMAC-SHA256 signing and timing-safe verification |
| Pending UI state | Amber, pulsing, with the Scan button locked while a badge is in flight |
| `test_pivot.py` | 16 automated acceptance tests covering every handout requirement |
| Idempotency ledger (`_settled_jobs`) | Ensures a repeated delivery of the same job cannot be applied twice |

---

## 2. The hardest problem the pivot created

**Duplicate protection could no longer wait for confirmation.**

Under the synchronous model the question "has this person already been given a
badge?" had a simple answer, because the kiosk blocked until the printer replied.
There was no window in which a badge existed but the system did not know it.

Asynchronously, that window is the normal case. A second scan arriving two
seconds after the first finds an attendee who is *not yet checked in* — the badge
is still printing. Checking `status == "checked_in"` would have let a second
badge through, which is precisely the failure the client named.

**The fix:** claim the attendee at *publish* time, not confirmation time. The
moment a job goes onto the queue the attendee moves to `printing`, and
`claim()` refuses anyone in `printing` or `checked_in`. The claim and the status
read happen under a single lock, so two simultaneous scans cannot both succeed.

**The second-order problem:** if state can be claimed before it is confirmed,
then a *late* confirmation from an abandoned job could overwrite newer, correct
state. So each attendee records the `job_id` that claimed them, and `confirm()`
drops any callback whose `job_id` is not the current one. A settled-jobs ledger
additionally makes repeat deliveries of the same job harmless.

Verified empirically. Jobs published in the order 1001 → 1002 → 1003 → 1004
were confirmed in the order **1003 → 1001 → 1002 → 1004**, and every attendee
still ended in the correct state.

---

## 3. Trade-offs accepted, and what they cost

| Decision | Gained | Cost / risk |
| --- | --- | --- |
| Huey + SQLite rather than Redis or RabbitMQ | A real queue library with zero infrastructure setup — deliverable within the deadline | SQLite is not the right broker at conference scale; a production deployment would swap the backend. The application code would not change, only the Huey configuration line. |
| Kiosk screen polls every 1 second | Simple, robust, no extra dependency | Wasteful at scale and up to 1s of visual lag. Server-sent events or websockets would be the production answer; polling was chosen because it could not fail under time pressure. |
| Attendee state held in memory | Fast, no database work | State is lost if the kiosk restarts mid-conference. Genuinely unacceptable in production — the register belongs in a database. Flagged, not solved. |
| Shared secret hard-coded in `config.py` | No secret-management setup | Visible in a public repository. Prototype value only; belongs in an environment variable or secret store. Declared rather than hidden. |
| Vendor simulated locally | Demonstrable end to end with no third party | A real vendor would differ in retry behaviour, signature format and payload shape. The signature verification and idempotency logic are written to be independent of those details. |
| 12% simulated print-failure rate | Forces the failure path to be real and tested | Makes demo runs non-deterministic — an attendee may show `Print failed` and need a re-scan. This is intended behaviour, not a bug. |

---

## 4. Reprioritised backlog

**Done — the client's stated requirements**

1. Publish print requests to the vendor's message queue
2. Webhook endpoint receiving completion callbacks
3. Pending state visible in the UI until confirmation
4. Duplicate-scan protection holding under the async model
5. Correct behaviour under out-of-order confirmations
6. At least three test attendees checking in successfully
7. Obsolete synchronous code removed, not left running

**Deferred — deliberately, with reasons**

| Item | Why deferred |
| --- | --- |
| Persistent attendee register (database) | Highest-value next item. In-memory state was accepted only because the deadline was fixed and no requirement named durability. |
| Automatic retry / dead-letter handling for failed prints | Currently staff re-scan manually. Acceptable for a staffed kiosk; not acceptable unattended. |
| Replay-window protection (timestamp + nonce on callbacks) | Signature verification proves authenticity but an intercepted callback could in principle be replayed. The job-id ledger blunts this; a timestamp check would close it. |
| Server-sent events instead of polling | Cosmetic and performance only; no requirement depends on it. |
| Secret moved to environment variable | One-line change, deferred only because nothing in the demo depends on it. |
| Real QR scanner input | The handout's scan action is simulated by a button; scanner integration is hardware work outside this sprint. |
| Adding attendees from the kiosk UI | Identified as a genuine operational need — staff will have walk-ups. Requires the persistent register above to be built first, otherwise additions are lost on restart. Deferred as scope beyond the client's stated requirements, not as an oversight. |
| A `declined` status for attendees not attending | Would need to block scanning like `checked_in` does, and to take precedence over a print confirmation arriving afterwards for a job already in flight. The existing `confirm()` job-id check already provides the mechanism. Deferred for the same reason. |

---

## 5. Honest notes on process

Two things are worth recording plainly rather than presenting a smoother story.

**The sprint was compressed.** I started late and had under one working day for
what is designed as a five-day sprint. Assignment 1's timebox was reduced from
two days to ninety minutes, and this is declared at the top of
`LEARNING_JOURNAL.md` rather than disguised with fabricated entries.

**I received step-by-step assistance on the Assignment 1 verification logic**,
also declared in that journal. It is relevant here because that same code became
`signing.py` after the pivot.

**What went right, and was deliberate:** the pre-pivot build separated the
*source* of data from the *state* it produced. Because `attendees.py` never knew
how badges were printed, the pivot changed how work was dispatched without
rewriting what the system knew. The unfamiliar tool for Assignment 1 was also
chosen for its likelihood of surviving the pivot — the webhook verification
written on Day 1 is in production use in the final deliverable, unchanged in
substance.

**What I would do differently:** clarify the scenario before building. The
sprint brief described one client and product (Northstar Retail, inventory sync)
and the pivot handout described another (Solstice Events, check-in kiosk). I
built against the first before discovering the second. That earlier work is
retained in the repository and its architecture proved transferable, but the
time spent was avoidable and the lesson is to confirm the brief before writing
code, not after.
