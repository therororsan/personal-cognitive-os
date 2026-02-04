# PCO_BOT_COPY_SPEC.md
Date: 2026-02-04

## Status
- This document is a **canonical UX copy spec** for the Telegram capture bot approval gate.
- It is **additive** and should be updated when capture UX changes (approve/edit/reject, edit-mode wording, cancel behavior).

## Principle
iOS Telegram “Copy” copies the entire message. Therefore, any message intended to be copied/edited MUST contain only the transcript text.

## Review message (after voice OR text)
**Body:**
```
<TRANSCRIPT_TEXT>
```
**Inline buttons:** ✅ Approve | ✏️ Edit | ❌ Reject

## Edit flow
### Enter edit mode (tap ✏️ Edit)
Bot sends a new message with:
**Body:**
```
<TRANSCRIPT_TEXT>
```
**Inline button:** ❌ Cancel

### Submit edit (user replies with corrected text)
Bot replies:
```
Updated.
```
Then re-sends the Review message (transcript-only) with ✅/✏️/❌ buttons.

### Cancel edit (tap ❌ Cancel)
Bot replies:
```
Cancelled.
```
Then re-sends the Review message (transcript-only) with ✅/✏️/❌ buttons.

## Approve
Bot replies:
```
Logged ✅
```

## Reject
Bot replies:
```
Discarded ❌
```

## Consistency
Text messages use the same approval gate as voice messages.
