# PROJECT_STATE

## Snapshot
- Backend: FastAPI + Postgres, running and stable
- Raw events: append-only, schema {source, text}
- Daily digest: automated at 06:00 Asia/Taipei (conditional on new data)
- Capture surfaces:
  - Telegram text: live
  - Telegram voice: live (V1)

## Voice Capture (V1)
- Voice notes are transcribed client-side
- Transcript text only is persisted to /v1/raw-events
- Audio is transient and not stored

## Status
System is stable at a clean commit boundary post-voice-capture V1.
