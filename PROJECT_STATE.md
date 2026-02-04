# PROJECT_STATE (TAKE_A_DUMP 2026-02-04)

## Preservation Notice

This document is **additive and preservative**.
Operational details are retained verbatim unless explicitly superseded.

---

## Backend Status
- FastAPI + Postgres
- Backend is authoritative; chat is non-authoritative
- Running and stable

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

## Daily Digest
- Automated
- Stable
- Produces daily digest artifacts

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
