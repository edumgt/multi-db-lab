"""
도메인 예외 → HTTP 응답 변환 (FastAPI exception handler).

[Clean Architecture 적용 사례 — 의존성 방향]
  도메인은 HTTP 를 모르므로, "NotFoundError 는 404" 라는 지식은 바깥(이 파일) 에만 존재합니다.
  유스케이스 7 개 · 게이트웨이 13 개 어디에도 status_code 숫자가 없습니다.

[Python 중급 적용 사례 — 예외 처리 · JSON 처리]
  * 예외 클래스 → 상태코드 매핑을 dict 로 두고 `type(exc)` 로 조회합니다.
    서브클래스 매칭이 필요하면 MRO(`type(exc).__mro__`) 를 순회해 가장 가까운 조상을 찾습니다.
  * 응답 본문은 `JSONResponse` 로 직접 만듭니다. `{"detail": ...}` 형태는 FastAPI 기본 HTTPException 과
    같은 모양이어서 프론트엔드(app.js) 가 수정 없이 동작합니다.
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.domain.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    PermissionDeniedError,
    UnsupportedProviderError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_EXCEPTION: Final[dict[type[DomainError], int]] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    ConfigurationError: status.HTTP_400_BAD_REQUEST,
    UnsupportedProviderError: status.HTTP_400_BAD_REQUEST,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    DomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def status_code_for(exc: DomainError) -> int:
    """예외 타입의 MRO 를 따라 올라가며 가장 구체적인 매핑을 찾습니다."""
    for klass in type(exc).__mro__:
        if klass in _STATUS_BY_EXCEPTION:
            return _STATUS_BY_EXCEPTION[klass]  # type: ignore[index]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    code = status_code_for(exc)
    body: dict[str, object] = {"detail": exc.detail, "error": type(exc).__name__}
    if isinstance(exc, ExternalServiceError):
        body["service"] = exc.service
        # 502 는 운영자가 봐야 하는 장애이므로 원인 예외(__cause__) 까지 스택을 남깁니다.
        logger.exception("external service failure on %s %s", request.method, request.url.path, exc_info=exc)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(status_code=code, content=body, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    """main.py 에서 한 번 호출. DomainError 루트 하나만 등록해도 모든 서브클래스가 잡힙니다."""
    app.add_exception_handler(DomainError, _domain_error_handler)  # type: ignore[arg-type]
