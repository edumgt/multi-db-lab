"""
벡터 저장소 게이트웨이 3 종 — VectorStore 포트 구현 (Pinecone · Weaviate · Qdrant).

[Clean Architecture 적용 사례 — Interface Adapter]
  세 provider 의 API 모양은 전혀 다릅니다.
    Pinecone : index.upsert(vectors=[{id, values, metadata}]) / result.matches[].score
    Weaviate : collection.data.insert(uuid, properties, vector) / obj.metadata.distance
    Qdrant   : client.upsert(points=[PointStruct]) / point.score
  게이트웨이는 이 차이를 흡수해 유스케이스에는 항상 `list[VectorMatch]` 만 돌려줍니다.

[Python 중급 적용 사례 — 클래스]
  * `uuid.uuid5(NAMESPACE, external_id)` : 같은 외부 id 는 항상 같은 UUID 로 결정적으로 매핑 (멱등 upsert).
  * 세 클래스가 같은 ABC 를 상속하므로 `isinstance(store, VectorStore)` 로 일괄 처리 가능.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar, Final, Sequence

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams
from weaviate.classes.query import MetadataQuery
from weaviate.collections import Collection as WeaviateCollection
from weaviate.exceptions import WeaviateBaseError

from backend.domain.entities import JsonObject, VectorMatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import VectorStore

WEAVIATE_UUID_NAMESPACE: Final = uuid.UUID("f33e9e58-8f5e-44cb-a272-4f2f96699e2f")
QDRANT_UUID_NAMESPACE: Final = uuid.UUID("a3f0e4b2-6c1d-4e9a-9b3f-7d2c8e5a1f60")


class PineconeVectorStore(VectorStore):
    provider: ClassVar[str] = "pinecone"

    def __init__(self, index: Any) -> None:  # pinecone Index 타입은 SDK 버전마다 경로가 달라 Any 로 둡니다.
        self._index = index

    def upsert(self, vector_id: str, values: Sequence[float], metadata: JsonObject) -> None:
        try:
            self._index.upsert(vectors=[{"id": vector_id, "values": list(values), "metadata": dict(metadata)}])
        except Exception as exc:  # pinecone SDK 는 공통 예외 루트가 없어 넓게 잡고 즉시 도메인 예외로 변환
            raise ExternalServiceError("Pinecone upsert 실패", service=self.provider) from exc

    def query(self, values: Sequence[float], top_k: int) -> list[VectorMatch]:
        try:
            result = self._index.query(vector=list(values), top_k=top_k, include_metadata=True)
        except Exception as exc:
            raise ExternalServiceError("Pinecone query 실패", service=self.provider) from exc
        matches = result.to_dict().get("matches", [])
        return [
            VectorMatch(id=str(m["id"]), score=m.get("score"), payload=dict(m.get("metadata") or {})) for m in matches
        ]


class WeaviateVectorStore(VectorStore):
    provider: ClassVar[str] = "weaviate"

    def __init__(self, collection: WeaviateCollection) -> None:
        self._collection = collection

    def upsert(self, vector_id: str, values: Sequence[float], metadata: JsonObject) -> None:
        try:
            self._collection.data.insert(
                uuid=str(uuid.uuid5(WEAVIATE_UUID_NAMESPACE, vector_id)),
                properties={"external_id": vector_id, "metadata": dict(metadata)},
                vector=list(values),
            )
        except WeaviateBaseError as exc:
            raise ExternalServiceError("Weaviate upsert 실패", service=self.provider) from exc

    def query(self, values: Sequence[float], top_k: int) -> list[VectorMatch]:
        try:
            result = self._collection.query.near_vector(
                near_vector=list(values), limit=top_k, return_metadata=MetadataQuery(distance=True)
            )
        except WeaviateBaseError as exc:
            raise ExternalServiceError("Weaviate query 실패", service=self.provider) from exc
        return [
            VectorMatch(
                id=str(obj.properties.get("external_id", obj.uuid)),
                # Weaviate 는 '거리' 를 주므로 '점수' 로 통일하기 위해 1 - distance 로 변환합니다.
                score=None if obj.metadata.distance is None else 1.0 - obj.metadata.distance,
                payload={"uuid": str(obj.uuid), "distance": obj.metadata.distance, **dict(obj.properties)},
            )
            for obj in result.objects
        ]


class QdrantVectorStore(VectorStore):
    provider: ClassVar[str] = "qdrant"

    def __init__(self, client: QdrantClient, collection_name: str) -> None:
        self._client = client
        self._collection = collection_name

    def _ensure_collection(self, dimension: int) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def upsert(self, vector_id: str, values: Sequence[float], metadata: JsonObject) -> None:
        try:
            self._ensure_collection(len(values))
            self._client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=str(uuid.uuid5(QDRANT_UUID_NAMESPACE, vector_id)),
                        vector=list(values),
                        payload={"external_id": vector_id, **dict(metadata)},
                    )
                ],
            )
        except (UnexpectedResponse, OSError) as exc:
            raise ExternalServiceError("Qdrant upsert 실패", service=self.provider) from exc

    def query(self, values: Sequence[float], top_k: int) -> list[VectorMatch]:
        try:
            result = self._client.query_points(collection_name=self._collection, query=list(values), limit=top_k)
        except (UnexpectedResponse, OSError) as exc:
            raise ExternalServiceError("Qdrant query 실패", service=self.provider) from exc
        return [
            VectorMatch(
                id=str((point.payload or {}).get("external_id", point.id)),
                score=point.score,
                payload=dict(point.payload or {}),
            )
            for point in result.points
        ]
