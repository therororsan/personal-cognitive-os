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

## ADD — 2026-02-04 — Stabilization discipline decision

- Introduced an explicit **stabilization window** concept:
  - During stabilization, no new features or refactors are introduced.
  - Only alignment, verification, and canonical documentation updates are allowed.
- Decision:
  - Stabilization must end in a **clean, pushed checkpoint** before any new feature work proceeds.
- This rule now applies to future multi-step work (e.g. capture UX, episode logic, future surfaces).


## ADD — 2026-02-05 — Platform strategy: Telegram now, surface-agnostic core

Decision:
- Telegram is used as an initial **phone-first** surface for capture + advice because it is fast to ship.
- Core logic must remain **surface-agnostic** so an iOS/Android app can be built later without re-architecting.

---

## ADD — 2026-02-05 — Advisor MVP interaction style (A1)

Decision:
- Advisor MVP uses **command-based separation** in Telegram:

  - Capture = normal voice/text messages (approval gate)
  - Advice = `/ask <question>`

Rationale:
- Avoids accidental mixing of “capture” vs “question” intent.
- Transfers cleanly to future app surfaces (separate capture vs ask screens).

---

## ADD — 2026-02-05 — App development gate (A/B/C)

Decision:
- Custom app work is deferred until all are proven in real use:
  A) Capture works
  B) Analysis filing/storage is visible and correct
  C) Advisor (FAST/DEEP) works with follow-up mode switching

---

## ADD — 2026-02-05 — Canonical salience + advisor UX specs

Decision:
- Promote the following to canonical, evolvable artifacts:
  - `PSYCHOLOGICAL_SALIENCE_FRAMEWORK.md`
  - `PCO_ADVISOR_UX_SPEC.md`

These must be included in future TAKE_A_DUMP snapshots.

---

## ADD — 2026-02-05 — Advisor MVP A1: sticky default mode (Option A)

Decision:
- Advisor mode (FAST/DEEP) is **sticky by default** per user:
  - The user can set a default with `/mode fast` or `/mode deep`.
  - The default persists until cleared with `/mode clear`.
  - `/ask <question>` uses the sticky default; mode picker is only needed when no default exists.

Rationale:
- Reduces friction for repeated usage while keeping a clean A1 command boundary (`/ask` vs capture).
- Keeps Telegram UX thin and avoids over-investment in surface-specific behaviors.

Implementation checkpoint:
- Branch: `feat/advisor-mvp-a1`
- Commit: `67b5e8d859f92d94c2bd7c67661cfddf7d966d81`

---

## ADD — 2026-02-05 — “Daily digest” terminology is superseded (non-user-facing)

Decision:
- “Daily digest to user” is **not** a requirement.
- Any periodic processing is background-only (batch analysis / episode builder / memory update), with operator-visible artifacts.
- Avoid reintroducing “daily digest” language in future plans unless explicitly requested.

## ADD — 2026-02-06 — Controlled Codex Adoption

Decision:
- Codex may be used starting at **Layer 3 (Memory Construction)** only.
- Codex is an optional accelerator, not a default workflow.

Constraints:
- Codex must follow the **Codex Usage Protocol** in AI_WORKING_PROFILE.md.
- Safety, reversibility, and isolation take precedence over speed.

Rationale:
- Previous negative Codex experience (file deletion, unrecoverable state) requires strict governance.
- Canonical discipline must extend to tooling choices.

## ADD — 2026-02-06 — Layer 3: Memory Construction v0 (append-only)

Decision:
- Introduce file-based memory ledger:
  - `backend/logs/memory/<user_id>/memory_v0.jsonl`
- Append-only JSONL format.
- No DB schema changes.
- No destructive updates.
- No compaction or merging.

Properties:
- Weak-signal / confidence-weighted.
- Each entry must include:
  - source episode path
  - source input_hash
  - evidence pointer
- Re-runs must not duplicate entries for same input_hash.

Rationale:
- Enables long-term memory accumulation without architectural risk.
- Fully reversible (delete memory folder to disable).
- Keeps Layer 3 isolated from core system.

Classification:
- Non-breaking.
- No API changes.
- Job-only.

---

## ADD — 2026-02-13 — Advisor reads Memory v0 as weak-signal context (read-only)

Decision:
- The Advisor surface may **read** Memory v0 (append-only JSONL) and inject recent entries into answers as context.
- This is **read-only** and does not modify memory artifacts during advisory responses.

Constraints (binding):
- Memory v0 remains:
  - append-only
  - confidence-weighted / weak-signal
  - reversible
  - file-based
- No DB schema changes.
- No compaction / consolidation.
- Advisor must fail-open (no user-visible errors) if memory is missing or ambiguous.

Deterministic user mapping:
- Prefer explicit mapping via:
  - `PCO_MEMORY_USER_ID=<user_id>`
- Tail control:
  - `PCO_MEMORY_TAIL_LIMIT=<N>` (default: 20)

Rationale:
- Improves advice continuity without introducing irreversible memory semantics or new infrastructure risk.
