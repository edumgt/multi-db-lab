"""
backend 패키지 — Clean Architecture 계층 구조.

    domain/          엔티티 · 도메인 예외 · 포트(ABC)            ← 아무것도 의존하지 않음
    usecases/        애플리케이션 비즈니스 규칙                   ← domain
    adapters/        게이트웨이 · 보안 · HTTP 컨트롤러/프리젠터   ← usecases, domain, (infrastructure 타입)
    infrastructure/  설정 · ORM · DB 드라이버 클라이언트           ← (domain.exceptions 만)
    main.py          조립 지점                                   ← 전부

`from backend import app` 는 하위 호환을 위해 유지합니다 (Dockerfile 은 backend.main:app 사용).
"""

from backend.main import app

__all__ = ["app"]
