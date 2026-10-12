"""
벡터 유스케이스 — provider(Pinecone · Weaviate · Qdrant) 선택은 조립 단계로 밀어냅니다.

[Clean Architecture 적용 사례 — Use Case vs Interface Adapter]
  과거 코드는 라우터 안에서 `if provider == "pinecone": ... elif "weaviate": ...` 로 분기했습니다.
  이제 라우터는 `VectorStore` 구현체가 무엇인지 모르고, deps.py 의 팩토리가 설정값으로 골라 줍니다.
  새 provider 를 추가할 때 이 파일과 라우터는 *한 줄도* 바뀌지 않습니다 (OCP, 개방-폐쇄 원칙).
"""

from __future__ import annotations

from typing import Sequence

from backend.domain.entities import JsonObject, VectorMatch
from backend.domain.exceptions import ValidationError
from backend.domain.ports import VectorStore


class VectorUseCase:
    def __init__(self, store: VectorStore) -> None:
        self._store = store

    @property
    def provider(self) -> str:
        return self._store.provider

    def upsert(self, vector_id: str, values: Sequence[float], metadata: JsonObject) -> None:
        if not values:
            raise ValidationError("values 는 비어 있을 수 없습니다.")
        self._store.upsert(vector_id, values, metadata)

    def query(self, values: Sequence[float], top_k: int = 3) -> list[VectorMatch]:
        if not values:
            raise ValidationError("values 는 비어 있을 수 없습니다.")
        if not 1 <= top_k <= 20:
            raise ValidationError("top_k 는 1 이상 20 이하여야 합니다.")
        return self._store.query(values, top_k)
