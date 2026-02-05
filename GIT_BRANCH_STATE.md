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

## ADD — 2026-02-04 — Verified clean baseline

- Verified clean, pushed baseline for continuation:
  - Branch: `feat/episode-builder-v1-job-final`
  - Commit: `598fa1a`
- This branch now includes:
  - Episode Builder v1 (job-only)
  - Telegram approval gate UX
  - Canonical TAKE_A_DUMP documentation
  - `.gitignore` hygiene for local operator scripts
- New work must branch from this verified baseline unless explicitly stated otherwise.


---

## ADD — 2026-02-05 — Next feature branch (Advisor MVP)

Planned new work:
- Create `feat/advisor-mvp-a1` from the verified baseline (`feat/episode-builder-v1-job-final` at 598fa1a) for Advisor MVP work.
- Record final branch state here once created and pushed.

## ADD — 2026-02-05 — Advisor MVP branch created + checkpoint committed

- Created feature branch:
  - `feat/advisor-mvp-a1`
- Base:
  - branched from `feat/episode-builder-v1-job-final` at `598fa1a`
- Checkpoint commit:
  - `67b5e8d859f92d94c2bd7c67661cfddf7d966d81`
- Scope of change at this checkpoint:
  - Telegram bot: added Advisor MVP A1 (`/ask`, sticky `/mode`, follow-up mode switching, done → return to capture)
