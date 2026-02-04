# GIT_BRANCH_STATE (CRITICAL)

## Repository
- Repo: personal-cognitive-os
- Remote default branch:
  origin/feat/daily-episodes-v1-clean

## Branches

### fix/restore-backend-tracking
- Purpose: restore backend source files into git tracking
- Status: pushed and clean
- Must be merged before dependent feature branches

### feat/episode-builder-v1-job-final
- Purpose: Episode Builder v1 (job-only)
- Status: implemented, smoke-tested, committed
- Depends on restore-backend-tracking

## Rules
- Always branch from remote default
- Never reuse polluted branches
- Branch state must be recorded in canonical docs


---

## ADD — 2026-02-04 — Telegram approval gate UX copy spec (PCO_BOT_COPY_SPEC.md)

- Canonical doc set now includes **PCO_BOT_COPY_SPEC.md** for capture UX stability.
