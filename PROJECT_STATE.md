# PROJECT_STATE (TAKE_A_DUMP 2026-02-14)

## Preservation Notice
This document is **additive and preservative**.
Operational details are retained verbatim unless explicitly superseded.

---

## Major Milestone Achieved (2026-02-14)
- **Advisor Beta Gate Passed**: `/ask` now triggers real LLM (Grok via xAI) with full patient-folder context (psychological snapshot + Memory v0 + episode recap).
- Sticky FAST/DEEP modes working.
- Follow-up conversations preserved via session history.
- Capture flow (voice + text + approval gate) remains completely untouched.

## Backend Status
- FastAPI + Postgres
- Backend is authoritative; chat is non-authoritative
- Running and stable

## Advisor Status (Current)
- Real LLM-backed (Grok)
- Context: psychological snapshot, Memory v0 (read-only), episode summaries
- Modes: sticky default via `/mode fast|deep|clear`
- Picker shown only when no default set
- Conversational follow-ups active (history preserved)
- Fail-open fallback implemented

## Next Phase (approved direction)
- Evolve to persistent conversational persona (natural back-and-forth like this chat)
- Long-term memory design (psychologist-file style: selective, high-salience, cost-controlled)
- Voice capture remains sacred and unchanged

[All previous sections from 2026-02-04 TAKE_A_DUMP remain verbatim below this line...]



## Raw Events
- Append-only ingestion
- Schema: { "source": "...", "text": "..." }
- Endpoint: POST /v1/raw-events

## Capture Surfaces

### Telegram
- Text capture: live
- Voice capture: live (V1)

### Voice Transcription (V1)
- Client-side only
- Backend remains text-only
- Audio is transient and not stored

#### Providers
- Default: Deepgram
- Alternative: Google Cloud Speech-to-Text

#### Switch Mechanism
- `PCO_TRANSCRIBE_PROVIDER=deepgram|google`
- `GOOGLE_APPLICATION_CREDENTIALS=<path>`

---

## Background analysis (daily batch; not user-facing)

- The project does **not** require a user-facing “daily digest” sent to the user.
- A daily (or periodic) batch job may exist purely as **background maintenance** to:
  - organize/structure captured records into durable memory/history,
  - update episode artifacts,
  - update retrieval indexes for advisor.
- Terminology guardrail:
  - Use “batch analysis” / “episode builder” / “background maintenance job” rather than “daily digest” unless you explicitly re-introduce a user-facing digest requirement.

---

## Episode Builder v1 (LOCKED)
- Job-only
- Invocation: `python -m jobs.run_episode_builder` (from backend/)
- Output:
  `backend/logs/episodes/<user_id>/<YYYY-MM-DD>.json`
- Idempotent per user/day via `input_hash`
- Advisory, non-therapeutic

## ADD — 2026-02-04 — Operational verification: Telegram voice → transcription → raw event → Episode Builder v1 → artifact

- Completed an end-to-end operational run using real Telegram voice input (capture + client-side transcription + raw event ingestion).
- Episode Builder v1 executed successfully via:
  - `python -m jobs.run_episode_builder`
- Run output:
  - `[run_episode_builder] user_id=094ebda7-4004-422d-8857-7ee773756a6d updated: 2026-02-04.json events=3`
  - `[run_episode_builder] done | date=2026-02-04 users=1 written=1 skipped=0`
- Artifact path written:
  - `backend\logs\episodes\094ebda7-4004-422d-8857-7ee773756a6d\2026-02-04.json`
- Artifact contents (2026-02-04.json):
  - Top-level keys present: `recap`, `psychological_status`, `actionable_advice[]`, `date`, `meta{}`
  - `meta.event_count=3`
  - `meta.input_hash=585e2428692bf6d5018c38820b561fd333b721c563c8c148537e6d31bacb18c5`
  - `meta.generated_at=2026-02-04T11:00:12.728736+08:00`
  - `meta.source_latest_event_at=2026-02-04T02:59:47.046602+00:00`
  - `meta.digest_included=false`
- Artifact file size observation:
  - `find /c /v "" <artifact>` reported 17 lines.

---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

### New canonical doc
- Added **PCO_BOT_COPY_SPEC.md** (Telegram approval gate copy/UX spec) to the canonical doc set so future TAKE_A_DUMP snapshots include it.

### Placement in repo
- Store at repo root:
  - `C:\Users\User\OneDrive\SMART\personal-cognitive-os\PCO_BOT_COPY_SPEC.md`

### How it is used
- Operator + developer reference for Telegram capture UX.
- Codex changes that touch Telegram capture UX MUST be aligned to this spec.
- If bot behavior changes, update this doc and include it in the next TAKE_A_DUMP.

---

## ADD — 2026-02-04 — Stabilization checkpoint completed

- A full stabilization window was executed and closed successfully.
- Scope of stabilization:
  - Canonical documentation aligned and committed (TAKE_A_DUMP).
  - Telegram capture approval gate (approve / edit / reject) verified live.
  - Edit-mode UX confirmed transcript-only per iOS copy constraint.
  - Local-only operator scripts (`start_pco.bat`, `stop_pco.bat`) explicitly ignored via `.gitignore`.
- Stabilization commit head:
  - Branch: `feat/episode-builder-v1-job-final`
  - Commit: `598fa1a`
- Backend + Telegram bot restarted successfully after stabilization.
- Text and voice capture flows both pass through the approval gate correctly.

Status: **Stable, ready for controlled continuation**.

---

## ADD — Known Safe Resume Commands (PCO)

Purpose: cold-start resume to a known-good operational state with **minimal risk**.  
Properties: cmd.exe-first, no discovery, no file edits, no schema/API changes.

Operator repo root:
`C:\Users\User\OneDrive\SMART\personal-cognitive-os`

### 0) Open cmd.exe in repo root
```bat
cd /d C:\Users\User\OneDrive\SMART\personal-cognitive-os
```

### 1) Confirm branch + cleanliness (read-only)
```bat
git branch --show-current
git status
```
Expected:
- Correct branch per `GIT_BRANCH_STATE.md`
- Ideally: working tree clean

### 2) Stop any stale PCO processes (idempotent)
```bat
call stop_pco.bat
```
Note: “PID not found” messages are benign if nothing was running.

### 3) Start API + Telegram bot (known-good launch)
```bat
call start_pco.bat
```
Expected:
- API running on `http://127.0.0.1:8000`
- Telegram capture bot running

### 4) Minimal API liveness check (read-only)
```bat
curl http://127.0.0.1:8000/health
```
Expected:
- HTTP 200 (or project-standard health response)

### 5) Minimal Telegram UX liveness (manual, no code changes)
- Send a **text** message to the Telegram bot  
  Expected: approval gate appears (✅ Approve | ✏️ Edit | ❌ Reject), message body is transcript-only.
- Tap **✏️ Edit**  
  Expected: edit-mode message body is transcript-only + ❌ Cancel.
- (Optional) Send a **voice** message  
  Expected: same gate behavior as text.

### 6) Optional — Episode Builder job sanity run (job-only)
Run only if you intend to operate Episode Builder now:
```bat
cd /d C:\Users\User\OneDrive\SMART\personal-cognitive-os\backend && call .\.venv\Scripts\activate.bat && docker compose up -d && python -m jobs.run_episode_builder
```
Expected:
- Clear “done” output
- Writes or skips based on new events (no errors)


---

## ADD — 2026-02-05 — Surface-agnostic phone-first MVP (Capture + Advisor)

### Phone-first objective
Primary user experience is phone-based:
- **Capture** thoughts via voice/text
- **Ask** for advice (FAST or DEEP)
- Iterate via follow-ups (mode-switchable)

Telegram is the current surface because it ships fastest, but the system must avoid Telegram lock-in.

### Success milestone before building a custom app
We will not invest in an iOS/Android app until all three are true:

A) Capture works end-to-end on phone (voice/text → approved transcript stored)  
B) The system can show evidence that it analyzed/organized/stored the record correctly (operator-visible artifacts)  
C) The user can receive AI coaching advice (FAST + DEEP), with follow-up mode switching

Only after A/B/C are met do we consider a custom app surface.

### Canonical UX specs
To support cold-start continuity, the following surface specs are canonical (and evolvable):

- `PCO_BOT_COPY_SPEC.md` — capture approval gate UX (voice + text)
- `PCO_ADVISOR_UX_SPEC.md` — advisor UX (A1 command-based `/ask`, FAST/DEEP)

### Psychological salience framework
- `PSYCHOLOGICAL_SALIENCE_FRAMEWORK.md` is canonical and evolvable.
- It guides retention/retrieval priority; it is not a rigid contract.

## ADD — 2026-02-05 — Advisor MVP A1 shipped on Telegram (sticky mode)

Milestone:
- Advisor MVP (A1 command-based) is implemented in the Telegram bot and verified working in real use.
- Branch: `feat/advisor-mvp-a1`
- Commit: `67b5e8d859f92d94c2bd7c67661cfddf7d966d81`

User-facing commands (Telegram):
- Set sticky default mode:
  - `/mode deep` (default advisor mode = DEEP)
  - `/mode fast` (default advisor mode = FAST)
  - `/mode clear` (removes sticky default; `/ask` will prompt)
- Ask for advice:
  - `/ask <question>`

Advisor interaction rules (Telegram):
- `/ask` enters advisor flow and responds in FAST or DEEP depending on the sticky default (or via picker if no default set).
- Follow-up mode can be switched via buttons during an active advisor session.
- Exiting advisor session returns to normal capture behavior (approval gate applies to normal text/voice).

Non-goals / constraints:
- Telegram UX is intentionally kept minimal (“thin Telegram”) to prove the end-to-end loop before any custom iOS/Android surface work.
- Core logic remains surface-agnostic; Telegram is just the current surface.

## Backend Status
- FastAPI + Postgres
- Backend is authoritative; chat is non-authoritative
- Running and stable

---

## Development Tooling Policy (ADD — 2026-02-06)

- Human-driven development is the default.
- Codex is approved **only** as a constrained accelerator.
- All Codex usage must:
  - occur after a clean, committed checkpoint
  - be fully reversible via git
  - respect isolation boundaries

This project explicitly prioritizes:
- correctness
- inspectability
- recoverability

over raw iteration speed.

---

## Layer 3 — Memory Construction v0 (LOCKED)

Status:
- Implemented as job-only (`run_memory_builder.py`)
- File-based
- Append-only JSONL ledger
- No DB schema changes

Artifact path:
- `backend/logs/memory/<user_id>/memory_v0.jsonl`

Properties:
- Weak-signal candidates only
- Confidence-weighted
- Evidence-linked to episode artifacts
- Fully reversible (delete memory directory)

Non-goals:
- No consolidation
- No compaction
- No irreversible summarization
- No schema modification


---

## ADD — 2026-02-13 — Layer 3 Memory v0 integrated into Advisor (Telegram)

Status:
- Layer 3 Memory v0 remains **job-only, file-based, append-only**, and fully reversible (no DB/schema changes).
- Advisor now **reads** Memory v0 entries and injects them into `/ask` answers as **weak-signal context** (read-only).

Memory artifact:
- `backend/logs/memory/<user_id>/memory_v0.jsonl`

Advisor integration behavior (read-only):
- On `/ask` answers and follow-ups, the bot may prepend a block:
  - `MEMORY CANDIDATES (weak-signal; confidence-weighted)`
- If memory cannot be resolved safely, the advisor proceeds without memory (fail-open).

Deterministic user mapping (recommended):
- Environment variable:
  - `PCO_MEMORY_USER_ID=<user_id>`
- Optional:
  - `PCO_MEMORY_TAIL_LIMIT=<N>` (default: 20)

Reversibility:
- Deleting `backend/logs/memory/` disables all Layer 3 effects immediately.
- No memory compaction or consolidation is introduced.
