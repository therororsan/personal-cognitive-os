# PCO_ADVISOR_UX_SPEC.md
Date: 2026-02-05

## Status
- Canonical, evolvable UX spec for the **Advisor** interaction on Telegram.
- Separate from capture-gate spec (`PCO_BOT_COPY_SPEC.md`).

## Goal
Provide phone-first coaching advice using long-lived memory, with explicit choice of response depth.

## Interaction Style (A1: command-based separation)

### Capture vs Advice
- **Capture**: normal voice/text messages to the bot → approval gate applies (see `PCO_BOT_COPY_SPEC.md`).
- **Advice**: user sends a command:
  - `/ask <QUESTION>`

This avoids accidental mixing of “capture” and “advice request” intents.

## Advisor response modes

### Mode selection (initial answer)
When bot receives `/ask <QUESTION>`, bot replies with a mode picker message.

**Body:**
```
Choose response mode:
```
**Inline buttons:** ⚡ Fast | 🧠 Deep

Notes:
- The question text itself should be echoed only if doing so does not create copy-friction; otherwise keep messages minimal.
- The system may ask up to 1–3 micro clarification questions before answering, when confidence is low or stakes are high.

### Fast mode answer
Bot replies with an answer optimized for speed and actionability.

### Deep mode answer
Bot replies with an answer optimized for thoroughness.
- Allowed to take longer (minutes), by design.

## Follow-ups with mode switching
After an answer, the bot appends a small mode-switch affordance.

**Body:**
```
Follow-up mode:
```
**Inline buttons:** ⚡ Fast follow-up | 🧠 Deep follow-up

Follow-up user messages (non-command) within an active advisor thread are treated as advice follow-ups until:
- user sends `/done` (optional), or
- a reasonable timeout window is implemented later (not required for MVP)

## Safety / scope notes
- Advice is non-therapeutic and informational; the system is not a clinician.
- The system should avoid diagnosing and instead focus on actionable guidance and reflective questions.
