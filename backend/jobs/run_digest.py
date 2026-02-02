from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Episode, InsightArtifact, RawEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def main() -> None:
    run_ts = _utc_now()

    db = SessionLocal()
    try:
        # Deterministic ordering: user_id then id.
        raw_events = (
            db.execute(
                select(RawEvent)
                .where(RawEvent.digest_included_at.is_(None))
                .order_by(RawEvent.user_id, RawEvent.id)
            )
            .scalars()
            .all()
        )

        if not raw_events:
            print(f"[run_digest] nothing to do (no new raw events) @ {run_ts.isoformat()}")
            return

        # Group deterministically (raw_events is already ordered).
        events_by_user: dict[str, list[RawEvent]] = {}
        for evt in raw_events:
            events_by_user.setdefault(str(evt.user_id), []).append(evt)

        user_ids = sorted(events_by_user.keys())

        total_insights = 0
        total_marked = 0
        total_new_episodes = 0

        for user_id in user_ids:
            user_events = events_by_user[user_id]

            existing_episode = (
                db.execute(select(Episode).where(Episode.user_id == user_id).limit(1))
                .scalars()
                .first()
            )

            # Minimal guardrail: if a user has no Episode yet, create placeholder episodes.
            if not existing_episode:
                for evt in user_events:
                    episode = Episode(
                        user_id=user_id,
                        title="Placeholder Episode",
                        content=evt.text,
                    )
                    db.add(episode)
                    total_new_episodes += 1

            summary_lines = [
                "# Daily Digest",
                f"Generated: {run_ts.isoformat()}",
                "",
                f"Events included: {len(user_events)}",
                "",
                "## Sources",
            ]

            # Dedupe sources but keep a stable order.
            sources = _dedupe_preserve_order([evt.source for evt in user_events])
            summary_lines.extend([f"- {src}" for src in sources])

            insight = InsightArtifact(
                user_id=user_id,
                kind="daily_digest",
                content_md="\n".join(summary_lines),
            )
            db.add(insight)
            total_insights += 1

            # Mark included with a single run timestamp.
            for evt in user_events:
                evt.digest_included_at = run_ts
                total_marked += 1

            print(
                f"[run_digest] user_id={user_id}: events={len(user_events)} "
                f"episodes_created={'yes' if not existing_episode else 'no'}"
            )

        db.commit()
        print(
            f"[run_digest] done @ {run_ts.isoformat()} | "
            f"users={len(user_ids)} insights={total_insights} "
            f"events_marked={total_marked} episodes_created={total_new_episodes}"
        )
    except Exception as e:
        db.rollback()
        print(f"[run_digest] ERROR: {e.__class__.__name__}: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
