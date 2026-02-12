"""
Layer 3 — Memory Construction v0 (append-only, reversible)

Properties:
- File-based (no DB/schema changes)
- Append-only JSONL ledger per user
- Weak-signal, confidence-weighted
- Evidence pointers to episode artifacts
- Re-runs are idempotent per episode input_hash
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[1]
EPISODES_DIR = BASE_DIR / "logs" / "episodes"
MEMORY_DIR = BASE_DIR / "logs" / "memory"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def load_existing_hashes(memory_file: Path):
    if not memory_file.exists():
        return set()

    hashes = set()
    with open(memory_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                h = obj.get("source_input_hash")
                if h:
                    hashes.add(h)
            except Exception:
                continue
    return hashes


def extract_candidates(user_id: str, episode_path: Path, episode: dict):
    """
    Extremely conservative v0 extraction:
    - Only extract psychological_status as candidate
    - Confidence intentionally moderate
    - Salience low (can evolve later)
    """

    meta = episode.get("meta") or {}
    psych = episode.get("psychological_status") or ""
    date = episode.get("date")

    if not psych:
        return []

    candidate = {
        "memory_id": str(uuid.uuid4()),
        "ts_generated": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "source_episode_date": date,
        "source_episode_path": str(episode_path.relative_to(BASE_DIR)),
        "source_input_hash": meta.get("input_hash"),
        "candidate_type": "psychological_state_snapshot",
        "statement": psych.strip(),
        "evidence": {
            "psychological_status": psych.strip()
        },
        "confidence": 0.6,
        "salience": 0.3,
        "status": "candidate"
    }

    return [candidate]


def append_memory(memory_file: Path, entries):
    with open(memory_file, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run():
    if not EPISODES_DIR.exists():
        print("[memory_builder] no episodes directory found")
        return

    users_processed = 0
    entries_written = 0

    for user_dir in EPISODES_DIR.iterdir():
        if not user_dir.is_dir():
            continue

        user_id = user_dir.name
        memory_user_dir = MEMORY_DIR / user_id
        ensure_dir(memory_user_dir)

        memory_file = memory_user_dir / "memory_v0.jsonl"
        existing_hashes = load_existing_hashes(memory_file)

        for episode_file in sorted(user_dir.glob("*.json")):
            episode = load_json(episode_file)
            input_hash = (episode.get("meta") or {}).get("input_hash")

            if not input_hash:
                continue

            if input_hash in existing_hashes:
                continue

            candidates = extract_candidates(user_id, episode_file, episode)
            if candidates:
                append_memory(memory_file, candidates)
                entries_written += len(candidates)

        users_processed += 1

    print(
        f"[memory_builder] done | users={users_processed} entries_written={entries_written}"
    )


if __name__ == "__main__":
    run()
