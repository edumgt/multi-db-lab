"""
인증 컨트롤러 — /api/auth/*

[Clean Architecture 적용 사례 — Interface Adapter(Controller)]
  라우터 함수 본문은 2~3 줄입니다: (1) 요청 스키마에서 값 꺼내기 (2) 유스케이스 호출 (3) 응답 스키마로 포장.
  비즈니스 판단(비밀번호 일치 여부, 사용자 존재 여부) 은 전부 AuthUseCase 안에 있습니다.
  과거 auth_router.py 는 UserRepository 를 직접 만들고 verify_password 를 호출했습니다 — 컨트롤러가
  유스케이스 역할까지 하던 것을 분리했습니다.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.adapters.api.deps import AuthUC, CurrentUser
from backend.adapters.api.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, auth: AuthUC) -> LoginResponse:
    token = auth.login(payload.username, payload.password)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(id=current_user.id, username=current_user.username)
