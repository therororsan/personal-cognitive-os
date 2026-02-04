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

