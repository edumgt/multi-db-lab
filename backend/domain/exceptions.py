"""
도메인 예외 계층.

[Python 중급 적용 사례 — 예외 처리]
  * 사용자 정의 예외는 "의미 있는 계층" 으로 설계합니다.
        DomainError
        ├── NotFoundError            (404 로 번역됨)
        ├── ValidationError          (400)
        ├── PermissionDeniedError    (403)
        ├── AuthenticationError      (401)
        ├── ConfigurationError       (400 — 환경변수 누락 등 운영자 실수)
        ├── UnsupportedProviderError (400)
        └── ExternalServiceError     (502 — DB/외부 API 장애를 감싼 예외)
    바깥 계층은 가장 구체적인 예외를 잡을 수도, `except DomainError` 로 한 번에 잡을 수도 있습니다.

  * 예외 객체에 `detail` 속성을 두어 메시지를 구조적으로 보관합니다.
    (문자열만 넘기면 `str(exc)` 로 꺼내야 하고, 다국어/코드 추가가 어렵습니다.)

[Clean Architecture 적용 사례 — 의존성 방향]
  * 여기에는 HTTP 상태코드가 *없습니다.* 404/403 으로 바꾸는 일은 Interface Adapter 계층
    (backend/adapters/api/error_handlers.py) 의 책임입니다.
    덕분에 같은 유스케이스를 CLI · gRPC · 배치 작업에서도 재사용할 수 있습니다.
  * 과거 코드는 services/post_service.py 에서 `fastapi.HTTPException` 을 직접 던졌습니다.
    → 비즈니스 계층이 웹 프레임워크에 의존하는 "의존성 역전 위반" 이었고, 이번 고도화에서 제거했습니다.
"""

from __future__ import annotations


class DomainError(Exception):
    """모든 도메인 예외의 루트. `detail` 은 사람이 읽을 메시지."""

    default_detail: str = "요청을 처리할 수 없습니다."

    def __init__(self, detail: str | None = None) -> None:
        # 서브클래스가 default_detail 만 바꿔도 메시지가 바뀌도록 클래스 속성을 활용합니다.
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(DomainError):
    default_detail = "리소스를 찾을 수 없습니다."


class ValidationError(DomainError):
    default_detail = "요청 값이 올바르지 않습니다."


class PermissionDeniedError(DomainError):
    default_detail = "권한이 없습니다."


class AuthenticationError(DomainError):
    default_detail = "인증 정보가 유효하지 않습니다."


class ConfigurationError(DomainError):
    default_detail = "필요한 설정(환경변수)이 없습니다."


class UnsupportedProviderError(DomainError):
    default_detail = "지원하지 않는 provider 입니다."


class ExternalServiceError(DomainError):
    """DB · 외부 API 호출 실패를 감쌉니다.

    게이트웨이는 드라이버 고유 예외(PyMongoError, RedisError …)를 잡아 이 예외로 *변환* 합니다.
    `raise ExternalServiceError(...) from exc` 처럼 원인 예외를 체이닝(__cause__)해 두면
    로그에서 원래 스택을 추적할 수 있습니다.
    """

    default_detail = "외부 저장소 호출에 실패했습니다."

    def __init__(self, detail: str | None = None, *, service: str = "unknown") -> None:
        self.service = service
        super().__init__(detail)
