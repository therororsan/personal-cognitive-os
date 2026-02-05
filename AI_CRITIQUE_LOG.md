# AI_CRITIQUE_LOG

## 2026-02-03 — Institutional Knowledge Risk
- Risk: loss of transcription provider knowledge
- Mitigation: record provider-switch architecture in TAKE_A_DUMP docs

## 2026-02-04 — Git Hygiene Failure Mode
- Issue: feature branch created from incorrect base
- Symptom: backend appeared untracked
- Resolution:
  - Restore backend tracking in dedicated branch
  - Add explicit git/branch state documentation

## 2026-02-04 — Canonical Doc Erosion Incident

- Issue: Regeneration of TAKE_A_DUMP_ARCHITECTURE_DECISIONS removed provider-level details.
- Impact: Risk of losing institutional architectural knowledge.
- Resolution:
  - Codified additive + preservative rule in AI_WORKING_PROFILE.
  - Added explicit preservation notices to canonical docs.
- Status: Locked; future violations must be recorded.

## ADD — 2026-02-04 — Timestamp timezone observation (non-failure)

- Observation: Episode artifact metadata included mixed timezone offsets:
  - `generated_at` was recorded with `+08:00`
  - `source_latest_event_at` was recorded with `+00:00`
- Note: This is an observation for operator clarity; no architecture or schema change implied.



---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

- Added **PCO_BOT_COPY_SPEC.md** as canonical to prevent UX copy regressions (esp. iOS transcript copy friction).

## ADD — 2026-02-04 — Cmd.exe multiline failure mode (non-fatal)

- Observation:
  - Using parenthesized multi-line `echo` blocks in cmd.exe triggered `More?` prompts.
- Impact:
  - No functional breakage; command eventually completed correctly.
- Resolution / rule:
  - Prefer **single-line append commands** in cmd.exe to avoid interactive prompts.
- Classification: operator ergonomics issue, not a system failure.


---

## ADD — 2026-02-05 — Tool/platform mismatch risk (phone UX)

Risk:
- Designing workflows that are not supported by the chosen surface (Telegram) can cause rework or degraded UX.

Mitigation:
- Codify surface UX specs (capture + advisor) as canonical docs.
- Keep core logic surface-agnostic.
- Defer app investment until A/B/C milestone proves the loop works.

## ADD — 2026-02-05 — Multiple bot processes caused silent “no response” symptom

Issue:
- `/mode` and `/ask` produced no replies in Telegram despite the API being healthy.

Primary causes observed:
- Multiple concurrent `telegram_capture_bot.py` processes (multiple pollers) running at the same time.
- Bot file on disk did not actually contain the new `/ask` + `/mode` handlers (replacement mismatch).

Resolution:
- Kill all matching processes via `stop_pco.bat`, then restart via `start_pco.bat` only.
- Verify handler registration exists before testing Telegram:
  - `findstr /n /i "CommandHandler(\"ask\"" backend\telegram_capture_bot.py`
  - `findstr /n /i "CommandHandler(\"mode\"" backend\telegram_capture_bot.py`

Classification:
- Operator/process hygiene issue + file replacement mismatch, not a backend or Telegram API defect.
