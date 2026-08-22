# Learning & Blocker Journal — Sprint 2, Assignment 1

**Learner:** Diana Anne
**Client / sprint:** Northstar Retail Co. — Sprint 2, "The Meridian Pivot"
**Assigned unfamiliar tool:** Webhook signature verification (HMAC-SHA256)
**Prior exposure:** None. No prior backend or Python experience; Sprint 1 role was React frontend.
**Date:** 22 August 2026

## Declared timebox and declared help — read this first

Two honest declarations, made up front rather than buried:

**1. Compressed timebox.** This sprint is designed as two days of solo work. I
started late and had under one day of total working time for the whole sprint.
I therefore set a compressed timebox of roughly 90 minutes for this assignment
rather than two days. The entries below are a real-time record of that window,
not a reconstruction of two days I did not have.

**2. Declared assistance.** I worked the environment setup and the plumbing
(Steps 0–3) with guidance, and I attempted to work from the official `hmac` and
Flask documentation. For the signature verification logic itself (Step 4) I
requested and received step-by-step guidance, including the code, with
line-by-line explanation. I am declaring this rather than presenting the work as
unaided. The understanding recorded in section "What I now know" is genuine and
I can explain every line; the authorship of that section of code is not solely
mine.

**Timebox set:** 90 minutes
**Started:** 22 Aug 2026, approx. 04:45
**Prototype passing all four tests:** 22 Aug 2026, approx. 05:35
**Actual elapsed:** approx. 50 minutes of the 90 allowed

---

## 1. What I understood before I started

*(Written before beginning. Left uncorrected on purpose.)*

- What I thought this tool does: something to do with security on messages
  between two systems — I assumed it was mostly configuration, not code I write.
- Why the client would use it: so the warehouse can tell us about stock changes.
- What I expected to be hard: writing any backend code at all, having only done
  React frontend before.
- What I expected to take longest: understanding the security part.

**What actually took longest:** none of the above. Every significant delay was
Windows environment friction — file naming, PowerShell policy, empty files. The
security logic itself, once the environment worked, was about fifteen lines.

---

## 2. Prototype target

A small service with one endpoint that receives a POST message carrying a
signature header, and decides whether that signature is genuine — accepting with
`200` or rejecting with `401`. Plus a sender script that can produce genuine,
tampered, wrongly-signed and unsigned messages on demand.

**Definition of done — all met:**

- [x] Runs from a clean checkout with documented commands
- [x] Correctly signed message is accepted (200)
- [x] Tampered body with a valid original signature is rejected (401)
- [x] Wrong signature is rejected (401)
- [x] Missing signature header is rejected cleanly, not crashed (401)

---

## 3. Blocker log

### B-01 · ~04:50 · "Running scripts is disabled on this system"

- **Symptom:** `.\.venv\Scripts\Activate.ps1 cannot be loaded because running
  scripts is disabled on this system. ... SecurityError ... UnauthorizedAccess`
- **What I thought was wrong:** Python wasn't installed properly, or the
  installation had failed. My instinct was to abandon local Python and move to an
  online editor instead.
- **What I tried:**
  1. Re-ran the same command assuming a typo
  2. Considered switching to an online Python environment entirely
- **What was actually wrong:** Nothing to do with Python. PowerShell blocks
  running any `.ps1` script file by default as a security measure. It was
  blocking the activation helper script, not Python.
- **How I found it:** Reading the error text properly — it names `Activate.ps1`
  and says `SecurityError`. It never mentions Python.
- **Resolution:** Skipped activation entirely and called the interpreter by its
  full path (`.\.venv\Scripts\python.exe`). No policy change required.
- **Time lost:** ~10 min
- **What I'd do first next time:** Read *which file* the error names before
  concluding which tool is broken.

### B-02 · ~05:05 · "No such file or directory" for a file I had just created

- **Symptom:** `can't open file '...\hello.py': [Errno 2] No such file or
  directory` — for a file visible in File Explorer.
- **What I thought was wrong:** Python was looking in the wrong folder, or the
  virtual environment was misconfigured.
- **What I tried:**
  1. Re-ran the command
  2. Confirmed I was in the right directory with `cd`
  3. Tried a second file (`server.py`) — same error
- **What was actually wrong:** Windows hides known file extensions by default.
  Notepad had saved the file as `hello.py.txt`. Explorer displayed it as
  `hello.py`, so what I could see was not what was on disk.
- **How I found it:** Listing the directory from the terminal
  (`Get-ChildItem`) rather than trusting the Explorer display. The real name was
  immediately visible.
- **Resolution:** Renamed to `hello.py`; enabled file-extension display in
  Explorer so the problem cannot silently recur.
- **Time lost:** ~10 min
- **What I'd do first next time:** When a file "doesn't exist", list the
  directory from the terminal before doubting the tool.

### B-03 · ~05:08 · Pattern noticed across B-01 and B-02

Not a separate bug — a pattern worth recording. In both cases the error message
named the real problem plainly (`Activate.ps1`, `hello.py`), and in both cases my
first hypothesis was "the large thing is broken" (Python, the venv) rather than
"the small thing is misnamed". Recognising that bias was more useful than either
individual fix, and it is the reason B-04 took two minutes instead of twenty.

### B-04 · ~05:12 · Script runs, produces nothing, no error

- **Symptom:** `python server.py` returned to the prompt instantly. No output,
  no error, no server.
- **What I thought was wrong:** Flask had failed to start silently.
- **What I tried:** Checked the file size before anything else — applying the
  lesson from B-03.
- **What was actually wrong:** `server.py` was 0 bytes. I had created the file
  but not yet written or saved anything into it. Python opened an empty file,
  found no instructions, and exited successfully.
- **How I found it:** `Get-Item server.py` — size 0.
- **Time lost:** ~2 min
- **What I'd do first next time:** Silent success with no output usually means an
  empty or unsaved file. Verify contents with `Get-Content` before debugging
  logic that isn't there.

### B-05 · Anticipated and avoided rather than hit

Recorded because the avoidance was deliberate. Three known failure modes of
HMAC verification were identified from the documentation before writing code:

1. **Signing different bytes than were sent.** Avoided by sending the body as a
   plain string with `data=`, rather than `json=` which would let the library
   re-serialise the text and change the bytes.
2. **Hex vs base64 mismatch between sender and receiver.** Avoided by using
   `.hexdigest()` on both sides.
3. **Timing-attack-vulnerable comparison.** Avoided by using
   `hmac.compare_digest()` rather than `==`.

The `str` vs `bytes` distinction was the other expected trap: the sender must
call `.encode()` on its text, while the server must not, because
`request.get_data()` already returns bytes.

---

## 4. Sources consulted

| # | Source | What I was looking for | Did it help? |
| --- | --- | --- | --- |
| 1 | Python official docs — `hmac` module | How to create and compare a fingerprint | Yes — `hmac.new()` and `compare_digest()` |
| 2 | Python official docs — `hashlib` | Which hash to pass to `hmac` | Yes — `sha256` |
| 3 | Flask Quickstart — Minimal Application | Getting any server running | Yes |
| 4 | Flask Quickstart — HTTP Methods, Request Object | Accepting POST, reading headers and raw body | Yes — `methods=`, `request.headers`, `request.get_data()` |
| 5 | Requests docs — POST, custom headers | Sending a signed test message | Yes |

**Human/AI help received:** Declared in full at the top of this document.
Environment setup and plumbing: guided. Step 4 verification logic: step-by-step
guidance including code, with explanation.

---

## 5. Dead ends

| Approach | Why I abandoned it | Time before abandoning |
| --- | --- | --- |
| Switching to an online Python editor | Diagnosed B-01 as a PowerShell policy issue, not a Python one — so the local install was fine. Also: an online editor cannot host a long-running server that receives inbound POSTs, which is exactly what the Day 4 deliverable requires. | ~5 min |
| Changing the PowerShell execution policy | Unnecessary once I called the interpreter by full path. Preferred not to alter a machine-wide security setting to solve a problem that had a simpler answer. | ~2 min |

---

## 6. Time-to-completion

| Phase | Estimate | Actual | Variance |
| --- | --- | --- | --- |
| Environment setup | 10 min | 25 min | **+15 min** |
| Server running (Steps 0–1) | 20 min | 10 min | −10 min |
| Receive + send plumbing (Steps 2–3) | 20 min | 8 min | −12 min |
| Signature verification (Step 4) | 30 min | 10 min (guided) | −20 min, with declared help |
| Testing all four cases | 10 min | 5 min | −5 min |
| **Total** | **90 min** | **~50 min** | **−40 min** |

**Where the estimate broke, and why:** The estimate was wrong in its *shape*,
not its total. I budgeted for the security concept to be the hard part and
setup to be trivial. The reverse was true: every blocker in this journal is an
environment or tooling problem, and none is a conceptual one. For someone new,
the cost of a task is dominated by the toolchain, not the idea. The Step 4
figure is not a fair measure of my own speed, given the declared assistance.

---

## 7. What I now know that I didn't at the start

- **What I most misunderstood:** I assumed webhook security was configuration to
  be switched on. It is code I write, and it is short — around fifteen lines.
- **The concept that took longest to click:** that the signature proves two
  things at once, not one. A password would prove *who sent it*. A signature
  proves *who sent it* **and** *that this exact message is unaltered*, because
  the fingerprint is computed from the message itself. The `tampered` test made
  this concrete: the signature header was completely genuine, and the message
  was still correctly rejected, because it no longer described the body it
  arrived with.
- **What I could teach someone in five minutes:** Both sides share a secret that
  is never transmitted. The sender mixes that secret into the exact message
  through a one-way function to get a fingerprint, and sends it alongside. The
  receiver repeats the calculation with its own copy of the secret and the bytes
  it received, then compares. Change one character of the message and the
  fingerprint changes completely, so tampering is detected.
- **The `str`/`bytes` distinction**, which I had not met before: text and bytes
  are different types in Python, cryptographic functions accept only bytes, and
  `.encode()` converts. This explains why the sender calls `.encode()` and the
  server does not.
- **What I still don't understand:** how the secret is safely shared and rotated
  in production; how a real system handles duplicate or out-of-order webhook
  deliveries; and what `sha256` is actually doing internally.

---

## 8. Carry-forward into the build

- **Reusable:** the verification function transfers almost unchanged into the
  Day 4 webhook receiver. This tool was chosen deliberately for that reason —
  it becomes part of the deliverable rather than a discarded exercise.
- **Throwaway:** the `MODE` switch in the sender is test scaffolding, not
  production code.
- **Known shortcut to flag:** the shared secret is hard-coded in both files. In
  production it belongs in an environment variable or secret store, never in
  committed source. Recorded here as a conscious prototype-stage trade-off
  rather than an oversight.
- **Risk to flag for the build:** Google Sheets cannot send webhooks to a
  service running on localhost — there is no public address for it to reach.
  The pivot will therefore need a warehouse simulator standing in for
  Northstar's system. This is standard practice when building against a
  third-party webhook source, and will be documented in the Scope Delta
  Analysis rather than hidden.

---

## 9. How to run this prototype

```powershell
cd ~\sprint2-inventory-sync

# window 1 - the receiver
.\.venv\Scripts\python.exe server.py

# window 2 - the sender
.\.venv\Scripts\python.exe send.py
```

Edit `MODE` in `send.py` to one of `good`, `tampered`, `wrongsig`, `nosig`.

| MODE | Simulates | Expected |
| --- | --- | --- |
| `good` | A genuine warehouse message | 200 `received` |
| `tampered` | Body altered in transit, original signature kept | 401 `invalid signature` |
| `wrongsig` | A forged signature | 401 `invalid signature` |
| `nosig` | No signature header at all | 401 `missing signature` |

All four verified passing on 22 August 2026.
