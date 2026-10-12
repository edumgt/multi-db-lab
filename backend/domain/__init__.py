"""
domain 패키지 — Clean Architecture 의 가장 안쪽 원(Enterprise Business Rules).

[Clean Architecture 적용 사례 — 의존성 방향]
  이 패키지는 *어떤 외부 패키지도 import 하지 않습니다.*
  (FastAPI · SQLAlchemy · pymongo · redis 등 프레임워크/드라이버 금지)
  오직 표준 라이브러리(dataclasses, abc, typing)만 사용합니다.

  바깥 계층(usecases → adapters → infrastructure)은 모두 이 패키지를 import 할 수 있지만,
  이 패키지는 바깥 계층을 절대 import 하지 않습니다. 이것이 "의존성 규칙(Dependency Rule)" 입니다.

구성:
  entities.py    — 순수 Python dataclass 로 표현한 도메인 엔티티
  exceptions.py  — 도메인 전용 예외 계층 (HTTP 상태코드를 모른다)
  ports.py       — 추상 인터페이스(ABC). 바깥 계층이 구현해야 할 "계약"
"""

from backend.domain import entities, exceptions, ports

__all__ = ["entities", "exceptions", "ports"]
