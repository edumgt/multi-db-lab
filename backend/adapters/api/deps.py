"""
의존성 조립(Composition Root) — "어떤 구현체를 어떤 유스케이스에 꽂을지" 를 결정하는 유일한 장소.

[Clean Architecture 적용 사례 — 의존성 방향의 '예외 지점']
  Clean Architecture 에서 모든 계층을 알아도 되는 곳은 가장 바깥의 조립 지점 하나뿐입니다.
  이 파일이 그 역할을 합니다: infrastructure(클라이언트) → adapters(게이트웨이) → usecases 순으로 조립합니다.
  라우터는 `Depends(get_lab_usecase("redis"))` 처럼 결과만 받습니다.

[Python 중급 적용 사례 — 클래스 · 타입 힌트]
  * `Callable[[], LabRecordRepository]` 팩토리를 dict 에 담아 provider 이름 → 구현체를 매핑합니다
    (if/elif 체인 대신 "전략 테이블"). 새 DB 추가 = 이 dict 에 한 줄 추가.
  * `get_lab_usecase(source)` 는 클로저를 반환하는 고차 함수입니다. FastAPI 가 호출할 수 있는
    인자 없는 함수를 동적으로 만들어 7 개 라우터 그룹에 재사용합니다.
  * `Annotated[User, Depends(get_current_user)]` 로 라우터 시그니처에서 타입과 주입을 한 번에 표현합니다.
"""

from __future__ import annotations

from typing import Annotated, Callable, Final

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.adapters.gateways.employee_dynamodb import DynamoDbEmployeeRepository
from backend.adapters.gateways.graph_neo4j import Neo4jGraphStore
from backend.adapters.gateways.lab_cassandra import CassandraLabRecordRepository
from backend.adapters.gateways.lab_clickhouse import ClickHouseLabRecordRepository
from backend.adapters.gateways.lab_mongo import MongoLabRecordRepository
from backend.adapters.gateways.lab_opensearch import OpenSearchLabRecordRepository
from backend.adapters.gateways.lab_postgres import PostgresLabRecordRepository
from backend.adapters.gateways.lab_redis import RedisLabRecordRepository
from backend.adapters.gateways.lab_supabase import SupabaseLabRecordRepository
from backend.adapters.gateways.sql_repositories import SqlPostRepository, SqlUserRepository
from backend.adapters.gateways.vector_stores import PineconeVectorStore, QdrantVectorStore, WeaviateVectorStore
from backend.adapters.security.bcrypt_hasher import BcryptPasswordHasher
from backend.adapters.security.jwt_token_provider import JwtTokenProvider
from backend.domain.entities import User
from backend.domain.exceptions import UnsupportedProviderError
from backend.domain.ports import LabRecordRepository, VectorStore
from backend.infrastructure import clients
from backend.infrastructure.orm import get_db
from backend.infrastructure.settings import settings
from backend.usecases import AuthUseCase, EmployeeUseCase, GraphUseCase, LabRecordUseCase, PostUseCase, VectorUseCase

# ---------------------------------------------------------------------------
# Lab 레코드 저장소 전략 테이블: URL 세그먼트 → 게이트웨이 팩토리
# ---------------------------------------------------------------------------
LAB_REPOSITORY_FACTORIES: Final[dict[str, Callable[[], LabRecordRepository]]] = {
    "mongo": lambda: MongoLabRecordRepository(clients.mongo_collection()),
    "postgres": lambda: PostgresLabRecordRepository(clients.lab_postgres_engine(), clients.lab_records_table),
    "supabase": lambda: SupabaseLabRecordRepository(clients.supabase_client(), settings.supabase_table_name),
    "redis": lambda: RedisLabRecordRepository(clients.redis_client(), settings.redis_key_prefix),
    "opensearch": lambda: OpenSearchLabRecordRepository(clients.opensearch_client(), settings.opensearch_index_name),
    "clickhouse": lambda: ClickHouseLabRecordRepository(clients.clickhouse_client(), settings.clickhouse_table_name),
    "cassandra": lambda: CassandraLabRecordRepository(clients.cassandra_session(), settings.cassandra_table_name),
}


def get_lab_usecase(source: str) -> Callable[[], LabRecordUseCase]:
    """라우터 등록 시 `Depends(get_lab_usecase("mongo"))` 로 사용하는 팩토리 생성기."""
    try:
        factory = LAB_REPOSITORY_FACTORIES[source]
    except KeyError as exc:
        raise UnsupportedProviderError(f"지원하지 않는 lab 저장소: {source}") from exc

    def _provide() -> LabRecordUseCase:
        return LabRecordUseCase(factory())

    _provide.__name__ = f"get_{source}_lab_usecase"  # OpenAPI/디버깅 시 이름이 보이도록
    return _provide


# ---------------------------------------------------------------------------
# Vector / Graph / Employee
# ---------------------------------------------------------------------------
VECTOR_STORE_FACTORIES: Final[dict[str, Callable[[], VectorStore]]] = {
    "pinecone": lambda: PineconeVectorStore(clients.pinecone_index()),
    "weaviate": lambda: WeaviateVectorStore(
        clients.weaviate_client().collections.get(settings.weaviate_collection_name)
    ),
    "qdrant": lambda: QdrantVectorStore(clients.qdrant_client(), settings.qdrant_collection_name),
}


def get_vector_usecase() -> VectorUseCase:
    provider = settings.vector_provider.lower()
    try:
        factory = VECTOR_STORE_FACTORIES[provider]
    except KeyError as exc:
        raise UnsupportedProviderError(f"지원하지 않는 VECTOR_PROVIDER 입니다: {provider}") from exc
    return VectorUseCase(factory())


def get_graph_usecase() -> GraphUseCase:
    return GraphUseCase(Neo4jGraphStore(clients.neo4j_driver(), settings.neo4j_database, settings.neo4j_graph_name))


def get_employee_usecase() -> EmployeeUseCase:
    return EmployeeUseCase(DynamoDbEmployeeRepository(clients.dynamodb_table()))


# ---------------------------------------------------------------------------
# Auth / Post (요청 단위 Session 이 필요하므로 get_db 를 체이닝)
# ---------------------------------------------------------------------------
_token_provider = JwtTokenProvider(
    secret_key=settings.secret_key,
    algorithm=settings.algorithm,
    expire_minutes=settings.access_token_expire_minutes,
)
_password_hasher = BcryptPasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def build_auth_usecase(db: Session) -> AuthUseCase:
    """main.py 의 시드 작업처럼 FastAPI Depends 바깥에서도 쓸 수 있도록 순수 함수로 분리."""
    return AuthUseCase(SqlUserRepository(db), _password_hasher, _token_provider)


def get_auth_usecase(db: Annotated[Session, Depends(get_db)]) -> AuthUseCase:
    return build_auth_usecase(db)


def get_post_usecase(db: Annotated[Session, Depends(get_db)]) -> PostUseCase:
    return PostUseCase(SqlPostRepository(db))


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth: Annotated[AuthUseCase, Depends(get_auth_usecase)],
) -> User:
    # AuthenticationError 는 error_handlers 가 401 + WWW-Authenticate 헤더로 번역합니다.
    return auth.authenticate(token)


# 라우터 시그니처를 짧게 만들어 주는 타입 별칭들
CurrentUser = Annotated[User, Depends(get_current_user)]
AuthUC = Annotated[AuthUseCase, Depends(get_auth_usecase)]
PostUC = Annotated[PostUseCase, Depends(get_post_usecase)]
EmployeeUC = Annotated[EmployeeUseCase, Depends(get_employee_usecase)]
VectorUC = Annotated[VectorUseCase, Depends(get_vector_usecase)]
GraphUC = Annotated[GraphUseCase, Depends(get_graph_usecase)]
