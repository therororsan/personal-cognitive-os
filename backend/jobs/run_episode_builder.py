from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import InsightArtifact, RawEvent


@dataclass(frozen=True)
class EpisodeInput:
    date_str: str
    digest_content: str | None
    events: list[RawEvent]


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _local_date() -> date:
    return _local_now().date()


def _local_tzinfo():
    return _local_now().tzinfo


def _episodes_dir() -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    return base_dir / "logs" / "episodes"


def _episode_path(user_id: str, date_str: str) -> Path:
    return _episodes_dir() / user_id / f"{date_str}.json"


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    tz = _local_tzinfo() or timezone.utc
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _load_existing_episode(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _compute_input_hash(inputs: EpisodeInput) -> str:
    parts: list[str] = [
        f"date:{inputs.date_str}",
        f"digest:{inputs.digest_content or ''}",
    ]

    for evt in inputs.events:
        parts.append(
            "|".join(
                [
                    str(evt.id),
                    evt.created_at.isoformat() if evt.created_at else "",
                    evt.source,
                    evt.text,
                ]
            )
        )

    payload = "\n".join(parts)
    return sha256(payload.encode("utf-8")).hexdigest()


def _build_recap(events: list[RawEvent], digest_content: str | None) -> str:
    snippets: list[str] = []
    for evt in events[:5]:
        text = _clean_text(evt.text)[:180]
        if text:
            snippets.append(text)

    digest_snippet = ""
    if digest_content:
        lines = [
            ln.strip()
            for ln in digest_content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if lines:
            digest_snippet = " ".join(lines[:2])

    if not snippets:
        return "No captured events for the day."

    recap = " / ".join(snippets)
    if digest_snippet:
        recap = f"{digest_snippet} Key events: {recap}"
    else:
        recap = f"Key events: {recap}"

    return recap


def _score_keywords(text: str, keywords: list[str]) -> int:
    score = 0
    for kw in keywords:
        if kw in text:
            score += 1
    return score


def _build_psychological_status(events: list[RawEvent]) -> str:
    corpus = " ".join(_clean_text(evt.text).lower() for evt in events)

    stress_keywords = ["stress", "stressed", "anxious", "overwhelmed", "tense", "worried"]
    energy_low_keywords = ["tired", "exhausted", "fatigued", "sleepy", "drained"]
    energy_high_keywords = ["energized", "energetic", "focused", "motivated"]
    clarity_low_keywords = ["confused", "unclear", "foggy", "scattered"]
    clarity_high_keywords = ["clear", "clarity", "focused", "decisive"]

    stress_score = _score_keywords(corpus, stress_keywords)
    energy_low = _score_keywords(corpus, energy_low_keywords)
    energy_high = _score_keywords(corpus, energy_high_keywords)
    clarity_low = _score_keywords(corpus, clarity_low_keywords)
    clarity_high = _score_keywords(corpus, clarity_high_keywords)

    if stress_score >= 2:
        stress = "elevated"
    elif stress_score == 1:
        stress = "mild"
    else:
        stress = "steady"

    if energy_high > energy_low:
        energy = "higher"
    elif energy_low > energy_high:
        energy = "lower"
    else:
        energy = "mixed"

    if clarity_high > clarity_low:
        clarity = "clearer"
    elif clarity_low > clarity_high:
        clarity = "foggy"
    else:
        clarity = "mixed"

    return (
        "Non-therapeutic, text-only readout: "
        f"stress={stress}, energy={energy}, clarity={clarity}."
    )


def _build_actionable_advice(events: list[RawEvent]) -> list[str]:
    corpus = " ".join(_clean_text(evt.text).lower() for evt in events)

    actions: list[str] = []

    if any(kw in corpus for kw in ["stress", "stressed", "overwhelmed", "anxious"]):
        actions.extend(
            [
                "Block a 10–20 min decompression window.",
                "Pick the single most important task for tomorrow and commit to it.",
            ]
        )

    if any(kw in corpus for kw in ["tired", "exhausted", "fatigued", "sleepy"]):
        actions.extend(
            [
                "Protect a consistent sleep window tonight.",
                "Plan a lighter first hour tomorrow (low-cognitive load).",
            ]
        )

    if any(kw in corpus for kw in ["confused", "unclear", "foggy", "scattered"]):
        actions.extend(
            [
                "Write a 3-line brief: goal, next step, and success criteria.",
                "Break the next task into a 10-minute starter step.",
            ]
        )

    actions.extend(
        [
            "Review open loops and capture any missing items.",
            "Prep the first action for tomorrow (materials, links, files).",
        ]
    )

    actions = _dedupe_preserve_order(actions)
    if len(actions) > 7:
        actions = actions[:7]
    if len(actions) < 3:
        actions.extend(
            [
                "Identify one risk to watch tomorrow.",
                "Set a realistic end-of-day stop time.",
            ]
        )
        actions = _dedupe_preserve_order(actions)[:3]

    return actions


def _build_episode_payload(inputs: EpisodeInput, run_ts: datetime) -> dict:
    recap = _build_recap(inputs.events, inputs.digest_content)
    psychological_status = _build_psychological_status(inputs.events)
    actionable_advice = _build_actionable_advice(inputs.events)

    latest_event_at = None
    if inputs.events:
        latest_event_at = max(evt.created_at for evt in inputs.events if evt.created_at)

    input_hash = _compute_input_hash(inputs)

    return {
        "date": inputs.date_str,
        "recap": recap,
        "psychological_status": psychological_status,
        "actionable_advice": actionable_advice,
        "meta": {
            "generated_at": run_ts.isoformat(),
            "input_hash": input_hash,
            "event_count": len(inputs.events),
            "source_latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
            "digest_included": bool(inputs.digest_content),
        },
    }


def _get_daily_digest(
    db: SessionLocal,
    user_id: str,
    start_utc: datetime,
    end_utc: datetime,
) -> str | None:
    stmt = (
        select(InsightArtifact)
        .where(
            InsightArtifact.user_id == user_id,
            InsightArtifact.kind == "daily_digest",
            InsightArtifact.created_at >= start_utc,
            InsightArtifact.created_at < end_utc,
        )
        .order_by(InsightArtifact.created_at.desc())
        .limit(1)
    )
    insight = db.execute(stmt).scalars().first()
    if not insight:
        return None
    return insight.content_md


def _get_daily_events(
    db: SessionLocal,
    start_utc: datetime,
    end_utc: datetime,
) -> list[RawEvent]:
    stmt = (
        select(RawEvent)
        .where(RawEvent.created_at >= start_utc, RawEvent.created_at < end_utc)
        .order_by(RawEvent.user_id, RawEvent.created_at, RawEvent.id)
    )
    return db.execute(stmt).scalars().all()


def main() -> None:
    run_ts = _local_now()
    day = _local_date()
    date_str = day.isoformat()

    start_utc, end_utc = _day_bounds_utc(day)

    db = SessionLocal()
    try:
        events = _get_daily_events(db, start_utc, end_utc)
        if not events:
            print(f"[run_episode_builder] nothing to do (no raw events for {date_str})")
            return

        # Group by user_id deterministically.
        events_by_user: dict[str, list[RawEvent]] = {}
        for evt in events:
            events_by_user.setdefault(str(evt.user_id), []).append(evt)

        user_ids = sorted(events_by_user.keys())
        total_written = 0
        total_skipped = 0

        for user_id in user_ids:
            user_events = events_by_user[user_id]
            digest_content = _get_daily_digest(db, user_id, start_utc, end_utc)

            inputs = EpisodeInput(
                date_str=date_str,
                digest_content=digest_content,
                events=user_events,
            )

            episode_path = _episode_path(user_id, date_str)
            existing = _load_existing_episode(episode_path)
            current_hash = _compute_input_hash(inputs)

            if existing and existing.get("meta", {}).get("input_hash") == current_hash:
                print(
                    f"[run_episode_builder] user_id={user_id} nothing to do "
                    f"(no new raw events since last episode for {date_str})"
                )
                total_skipped += 1
                continue

            payload = _build_episode_payload(inputs, run_ts)

            episode_path.parent.mkdir(parents=True, exist_ok=True)
            episode_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            action = "updated" if existing else "created"
            print(
                f"[run_episode_builder] user_id={user_id} {action}: "
                f"{episode_path.name} events={len(user_events)}"
            )
            total_written += 1

        print(
            f"[run_episode_builder] done | date={date_str} "
            f"users={len(user_ids)} written={total_written} skipped={total_skipped}"
        )
    except Exception as e:
        print(f"[run_episode_builder] ERROR: {e.__class__.__name__}: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
