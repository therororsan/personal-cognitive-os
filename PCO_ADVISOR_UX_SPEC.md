# PCO_ADVISOR_UX_SPEC.md
Date: 2026-02-14

## Status
- Canonical, evolvable UX spec for the **Advisor** interaction on Telegram.
- Updated to reflect conversational long-term persona (Phase 1).

## Goal
Provide a natural, ongoing conversational cognitive advisor using long-lived memory, psychological snapshot, and high-salience patterns.

## Interaction Style (Phase 1 – Conversational)
- **Capture**: normal voice/text messages → approval gate (unchanged).
- **Advice**: `/ask <question>` starts or continues a conversation.
- No forced mode picker on every message.
- Sticky mode (`/mode fast|deep|clear`) influences tone but is background.
- Follow-up messages are treated as natural continuation of the same thread.

## Response Style
- Always conversational and natural (like chatting with a wise, psychologically informed friend).
- Depth is chosen intelligently by the model based on question + context (no explicit FAST/DEEP required).
- Uses full conversation history + Memory v0 + psychological snapshot.
- Occasionally asks sharp clarifying questions.

## Long-term Design Principles
- Persistent persona across weeks/months.
- Selective memory (psychologist-file style: high-salience, not everything).
- Cost-aware (session summarization, relevance filtering).

## Safety / scope notes
- Non-therapeutic and informational only.
- Never diagnoses.
- Focus on actionable guidance and reflective questions.