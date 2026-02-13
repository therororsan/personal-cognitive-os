# AI_WORKING_PROFILE

## Confirmed Preferences
- Cmd.exe-first instructions
- Small, sequential steps
- Downloadable replacement files only (no inline edits)
- Backend is authoritative; chat is non-authoritative
- Canonical docs are binding; chat is non-binding

## New Reinforced Mode
- RMP: always provide downloadable artifacts for file changes

---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

### Canonical doc set expanded
- Canonical docs now include **PCO_BOT_COPY_SPEC.md**.
- TAKE_A_DUMP snapshots must include it and keep it additive/preservative.

### Governance
- Any change to Telegram capture UX requires:
  1) Update PCO_BOT_COPY_SPEC.md
  2) Append to DECISION_LOG.md + PROJECT_STATE.md (do not delete prior details)
  3) Record any deviations/failure modes in AI_CRITIQUE_LOG.md

---

## ADD — 2026-02-05 — Operational invariant: prevent multiple Telegram bot pollers

Failure pattern:
- Running multiple `telegram_capture_bot.py` processes concurrently (e.g., start_pco.bat + manual runs) can cause Telegram updates to be consumed unpredictably, including “no response” symptoms.

Operator rule:
- Before restarting, always run:
  - `call stop_pco.bat`
- Prefer launching via `call start_pco.bat` (single known-good entrypoint) rather than starting the bot manually.
- If Telegram replies appear missing, immediately verify only one bot process is running.

Suggested operator check (read-only):
- From repo root:
  - `powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*telegram_capture_bot.py*' -and $_.CommandLine -notlike '*cmd /k*' }; ($p|Measure-Object).Count"`
Expected: `1`

---

## ADD — 2026-02-06 — Codex Usage Protocol (BINDING)

Codex is approved **only as a surgical accelerator**, never as a default tool.

### Preconditions (MANDATORY)
Before any Codex involvement:
1) `git status` MUST be clean  
2) All work MUST be committed and pushed  
3) Repo root MUST be confirmed  

If any of the above is false → **Codex use is forbidden**.

### Scope Isolation
- Codex may only operate on **explicitly named files or directories**
- No global refactors
- No file deletions
- No renames
- No schema / API / architecture changes unless explicitly authorized

### Recovery Guarantee
- `git restore` MUST be sufficient to fully revert Codex changes
- If rollback cannot be guaranteed → Codex must not be used

### Output Contract
- Codex-generated changes must be:
  - minimal
  - explained
  - provided as downloadable replacement files only

Codex violations must be recorded in **AI_CRITIQUE_LOG.md**.


---

## ADD — 2026-02-13 — Operator environment variables (PCO)

Recommended persistent settings (Windows):
- Use `setx` for user-level persistence (takes effect in new shells).
- Use `set` for current-shell immediacy.

Memory v0 (advisor read-only context):
- `PCO_MEMORY_USER_ID=<user_id>` (recommended, deterministic)
- `PCO_MEMORY_TAIL_LIMIT=<N>` (optional; default 20)
