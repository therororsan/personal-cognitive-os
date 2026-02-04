from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    email: Optional[str] = None


class BootstrapResponse(BaseModel):
    user_id: UUID
    api_key: str


class RawEventCreate(BaseModel):
    source: str = Field(min_length=1)
    text: str = Field(min_length=1)


class RawEventOut(BaseModel):
    id: UUID
    source: str
    text: str
    created_at: datetime


class InsightOut(BaseModel):
    id: UUID
    kind: str
    content_md: str
    created_at: datetime
