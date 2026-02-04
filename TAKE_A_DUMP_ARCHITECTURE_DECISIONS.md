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
