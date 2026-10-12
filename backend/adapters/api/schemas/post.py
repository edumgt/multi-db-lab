from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=5000)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, min_length=1, max_length=5000)


class PostOut(BaseModel):
    id: int
    title: str
    content: str
    views: int
    owner: str
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    items: list[PostOut]
    total: int
