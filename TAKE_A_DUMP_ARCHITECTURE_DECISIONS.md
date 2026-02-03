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
