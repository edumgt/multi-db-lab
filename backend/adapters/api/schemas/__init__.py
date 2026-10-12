"""
pydantic 스키마 — HTTP 요청/응답 전용 데이터 모양.

[Clean Architecture 적용 사례 — 계층 분리]
  과거 backend/models/ 에 ORM 모델(User, Post) 과 pydantic 스키마가 섞여 있었습니다.
  이제 pydantic 은 "HTTP 경계" 의 것이므로 adapters/api 아래로, ORM 은 infrastructure 로 옮겼습니다.
  도메인 엔티티(domain/entities.py) 는 둘 다 모릅니다.
"""

from backend.adapters.api.schemas.auth import LoginRequest, LoginResponse, UserResponse
from backend.adapters.api.schemas.employee import EmployeeCreate, EmployeeRead
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
from backend.adapters.api.schemas.post import PostCreate, PostListResponse, PostOut, PostUpdate

__all__ = [
    "EmployeeCreate",
    "EmployeeRead",
    "GraphAnalysisRequest",
    "GraphAnalysisResponse",
    "GraphEdgeCreate",
    "GraphNodeCreate",
    "LabRecordCreate",
    "LabRecordRead",
    "LabRecordUpdate",
    "LoginRequest",
    "LoginResponse",
    "PostCreate",
    "PostListResponse",
    "PostOut",
    "PostUpdate",
    "UserResponse",
    "VectorQueryRequest",
    "VectorQueryResponse",
    "VectorUpsertRequest",
    "VectorUpsertResponse",
]
