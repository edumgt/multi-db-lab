"""
usecases 패키지 — Application Business Rules (Clean Architecture 의 두 번째 원).

[Clean Architecture 적용 사례 — Use Case 와 Interface Adapter 의 구분]
  Use Case 는 "애플리케이션이 하는 일" 을 하나의 클래스로 표현합니다.
    - 입력: 원시 타입 또는 도메인 값 객체 (pydantic 모델 ✗, Request 객체 ✗)
    - 출력: 도메인 엔티티 (JSON ✗, HTTP 응답 ✗)
    - 협력자: domain/ports.py 의 추상 인터페이스 (구현체 ✗)
  Interface Adapter(라우터)는 HTTP ↔ 유스케이스 입력/출력을 번역만 합니다.

  이렇게 나누면:
    * 유스케이스를 DB 없이 단위 테스트할 수 있습니다 (tests/ 의 InMemory 구현 참고).
    * 같은 유스케이스를 7 개 DB 라우터가 공유합니다 (LabRecordUseCase 하나로 7 × 4 = 28 엔드포인트 처리).

[Clean Architecture 적용 사례 — 의존성 방향]
  usecases → domain 만 import 합니다. adapters/infrastructure/fastapi 는 import 하지 않습니다.
"""

from backend.usecases.auth_usecase import AuthUseCase
from backend.usecases.employee_usecase import EmployeeUseCase
from backend.usecases.graph_usecase import GraphUseCase
from backend.usecases.lab_record_usecase import LabRecordUseCase
from backend.usecases.post_usecase import PostUseCase
from backend.usecases.vector_usecase import VectorUseCase

__all__ = [
    "AuthUseCase",
    "EmployeeUseCase",
    "GraphUseCase",
    "LabRecordUseCase",
    "PostUseCase",
    "VectorUseCase",
]
