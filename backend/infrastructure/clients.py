"""
DB 드라이버 클라이언트 팩토리 — 과거 lab_router.py 상단에 흩어져 있던 `@lru_cache` 함수들을 모았습니다.

[Python 중급 적용 사례 — 클래스 · 예외 처리]
  * `functools.lru_cache` 를 인자 없는 함수에 붙이면 "지연 초기화 싱글턴" 이 됩니다.
    첫 호출에서만 연결을 만들고, 이후에는 같은 객체를 돌려줍니다.
  * `atexit` 대신 `ResourceRegistry` 클래스로 정리 대상을 모아 두고, FastAPI lifespan 종료 시
    한 번에 닫습니다. 테스트에서도 `registry.close_all()` 로 결정적으로 정리할 수 있습니다.
  * 자원 정리 중 하나가 실패해도 나머지는 계속 닫도록 `try/except Exception` + 로그로 격리합니다.
  * 필수 설정이 없으면 드라이버 예외가 아니라 도메인의 `ConfigurationError` 를 던집니다.
    → 라우터 에러 핸들러가 400 + 친절한 메시지로 번역합니다.

[Python 중급 적용 사례 — 타입 힌트]
  * `Callable[[], object]` : "인자 없이 호출 가능한 것" 을 표현.
  * `Closeable` Protocol (domain/ports.py) : close() 만 있으면 어떤 객체든 등록 가능.

[Clean Architecture 적용 사례]
  * 이 모듈은 Frameworks & Drivers 계층입니다. 여기서 만든 객체를 사용하는 쪽은 adapters 의 게이트웨이이고,
    게이트웨이는 팩토리를 직접 부르지 않고 *생성자 인자* 로 받습니다 (deps.py 참고).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Callable

import boto3
import clickhouse_connect
import redis
import weaviate
from cassandra.cluster import Cluster, Session as CassandraSession
from clickhouse_connect.driver.client import Client as ClickHouseClient
from neo4j import Driver, GraphDatabase
from opensearchpy import OpenSearch
from pinecone import Pinecone
from pymongo import MongoClient
from pymongo.collection import Collection
from qdrant_client import QdrantClient
from sqlalchemy import JSON, Column, Engine, MetaData, String, Table, create_engine
from supabase import Client as SupabaseClient, create_client

from backend.domain.exceptions import ConfigurationError
from backend.infrastructure.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 종료 시 정리할 자원 레지스트리
# ---------------------------------------------------------------------------
class ResourceRegistry:
    """close 콜백을 모아 두었다가 앱 종료 시 역순으로 실행합니다 (LIFO — 나중에 연 것부터 닫기)."""

    def __init__(self) -> None:
        self._closers: list[tuple[str, Callable[[], object]]] = []

    def register(self, name: str, closer: Callable[[], object]) -> None:
        self._closers.append((name, closer))

    def close_all(self) -> None:
        while self._closers:
            name, closer = self._closers.pop()
            try:
                closer()
                logger.info("closed %s", name)
            except Exception:  # noqa: BLE001 — 정리 단계에서는 어떤 예외도 다른 자원 정리를 막으면 안 됨
                logger.exception("failed to close %s", name)


registry = ResourceRegistry()


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
@lru_cache
def mongo_client() -> MongoClient:
    client: MongoClient = MongoClient(settings.mongodb_uri)
    registry.register("mongo", client.close)
    return client


def mongo_collection() -> Collection:
    return mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name]


# ---------------------------------------------------------------------------
# Lab PostgreSQL (SQLAlchemy Core — 스키마가 단순하고 ORM 매핑이 과한 경우)
# ---------------------------------------------------------------------------
lab_metadata = MetaData()
lab_records_table = Table(
    settings.postgresql_table_name,
    lab_metadata,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("content", String, nullable=False),
    Column("tags", JSON, nullable=False),
)


@lru_cache
def lab_postgres_engine() -> Engine:
    engine = create_engine(settings.postgresql_dsn, future=True)
    lab_metadata.create_all(engine)
    registry.register("lab-postgres", engine.dispose)
    return engine


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------
@lru_cache
def supabase_client() -> SupabaseClient:
    if not settings.supabase_url or not settings.supabase_key:
        raise ConfigurationError("Supabase 설정(APP_SUPABASE_URL, APP_SUPABASE_KEY)이 필요합니다.")
    return create_client(settings.supabase_url, settings.supabase_key)


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
@lru_cache
def redis_client() -> redis.Redis:
    # decode_responses=True : bytes 대신 str 을 돌려받아 json.loads 에 바로 넘길 수 있습니다.
    client = redis.from_url(settings.redis_url, decode_responses=True)
    registry.register("redis", client.close)
    return client


# ---------------------------------------------------------------------------
# OpenSearch
# ---------------------------------------------------------------------------
@lru_cache
def opensearch_client() -> OpenSearch:
    client = OpenSearch(hosts=[settings.opensearch_url])
    registry.register("opensearch", client.close)
    return client


# ---------------------------------------------------------------------------
# ClickHouse
# ---------------------------------------------------------------------------
@lru_cache
def clickhouse_client() -> ClickHouseClient:
    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {settings.clickhouse_table_name}
        (
            id String,
            title String,
            content String,
            tags Array(String)
        ) ENGINE = MergeTree ORDER BY id
        """
    )
    registry.register("clickhouse", client.close)
    return client


# ---------------------------------------------------------------------------
# Cassandra
# ---------------------------------------------------------------------------
@lru_cache
def cassandra_session() -> CassandraSession:
    cluster = Cluster(settings.cassandra_host_list, port=settings.cassandra_port)
    session = cluster.connect()
    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {settings.cassandra_keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )
    session.set_keyspace(settings.cassandra_keyspace)
    session.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {settings.cassandra_table_name} (
            id text PRIMARY KEY,
            title text,
            content text,
            tags list<text>
        )
        """
    )

    def _shutdown() -> None:
        session.shutdown()
        cluster.shutdown()

    registry.register("cassandra", _shutdown)
    return session


# ---------------------------------------------------------------------------
# Vector DB
# ---------------------------------------------------------------------------
@lru_cache
def pinecone_index():
    if not settings.pinecone_api_key:
        raise ConfigurationError("Pinecone 설정(APP_PINECONE_API_KEY)이 필요합니다.")
    return Pinecone(api_key=settings.pinecone_api_key).Index(settings.pinecone_index_name)


@lru_cache
def weaviate_client() -> weaviate.WeaviateClient:
    client = weaviate.connect_to_local()
    registry.register("weaviate", client.close)
    return client


@lru_cache
def qdrant_client() -> QdrantClient:
    client = QdrantClient(url=settings.qdrant_url)
    registry.register("qdrant", client.close)
    return client


# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------
@lru_cache
def neo4j_driver() -> Driver:
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    registry.register("neo4j", driver.close)
    return driver


# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------
@lru_cache
def dynamodb_table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.dynamodb_table_name)
