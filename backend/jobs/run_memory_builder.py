"""
Layer 3 — Memory Construction v0 (append-only, reversible)

Properties:
- File-based (no DB/schema changes)
- Append-only JSONL ledger per user
- Weak-signal, confidence-weighted
- Evidence pointers to episode artifacts
- Re-runs are idempotent per episode input_hash
- NEW: avoid redundant writes via statement-level dedup (still append-only; no mutation)

Notes:
- This is intentionally conservative. v0 extracts only psychological_status snapshots.
- Dedup rule: do not append a candidate if the same (candidate_type, statement) already exists
  anywhere in the user's memory_v0.jsonl ledger.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set, Tuple, Any

BASE_DIR = Path(__file__).resolve().parents[1]
EPISODES_DIR = BASE_DIR / "logs" / "episodes"
MEMORY_DIR = BASE_DIR / "logs" / "memory"


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_jsonl_iter(path: Path) -> Iterable[Dict[str, Any]]:
    """Best-effort JSONL reader. Skips malformed lines."""
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def load_existing_dedup_sets(memory_file: Path) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """
    Returns:
      - existing_input_hashes: all source_input_hash values seen in ledger (for idempotence-by-episode)
      - existing_statements: set of (candidate_type, statement) seen in ledger (for dedup-by-statement)
    """
    existing_input_hashes: Set[str] = set()
    existing_statements: Set[Tuple[str, str]] = set()

    for obj in _safe_jsonl_iter(memory_file):
        h = obj.get("source_input_hash")
        if isinstance(h, str) and h:
            existing_input_hashes.add(h)

        ctype = obj.get("candidate_type")
        stmt = obj.get("statement")
        if isinstance(ctype, str) and isinstance(stmt, str):
            stmt_norm = stmt.strip()
            if stmt_norm:
                existing_statements.add((ctype, stmt_norm))

    return existing_input_hashes, existing_statements


def extract_candidates(user_id: str, episode_path: Path, episode: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extremely conservative v0 extraction:
    - Only extract psychological_status as candidate
    - Confidence intentionally moderate
    - Salience intentionally low (can evolve later)
    """

    meta = episode.get("meta") or {}
    psych = episode.get("psychological_status") or ""
    date = episode.get("date")

    if not isinstance(psych, str) or not psych.strip():
        return []

    psych_str = psych.strip()
    input_hash = meta.get("input_hash")

    candidate = {
        "memory_id": str(uuid.uuid4()),
        "ts_generated": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "source_episode_date": date,
        "source_episode_path": str(episode_path.relative_to(BASE_DIR)),
        "source_input_hash": input_hash,
        "candidate_type": "psychological_state_snapshot",
        "statement": psych_str,
        "evidence": {"psychological_status": psych_str},
        "confidence": 0.6,
        "salience": 0.3,
        "status": "candidate",
    }

    return [candidate]


def append_memory(memory_file: Path, entries: List[Dict[str, Any]]) -> None:
    with open(memory_file, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run() -> None:
    if not EPISODES_DIR.exists():
        print("[memory_builder] no episodes directory found")
        return

    users_processed = 0
    entries_written = 0
    entries_skipped_statement_dup = 0

    for user_dir in EPISODES_DIR.iterdir():
        if not user_dir.is_dir():
            continue

        user_id = user_dir.name
        memory_user_dir = MEMORY_DIR / user_id
        ensure_dir(memory_user_dir)

        memory_file = memory_user_dir / "memory_v0.jsonl"
        existing_hashes, existing_statements = load_existing_dedup_sets(memory_file)

        for episode_file in sorted(user_dir.glob("*.json")):
            episode = load_json(episode_file)
            meta = episode.get("meta") or {}
            input_hash = meta.get("input_hash")

            # Idempotence-by-episode
            if not isinstance(input_hash, str) or not input_hash:
                continue
            if input_hash in existing_hashes:
                continue

            candidates = extract_candidates(user_id, episode_file, episode)
            if not candidates:
                continue

            # NEW: statement-level dedup (append-only: we simply skip writing redundant entries)
            filtered: List[Dict[str, Any]] = []
            for c in candidates:
                ctype = c.get("candidate_type")
                stmt = c.get("statement")
                if not isinstance(ctype, str) or not isinstance(stmt, str):
                    continue
                stmt_norm = stmt.strip()
                key = (ctype, stmt_norm)
                if key in existing_statements:
                    entries_skipped_statement_dup += 1
                    continue
                filtered.append(c)
                existing_statements.add(key)

            if filtered:
                append_memory(memory_file, filtered)
                entries_written += len(filtered)

            # After processing this episode, we can mark its input_hash as seen
            existing_hashes.add(input_hash)

        users_processed += 1

    print(
        f"[memory_builder] done | users={users_processed} entries_written={entries_written} "
        f"skipped_statement_dup={entries_skipped_statement_dup}"
    )


if __name__ == "__main__":
    run()
