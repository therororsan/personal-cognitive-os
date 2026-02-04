# DECISION_LOG (TAKE_A_DUMP 2026-02-04)

## Voice Capture V1 (2026-02-03)
- Added Telegram voice capture
- Transcription is client-side only
- No backend schema or endpoint changes
- Default provider: Deepgram
- Google Cloud STT supported via env switch

## Episode Builder v1
- Implemented as job-only
- No API surface
- No DB schema changes
- File-based artifacts only

## Operational Decisions
- Postgres must be running (docker compose) before jobs
- Cmd.exe-first workflow
- Prefer single-line commands to avoid cmd.exe `More?`

## ADD — 2026-02-04 — Operational verification outcome (Telegram voice → Episode Builder v1)

- Verified an end-to-end run using real Telegram voice input:
  - voice capture + client-side transcription + raw event ingestion + `python -m jobs.run_episode_builder` + artifact creation
- Episode Builder v1 run output:
  - date=2026-02-04 users=1 written=1 skipped=0 events=3
- Artifact written:
  - `backend\logs\episodes\094ebda7-4004-422d-8857-7ee773756a6d\2026-02-04.json`
- Artifact metadata observed:
  - `input_hash=585e2428692bf6d5018c38820b561fd333b721c563c8c148537e6d31bacb18c5`
  - `generated_at=2026-02-04T11:00:12.728736+08:00`
  - `source_latest_event_at=2026-02-04T02:59:47.046602+00:00`
  - `digest_included=false`



---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

- Added **PCO_BOT_COPY_SPEC.md** as canonical UX copy spec for Telegram approval gate (approve/edit/reject + transcript-only edit mode).
- Policy: If capture-bot reply strings/buttons change, update PCO_BOT_COPY_SPEC.md and include it in TAKE_A_DUMP.
- Operational note: current operator repo root is `C:\Users\User\OneDrive\SMART\personal-cognitive-os`.