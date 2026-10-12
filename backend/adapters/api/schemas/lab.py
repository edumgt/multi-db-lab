"""
Lab(멀티 DB · 벡터 · 그래프) 요청/응답 스키마.

[Clean Architecture 적용 사례 — Interface Adapter]
  요청 스키마의 `to_entity()` / `to_patch()` 가 "HTTP 모양 → 도메인 모양" 변환을 맡습니다.
  응답은 presenters.py 가 "도메인 모양 → HTTP 모양" 으로 바꿉니다. 라우터는 두 변환을 호출만 합니다.

[Python 중급 적용 사례 — 타입 힌트]
  * `Literal["pagerank", "degree"]` 를 도메인의 GraphAlgorithm 별칭으로 재사용해 두 계층의 허용 값이 어긋나지 않게 합니다.
  * `Field(ge=1, le=20)` : 숫자 범위 제약도 타입 선언 옆에 둡니다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.domain.entities import GraphAlgorithm, GraphEdge, GraphNode, LabRecord, LabRecordPatch


class LabRecordCreate(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    def to_entity(self) -> LabRecord:
        return LabRecord(id=self.id, title=self.title, content=self.content, tags=list(self.tags))


class LabRecordUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None

    def to_patch(self) -> LabRecordPatch:
        return LabRecordPatch(title=self.title, content=self.content, tags=self.tags)


class LabRecordRead(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str]
    source: str


class VectorUpsertRequest(BaseModel):
    id: str = Field(min_length=1)
    values: list[float] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorUpsertResponse(BaseModel):
    provider: str
    status: str = "upserted"
    id: str


class VectorQueryRequest(BaseModel):
    values: list[float] = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class VectorMatchRead(BaseModel):
    id: str
    score: float | None
    payload: dict[str, Any]


class VectorQueryResponse(BaseModel):
    provider: str
    matches: list[VectorMatchRead]


class GraphNodeCreate(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(default="Entity", min_length=1)

    def to_entity(self) -> GraphNode:
        return GraphNode(id=self.id, label=self.label)


class GraphEdgeCreate(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    weight: float = 1.0

    def to_entity(self) -> GraphEdge:
        return GraphEdge(source=self.source, target=self.target, weight=self.weight)


class GraphAnalysisRequest(BaseModel):
    algorithm: GraphAlgorithm = "pagerank"


class NodeScoreRead(BaseModel):
    id: str
    score: float


class GraphAnalysisResponse(BaseModel):
    algorithm: str
    top_nodes: list[NodeScoreRead]
