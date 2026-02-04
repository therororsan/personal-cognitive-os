import json
import secrets
import uuid
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session


import os
from fastapi import Header, HTTPException

PCO_API_KEY = os.getenv("PCO_API_KEY")

def require_api_key(x_api_key: str = Header(default=None)):
    if not PCO_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != PCO_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import ApiKey, Episode, InsightArtifact, RawEvent, User
from app.schemas import BootstrapRequest, BootstrapResponse, InsightOut, RawEventCreate, RawEventOut

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/protected", dependencies=[Depends(require_api_key)])
def protected():
    return {"status": "ok"}



@app.post("/v1/admin/bootstrap", response_model=BootstrapResponse)
def bootstrap(payload: BootstrapRequest, db: Session = Depends(get_db)):
    if not settings.dev_only_bootstrap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    email = payload.email or f"dev+{uuid.uuid4()}@example.com"
    user = User(email=email)
    db.add(user)
    db.flush()

    key_value = secrets.token_urlsafe(32)
    api_key = ApiKey(user_id=user.id, key=key_value)
    db.add(api_key)
    db.commit()

    return BootstrapResponse(user_id=user.id, api_key=key_value)


@app.post("/v1/raw-events", response_model=RawEventOut)
def create_raw_event(
    payload: RawEventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_event = RawEvent(user_id=user.id, source=payload.source, text=payload.text)
    db.add(raw_event)
    db.commit()
    db.refresh(raw_event)
    return RawEventOut(
        id=raw_event.id,
        source=raw_event.source,
        text=raw_event.text,
        created_at=raw_event.created_at,
    )


@app.get("/v1/insights/latest", response_model=InsightOut)
def get_latest_insight(
    kind: str = "daily_digest",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(InsightArtifact)
        .where(InsightArtifact.user_id == user.id, InsightArtifact.kind == kind)
        .order_by(InsightArtifact.created_at.desc())
        .limit(1)
    )
    insight = db.execute(stmt).scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No insights found")

    return InsightOut(
        id=insight.id,
        kind=insight.kind,
        content_md=insight.content_md,
        created_at=insight.created_at,
    )


@app.get("/v1/export")
def export_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_events = db.execute(select(RawEvent).where(RawEvent.user_id == user.id)).scalars().all()
    episodes = db.execute(select(Episode).where(Episode.user_id == user.id)).scalars().all()

    lines = []
    for item in raw_events:
        lines.append(
            json.dumps(
                {
                    "type": "raw_event",
                    "id": str(item.id),
                    "source": item.source,
                    "text": item.text,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "digest_included_at": item.digest_included_at.isoformat()
                    if item.digest_included_at
                    else None,
                }
            )
        )
    for item in episodes:
        lines.append(
            json.dumps(
                {
                    "type": "episode",
                    "id": str(item.id),
                    "title": item.title,
                    "content": item.content,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
            )
        )

    body = "\n".join(lines)
    return Response(content=body, media_type="text/plain")
