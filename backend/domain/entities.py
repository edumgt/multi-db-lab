"""
도메인 엔티티 — 프레임워크에 독립적인 순수 Python 자료구조.

[Python 중급 적용 사례 — 클래스]
  * `@dataclass(frozen=True, slots=True)`
      - frozen=True : 생성 후 변경 불가(불변 객체). 여러 계층을 오가며 실수로 수정되는 것을 막습니다.
      - slots=True  : __dict__ 대신 슬롯을 사용해 메모리를 절약하고 오타 속성 대입을 차단합니다.
  * `field(default_factory=list)` : 가변 기본값(list) 을 안전하게 지정하는 방법.
  * `replace()` (dataclasses.replace) 를 사용해 불변 객체의 "수정본"을 만듭니다.

[Python 중급 적용 사례 — 타입 힌트]
  * `from __future__ import annotations` : 애너테이션을 문자열로 지연 평가 → 순환 참조/전방 참조 문제 해결.
  * `Literal[...]` : 허용되는 문자열 값을 타입 수준에서 제한.
  * `TypeAlias` / `type` 문 : 반복되는 복합 타입에 이름을 부여.
  * `Mapping[str, Any]` : "읽기 전용 dict" 라는 의도를 드러내는 타입.

[Clean Architecture 적용 사례 — 계층 분리]
  * Pydantic 요청/응답 스키마(adapters/api/schemas) 와 SQLAlchemy ORM 모델(infrastructure/orm) 은
    여기 없습니다. 엔티티는 "비즈니스가 다루는 개념" 만 표현하고, 직렬화·영속화 방식은 모릅니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Literal, Mapping

# ---------------------------------------------------------------------------
# 타입 별칭 (Python 3.12 의 `type` 문 — PEP 695)
# ---------------------------------------------------------------------------
# 게시글 정렬 키. 라우터(Query 파라미터) · 유스케이스 · 리포지토리가 모두 같은 별칭을 공유해
# 문자열 오타를 컴파일 타임(정적 분석) 에 잡을 수 있습니다.
type PostSortKey = Literal["created_at:desc", "views:desc", "id:desc", "id:asc"]

# 그래프 분석 알고리즘.
type GraphAlgorithm = Literal["pagerank", "degree"]

# 벡터 DB 메타데이터. "JSON 으로 직렬화 가능한 dict" 라는 의도를 이름으로 표현.
type JsonObject = Mapping[str, Any]


# ---------------------------------------------------------------------------
# Lab 레코드 (MongoDB · PostgreSQL · Supabase · Redis · OpenSearch · ClickHouse · Cassandra 공통)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class LabRecord:
    """7 개 저장소가 공통으로 다루는 실습용 레코드.

    어느 DB 에 저장되든 동일한 모양이므로, 유스케이스는 저장소 종류를 몰라도 됩니다.
    """

    id: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON/문서형 DB 에 넣기 좋은 평범한 dict 로 변환합니다.

        [JSON 처리] `dataclasses.asdict` 대신 명시적으로 작성해, 어떤 필드가 외부로 나가는지
        한눈에 보이게 했습니다. tags 는 복사본(list(...))을 넘겨 외부 수정이 엔티티에 전파되지 않게 합니다.
        """
        return {"id": self.id, "title": self.title, "content": self.content, "tags": list(self.tags)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> LabRecord:
        """DB 드라이버가 돌려준 dict/row 를 엔티티로 변환합니다.

        [예외 처리] 필수 키가 없으면 KeyError 가 그대로 올라오게 두지 않고,
        호출한 게이트웨이가 ExternalServiceError 로 감싸도록 합니다(게이트웨이 참고).
        [타입 힌트] `Mapping` 을 받으므로 dict, RowMapping, pymongo 문서 등 어떤 매핑이든 허용.
        """
        return cls(
            id=str(raw["id"]),
            title=str(raw["title"]),
            content=str(raw["content"]),
            tags=[str(tag) for tag in (raw.get("tags") or [])],
        )

    def apply(self, patch: LabRecordPatch) -> LabRecord:
        """불변 객체이므로 '수정' 은 새 객체를 돌려주는 방식으로 표현합니다."""
        return replace(self, **patch.changes())


@dataclass(frozen=True, slots=True)
class LabRecordPatch:
    """부분 수정(PATCH) 요청을 표현하는 값 객체.

    `None` 은 "변경하지 않음" 을 뜻합니다. 유스케이스는 `is_empty()` 로 '수정할 것이 없는 요청' 을
    검출해 ValidationError 를 던집니다 — 이 규칙이 라우터가 아닌 도메인/유스케이스에 있어야
    7 개 DB 라우터에서 같은 검사를 복붙하지 않게 됩니다.
    """

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None

    def changes(self) -> dict[str, Any]:
        """None 이 아닌 필드만 모아 dict 로 돌려줍니다 (각 DB 의 partial update 에 그대로 사용)."""
        return {
            key: value
            for key, value in (("title", self.title), ("content", self.content), ("tags", self.tags))
            if value is not None
        }

    def is_empty(self) -> bool:
        return not self.changes()


# ---------------------------------------------------------------------------
# Employee (DynamoDB)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Employee:
    id: str
    name: str
    position: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "position": self.position}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Employee:
        return cls(id=str(raw["id"]), name=str(raw["name"]), position=str(raw.get("position", "")))


# ---------------------------------------------------------------------------
# User / Post (PostgreSQL ORM 과 분리된 도메인 표현)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str
    password_hash: str


@dataclass(frozen=True, slots=True)
class Post:
    id: int
    title: str
    content: str
    views: int
    owner_id: int
    owner_name: str
    created_at: datetime
    updated_at: datetime

    def is_owned_by(self, user: User) -> bool:
        """'본인 글인가?' 라는 비즈니스 규칙을 엔티티 메서드로 표현합니다."""
        return self.owner_id == user.id


@dataclass(frozen=True, slots=True)
class PostPage:
    """목록 조회 결과(페이지). 제네릭 Page[T] 로 일반화할 수도 있지만 실습 범위에서는 구체 타입으로 둡니다."""

    items: list[Post]
    total: int


# ---------------------------------------------------------------------------
# Vector / Graph
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class VectorMatch:
    """벡터 유사도 검색의 한 건. provider 마다 score/distance 의미가 달라 extra 로 원본을 보존합니다."""

    id: str
    score: float | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    label: str = "Entity"


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class NodeScore:
    id: str
    score: float
