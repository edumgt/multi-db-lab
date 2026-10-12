"""
Lab 컨트롤러 — /lab/* (7 개 레코드 저장소 · 벡터 · 그래프)

[Clean Architecture 적용 사례 — Interface Adapter 의 극단적 단순화]
  과거 lab_router.py 는 약 500 줄로, 7 개 DB × 4 개 엔드포인트 = 28 개 함수에 같은 로직이 복사돼 있었습니다.
  이제 `_build_record_router(source)` 가 공통 라우터 4 개를 *한 번만* 정의하고, DB 종류는
  `Depends(get_lab_usecase(source))` 로 주입합니다. URL · 응답 모양은 이전과 100 % 동일합니다.

[Python 중급 적용 사례 — 클래스 · 함수]
  * 라우터를 만들어 돌려주는 팩토리 함수 + 클로저. source 가 각 핸들러에 캡처됩니다.
  * 중첩 함수 안에서는 `uc: LabRecordUseCase = Depends(provider)` 형태를 씁니다.
    (`from __future__ import annotations` 환경에서 함수 내부에 정의한 Annotated 별칭은 FastAPI 가
     문자열 애너테이션을 모듈 전역에서 해석하지 못해 쿼리 파라미터로 오인합니다 — 실제로 겪은 버그입니다.)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from backend.adapters.api import presenters
from backend.adapters.api.deps import LAB_REPOSITORY_FACTORIES, GraphUC, VectorUC, get_lab_usecase
from backend.adapters.api.schemas.lab import (
    GraphAnalysisRequest,
    GraphAnalysisResponse,
    GraphEdgeCreate,
    GraphNodeCreate,
    LabRecordCreate,
    LabRecordRead,
    LabRecordUpdate,
    VectorQueryRequest,
    VectorQueryResponse,
    VectorUpsertRequest,
    VectorUpsertResponse,
)
from backend.usecases import LabRecordUseCase

router = APIRouter(prefix="/lab", tags=["lab"])


def _build_record_router(source: str) -> APIRouter:
    """`/lab/{source}/records` CRUD 4 종을 가진 서브 라우터를 생성합니다."""
    sub = APIRouter(prefix=f"/{source}/records", tags=[f"lab:{source}"])
    provider = get_lab_usecase(source)

    @sub.post("", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
    def create_record(payload: LabRecordCreate, uc: LabRecordUseCase = Depends(provider)) -> LabRecordRead:
        return presenters.lab_record(uc.create(payload.to_entity()), source=uc.source)

    @sub.get("", response_model=list[LabRecordRead])
    def list_records(
        limit: Annotated[int, Query(ge=1, le=200)] = 20, uc: LabRecordUseCase = Depends(provider)
    ) -> list[LabRecordRead]:
        return presenters.lab_records(uc.list(limit), source=uc.source)

    @sub.patch("/{record_id}", response_model=LabRecordRead)
    def update_record(
        record_id: str, payload: LabRecordUpdate, uc: LabRecordUseCase = Depends(provider)
    ) -> LabRecordRead:
        return presenters.lab_record(uc.update(record_id, payload.to_patch()), source=uc.source)

    @sub.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_record(record_id: str, uc: LabRecordUseCase = Depends(provider)) -> Response:
        uc.delete(record_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return sub


# mongo · postgres · supabase · redis · opensearch · clickhouse · cassandra — 전략 테이블의 키가 곧 URL 세그먼트
for _source in LAB_REPOSITORY_FACTORIES:
    router.include_router(_build_record_router(_source))


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------
@router.post("/vector/upsert", response_model=VectorUpsertResponse)
def upsert_vector(payload: VectorUpsertRequest, vectors: VectorUC) -> VectorUpsertResponse:
    vectors.upsert(payload.id, payload.values, payload.metadata)
    return VectorUpsertResponse(provider=vectors.provider, id=payload.id)


@router.post("/vector/query", response_model=VectorQueryResponse)
def query_vector(payload: VectorQueryRequest, vectors: VectorUC) -> VectorQueryResponse:
    return presenters.vector_matches(vectors.query(payload.values, payload.top_k), provider=vectors.provider)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
@router.post("/graph/nodes", status_code=status.HTTP_201_CREATED)
def create_graph_node(payload: GraphNodeCreate, graph: GraphUC) -> dict[str, str]:
    node = graph.add_node(payload.to_entity())
    return {"id": node.id, "label": node.label}


@router.post("/graph/edges", status_code=status.HTTP_201_CREATED)
def create_graph_edge(payload: GraphEdgeCreate, graph: GraphUC) -> dict[str, object]:
    edge = graph.add_edge(payload.to_entity())
    return {"source": edge.source, "target": edge.target, "weight": edge.weight}


@router.post("/graph/analyze", response_model=GraphAnalysisResponse)
def analyze_graph(payload: GraphAnalysisRequest, graph: GraphUC) -> GraphAnalysisResponse:
    return presenters.graph_analysis(graph.analyze(payload.algorithm), algorithm=payload.algorithm)
