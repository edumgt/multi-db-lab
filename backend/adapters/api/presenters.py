"""
프리젠터 — 도메인 엔티티를 HTTP 응답 스키마로 변환합니다.

[Clean Architecture 적용 사례 — Interface Adapter(Presenter)]
  유스케이스는 `LabRecord` 를 돌려주고 "source 가 무엇인지" 조차 응답에 어떻게 넣을지 모릅니다.
  응답 모양(필드명, 중첩 구조) 을 바꾸고 싶으면 이 파일만 고치면 됩니다.

[Python 중급 적용 사례 — 타입 힌트]
  `Iterable[LabRecord]` 를 받으면 list · tuple · generator 어느 것이든 넘길 수 있습니다.
  반환은 구체 타입 `list[...]` 로 명시해 호출자가 len() 등을 안전하게 쓰게 합니다.
"""

from __future__ import annotations

from typing import Iterable

from backend.adapters.api.schemas.employee import EmployeeRead
from backend.adapters.api.schemas.lab import (
    GraphAnalysisResponse,
    LabRecordRead,
    NodeScoreRead,
    VectorMatchRead,
    VectorQueryResponse,
)
from backend.adapters.api.schemas.post import PostListResponse, PostOut
from backend.domain.entities import Employee, LabRecord, NodeScore, Post, PostPage, VectorMatch


def lab_record(record: LabRecord, *, source: str) -> LabRecordRead:
    return LabRecordRead(id=record.id, title=record.title, content=record.content, tags=list(record.tags), source=source)


def lab_records(records: Iterable[LabRecord], *, source: str) -> list[LabRecordRead]:
    return [lab_record(r, source=source) for r in records]


def employee(entity: Employee) -> EmployeeRead:
    return EmployeeRead(id=entity.id, name=entity.name, position=entity.position)


def post(entity: Post) -> PostOut:
    return PostOut(
        id=entity.id,
        title=entity.title,
        content=entity.content,
        views=entity.views,
        owner=entity.owner_name,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def post_page(page: PostPage) -> PostListResponse:
    return PostListResponse(items=[post(p) for p in page.items], total=page.total)


def vector_matches(matches: Iterable[VectorMatch], *, provider: str) -> VectorQueryResponse:
    return VectorQueryResponse(
        provider=provider,
        matches=[VectorMatchRead(id=m.id, score=m.score, payload=dict(m.payload)) for m in matches],
    )


def graph_analysis(scores: Iterable[NodeScore], *, algorithm: str) -> GraphAnalysisResponse:
    return GraphAnalysisResponse(algorithm=algorithm, top_nodes=[NodeScoreRead(id=s.id, score=s.score) for s in scores])
