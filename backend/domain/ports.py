"""
포트(Port) — 바깥 계층이 구현해야 하는 추상 인터페이스 모음.

[Python 중급 적용 사례 — 추상 인터페이스]
  * `abc.ABC` + `@abstractmethod` : 구현하지 않은 메서드가 있으면 인스턴스화 시점에 TypeError 가 납니다.
        class Broken(LabRecordRepository): pass
        Broken()   # TypeError: Can't instantiate abstract class ...
    → "구현을 깜빡한 어댑터" 를 런타임 초기에 잡아냅니다.
  * `ClassVar[str]` : 인스턴스가 아닌 클래스 수준 속성(source 이름)을 타입으로 표현.
  * `Protocol` (구조적 서브타이핑) 도 선택지이지만, 여기서는 "명시적으로 상속해 계약을 선언" 하는
    교육적 효과를 위해 ABC 를 사용했습니다. Protocol 사용 예는 `Closeable` 하나만 남겨 두었습니다.

[Clean Architecture 적용 사례 — 의존성 역전(DIP)]
  * 유스케이스는 `LabRecordRepository` 라는 *추상* 에만 의존합니다.
    MongoDB 구현인지 Redis 구현인지는 조립 시점(adapters/api/deps.py) 에만 결정됩니다.
  * 포트는 "안쪽(도메인)" 이 소유합니다. 즉 인터페이스를 정의하는 쪽은 사용하는 쪽(유스케이스)이지,
    구현하는 쪽(DB 어댑터)이 아닙니다. 이것이 의존성 화살표를 안쪽으로 향하게 만드는 핵심입니다.

[Clean Architecture 적용 사례 — Use Case vs Interface Adapter 구분]
  * 포트의 메서드 시그니처는 도메인 엔티티만 주고받습니다. (dict · pydantic · ORM 객체 금지)
    → 어댑터는 "DB 모양 ↔ 엔티티 모양" 변환만 담당하고, 유스케이스는 변환을 전혀 모릅니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Protocol, Sequence, runtime_checkable

from backend.domain.entities import (
    Employee,
    GraphAlgorithm,
    GraphEdge,
    GraphNode,
    JsonObject,
    LabRecord,
    LabRecordPatch,
    NodeScore,
    Post,
    PostPage,
    PostSortKey,
    User,
    VectorMatch,
)


# ---------------------------------------------------------------------------
# Lab 레코드 저장소 (7 개 DB 가 모두 이 하나의 포트를 구현)
# ---------------------------------------------------------------------------
class LabRecordRepository(ABC):
    """LabRecord CRUD 계약.

    구현체 목록(backend/adapters/gateways/):
      MongoLabRecordRepository · PostgresLabRecordRepository · SupabaseLabRecordRepository ·
      RedisLabRecordRepository · OpenSearchLabRecordRepository · ClickHouseLabRecordRepository ·
      CassandraLabRecordRepository
    """

    #: 응답의 `source` 필드에 노출되는 저장소 이름. 각 구현체가 반드시 덮어씁니다.
    source: ClassVar[str] = "unknown"

    @abstractmethod
    def add(self, record: LabRecord) -> LabRecord:
        """레코드를 저장하고 저장된 모습을 돌려줍니다."""

    @abstractmethod
    def list(self, limit: int) -> list[LabRecord]:
        """최대 limit 건을 돌려줍니다. 정렬 보장은 구현체마다 다릅니다."""

    @abstractmethod
    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        """부분 수정. 대상이 없으면 None (유스케이스가 NotFoundError 로 변환)."""

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        """삭제 성공 여부. False 면 대상이 없었다는 뜻."""


# ---------------------------------------------------------------------------
# 벡터 저장소 (Pinecone · Weaviate · Qdrant)
# ---------------------------------------------------------------------------
class VectorStore(ABC):
    provider: ClassVar[str] = "unknown"

    @abstractmethod
    def upsert(self, vector_id: str, values: Sequence[float], metadata: JsonObject) -> None: ...

    @abstractmethod
    def query(self, values: Sequence[float], top_k: int) -> list[VectorMatch]: ...


# ---------------------------------------------------------------------------
# 그래프 저장소 (Neo4j)
# ---------------------------------------------------------------------------
class GraphStore(ABC):
    @abstractmethod
    def merge_node(self, node: GraphNode) -> GraphNode: ...

    @abstractmethod
    def merge_edge(self, edge: GraphEdge) -> GraphEdge: ...

    @abstractmethod
    def analyze(self, algorithm: GraphAlgorithm, limit: int = 10) -> list[NodeScore]: ...


# ---------------------------------------------------------------------------
# Employee (DynamoDB)
# ---------------------------------------------------------------------------
class EmployeeRepository(ABC):
    @abstractmethod
    def add(self, employee: Employee) -> None: ...

    @abstractmethod
    def find(self, employee_id: str, name: str) -> Employee | None: ...

    @abstractmethod
    def delete(self, employee_id: str, name: str) -> None: ...

    @abstractmethod
    def list_all(self) -> list[Employee]: ...


# ---------------------------------------------------------------------------
# User / Post (PostgreSQL)
# ---------------------------------------------------------------------------
class UserRepository(ABC):
    @abstractmethod
    def find_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def add(self, username: str, password_hash: str) -> User: ...


class PostRepository(ABC):
    @abstractmethod
    def find_by_id(self, post_id: int) -> Post | None: ...

    @abstractmethod
    def search(self, q: str, page: int, size: int, sort: PostSortKey) -> PostPage: ...

    @abstractmethod
    def add(self, title: str, content: str, owner_id: int) -> Post: ...

    @abstractmethod
    def update(self, post_id: int, *, title: str | None, content: str | None) -> Post: ...

    @abstractmethod
    def increment_views(self, post_id: int) -> Post: ...

    @abstractmethod
    def delete(self, post_id: int) -> None: ...


# ---------------------------------------------------------------------------
# 인증 관련 포트 — 비밀번호 해시 / 토큰 발급은 "기술 선택" 이므로 바깥으로 밀어냅니다.
# ---------------------------------------------------------------------------
class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, raw_password: str) -> str: ...

    @abstractmethod
    def verify(self, raw_password: str, password_hash: str) -> bool: ...


class TokenProvider(ABC):
    @abstractmethod
    def issue(self, subject: str) -> str:
        """subject(여기서는 username) 를 담은 토큰 문자열을 발급합니다."""

    @abstractmethod
    def subject_of(self, token: str) -> str | None:
        """토큰이 유효하면 subject, 아니면 None."""


# ---------------------------------------------------------------------------
# Protocol 예시 — 명시적 상속 없이 "close() 가 있으면 된다" 는 구조적 타입.
# ---------------------------------------------------------------------------
@runtime_checkable
class Closeable(Protocol):
    """infrastructure/clients.py 가 종료 시 자원을 정리할 때 사용합니다."""

    def close(self) -> object: ...
