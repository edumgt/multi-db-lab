"""
환경변수 설정 — 애플리케이션의 "단일 진실 공급원(Single Source of Truth)".

[Python 중급 적용 사례 — 클래스 · 타입 힌트]
  * pydantic-settings 의 `BaseSettings` 를 상속하면 클래스 속성의 *타입 힌트* 가 곧 파싱 규칙이 됩니다.
      clickhouse_port: int = 8123   →  APP_CLICKHOUSE_PORT="8123" 을 int 로 변환, 실패 시 기동 중 에러
  * `@property` 로 파생 값(allowed_origin_list, cassandra_host_list) 을 계산해
    문자열 split 로직이 여러 모듈로 흩어지지 않게 합니다.
  * `Literal["pinecone", "weaviate", "qdrant"]` 로 vector_provider 의 오타를 기동 시점에 잡습니다.

[Clean Architecture 적용 사례]
  * 설정 읽기는 "프레임워크/드라이버" 관심사이므로 infrastructure 에 둡니다.
    유스케이스는 settings 를 import 하지 않고, 필요한 값은 조립 시점에 생성자 인자로 받습니다.
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

type VectorProviderName = Literal["pinecone", "weaviate", "qdrant"]


class Settings(BaseSettings):
    # ── Auth ────────────────────────────────────────────────────────────────
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    allowed_origins: str = "http://127.0.0.1:8001,http://localhost:8001"

    # ── Main PostgreSQL (users / posts, ORM) ───────────────────────────────
    database_url: str = "postgresql+psycopg://app_user:app_password@127.0.0.1:5432/app_db"

    # ── Lab PostgreSQL (lab_records, SQLAlchemy Core) ───────────────────────
    postgresql_dsn: str = "postgresql+psycopg://app_user:app_password@127.0.0.1:5432/app_db"
    postgresql_table_name: str = "lab_records"

    # ── AWS / DynamoDB ──────────────────────────────────────────────────────
    aws_region: str = "ap-northeast-2"
    dynamodb_table_name: str = "Employees"

    # ── MongoDB ─────────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "lab_db"
    mongodb_collection_name: str = "documents"

    # ── Supabase ────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_table_name: str = "lab_records"

    # ── Vector DB ───────────────────────────────────────────────────────────
    vector_provider: VectorProviderName = "pinecone"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "lab-vectors"
    weaviate_url: str = "http://localhost:8080"
    weaviate_collection_name: str = "LabVectors"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "lab-vectors"

    # ── Neo4j ───────────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    neo4j_graph_name: str = "lab_graph"

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "lab_record:"

    # ── OpenSearch ──────────────────────────────────────────────────────────
    opensearch_url: str = "http://localhost:9200"
    opensearch_index_name: str = "lab_records"

    # ── ClickHouse ──────────────────────────────────────────────────────────
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "default"
    clickhouse_table_name: str = "lab_records"

    # ── Cassandra ───────────────────────────────────────────────────────────
    cassandra_hosts: str = "127.0.0.1"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "lab_keyspace"
    cassandra_table_name: str = "lab_records"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    # ── 파생 값 ──────────────────────────────────────────────────────────────
    @cached_property
    def allowed_origin_list(self) -> list[str]:
        """쉼표 구분 문자열을 리스트로. cached_property 로 한 번만 계산합니다."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @cached_property
    def cassandra_host_list(self) -> list[str]:
        return [host.strip() for host in self.cassandra_hosts.split(",") if host.strip()]


settings = Settings()
