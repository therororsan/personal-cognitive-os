# ARCHITECTURE DECISIONS (TAKE_A_DUMP)

## Locked Decisions

### Voice Transcription
- Location: client-side only (capture surface)
- Backend remains text-only and schema-stable

### Providers
- Default: Deepgram
- Supported alternative: Google Cloud Speech-to-Text (service account)
- Switch mechanism:
  - PCO_TRANSCRIBE_PROVIDER=deepgram|google
  - GOOGLE_APPLICATION_CREDENTIALS=<path>

### Invariants
- No audio stored in backend
- No backend schema or endpoint changes


---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

### Capture UX (Telegram approval gate)
- Review gate applies to **both** text and voice capture.
- Edit-mode messages must be **transcript-only** (iOS copy behavior constraint).
- Cancel is provided as an inline button (and /cancel remains acceptable as a backstop).
- The authoritative wording + button behavior is specified in **PCO_BOT_COPY_SPEC.md** (canonical).

## ADD — 2026-02-04 — Stabilization invariants

- During stabilization windows:
  - Architecture decisions are not revisited.
  - Only documentation alignment and behavioral verification are permitted.
- This reinforces existing locked decisions and does not introduce new architecture.


---

## ADD — 2026-02-05 — Surface-agnostic “Capture” and “Advisor” separation (INTENT-LEVEL)

### Surface-agnostic core
Core capabilities are defined independent of surface:
- Capture event ingestion (approved transcript)
- Advisor query handling (FAST/DEEP)

Telegram is a client; future iOS/Android app is another client.

### Surface UX constraints for MVP
- Advisor uses **A1 command-based** separation:
  - `/ask <question>` for advice
  - normal messages for capture

### Transferability requirement
All capture/advice concepts must map cleanly to a future mobile app:
- capture screen (voice/text + coarse tags)
- ask screen (FAST/DEEP)
- follow-up with mode switching

## ADD — 2026-02-06 — Codex Isolation Requirement (LOCKED)

- Codex must operate only on isolated, explicitly approved files.
- Codex must not modify core system files unless explicitly authorized.
- Git is the sole rollback mechanism.
- Any Codex-induced drift is considered an architectural failure.

This decision is locked to prevent accidental large-scale repo damage.

---

## ADD — 2026-02-06 — Memory Construction v0 Isolation (LOCKED)

- Memory v0 must:
  - be append-only
  - be file-based
  - avoid schema changes
  - avoid irreversible compaction

- Memory entries must:
  - include source_input_hash
  - include source_episode_path
  - include confidence and salience fields

- Reversibility guarantee:
  - Deleting `backend/logs/memory/` fully disables Layer 3 effects.
  - No core system modification is allowed.

This decision prevents premature hardening of memory semantics.
