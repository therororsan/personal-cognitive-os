# TAKE_A_DUMP — Architecture Decisions & Open Forks

**Status:** Authoritative snapshot  
**Purpose:** Prevent loss of architectural/roadmap decisions across chats. This document records *what is locked*, *what is tentative*, and *what remains explicitly undecided*, so future work never relies on human memory or chat archaeology.

---

## 1. Hard Invariants (LOCKED)

### 1.1 System Role
- Backend + repo + canonical docs are the source of truth; chat is non-authoritative.
- System is **diagnostic/advisory only** (no execution or automation of real-world actions).
- Not therapy; no motivational fluff; no clinical identity labels.

### 1.2 Data Model
- Raw events are **append-only / immutable**; corrections are new events.
- Audio is **transient**; transcripts are **durable**.

### 1.3 Processing Cadence
- **Batch analysis only** (no per-message coaching).
- **Daily digest at 06:00 Asia/Taipei**, triggered **only if new data exists** since the last digest.

### 1.4 Operating Protocol
- AI must follow **AI_WORKING_PROFILE** (cmd.exe-first, small sequential steps, no monolithic scripts, no architecture changes unless requested).

---

## 2. Implemented & Verified (LOCKED)

- FastAPI backend operational.
- Raw event ingestion (`POST /v1/raw-events`) verified.
- Daily digest job (`python -m jobs.run_digest`) verified.
- Windows Task Scheduler automation in place.
- Operator logging enabled (per-day logs under `backend\logs`).

---

## 3. Capture Surface — Intent vs Status

### 3.1 Intent (LOCKED)
- **Voice-first**, **mobile-first**, **chat-based** capture.
- Phone is the primary interface; desktop-only capture is insufficient.
- Chat interaction (voice/text messages), **not** phone calls.

### 3.2 Target (TENTATIVE)
- Custom **iOS app (SwiftUI)** is the long-term capture surface.

### 3.3 Current State (LOCKED)
- **No capture surface exists yet** (no app, no bot, no UI).

### 3.4 Interim Capture (LOCKED)
- **Telegram bot, text-only** is the first interim capture surface.
- Bot behavior: acknowledge only (“Logged ✅”); no coaching, no questions by default.

### 3.5 Audio Capture (LOCKED INTENT)
- Audio capture (voice notes) is a **must-have later**, but is **not implemented in the interim text-only bot**.
- Audio pipeline details remain to be decided when implementing voice.

---

## 4. Roadmap Sequencing (LOCKED)

1. Backend first (completed).
2. Interim capture surface (Telegram text-only) next (in progress).
3. Delivery of digest to user (notification surface) after capture exists.
4. Voice capture pipeline (Telegram voice or iOS app) after text capture proves daily usage.
5. Episode structuring, pattern detection, belief tracking — **Phase 2+** only.
6. External object storage (e.g., R2) — deferred (Phase 2+).

---

## 5. Things Explicitly *Not* Decided (to avoid false memory)

- Whether the interim capture surface should be Telegram voice notes vs iOS app voice notes first.
- Web UI.
- Multiple digests per day.
- Real-time coaching mode.

---

## 6. Next Required Decision (UPCOMING)

> After Telegram text capture is stable, decide:
> - Voice capture path (Telegram voice notes vs iOS app first)
> - Audio storage + retention + transcription approach

---

## 7. Update Policy

- Any future decision that affects capture, cadence, scope, or sequencing **must be added here** at the next TAKE_A_DUMP.
- Conversational agreement without an entry here is **non-authoritative**.
