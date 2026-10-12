"""
OpenSearch 게이트웨이 — LabRecordRepository 포트 구현.

[Python 중급 적용 사례 — 예외 처리: 구체 예외를 먼저, 일반 예외를 나중에]
  `NotFoundError`(404) 는 "없음" 이라는 *정상 흐름* 이므로 None/False 로 번역하고,
  그 외 `OpenSearchException` 은 장애이므로 ExternalServiceError 로 올립니다.
  except 절의 순서가 중요합니다 — 넓은 예외를 먼저 쓰면 좁은 예외 절은 영원히 실행되지 않습니다.
"""

from __future__ import annotations

from typing import ClassVar

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError as OpenSearchNotFound, OpenSearchException

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository


class OpenSearchLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "opensearch"

    def __init__(self, client: OpenSearch, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def add(self, record: LabRecord) -> LabRecord:
        try:
            # refresh=True : 색인 직후 검색에 보이도록 강제 (실습용. 운영에서는 비용이 큼)
            self._client.index(index=self._index, id=record.id, body=record.to_dict(), refresh=True)
        except OpenSearchException as exc:
            raise ExternalServiceError("OpenSearch 색인 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            response = self._client.search(index=self._index, body={"query": {"match_all": {}}, "size": limit})
        except OpenSearchNotFound:
            return []  # 인덱스가 아직 없으면 빈 목록 — 정상 흐름
        except OpenSearchException as exc:
            raise ExternalServiceError("OpenSearch 검색 실패", service=self.source) from exc
        return [LabRecord.from_dict(hit["_source"]) for hit in response["hits"]["hits"]]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        try:
            self._client.update(index=self._index, id=record_id, body={"doc": patch.changes()}, refresh=True)
            result = self._client.get(index=self._index, id=record_id)
        except OpenSearchNotFound:
            return None
        except OpenSearchException as exc:
            raise ExternalServiceError("OpenSearch 수정 실패", service=self.source) from exc
        return LabRecord.from_dict(result["_source"])

    def delete(self, record_id: str) -> bool:
        try:
            self._client.delete(index=self._index, id=record_id, refresh=True)
        except OpenSearchNotFound:
            return False
        except OpenSearchException as exc:
            raise ExternalServiceError("OpenSearch 삭제 실패", service=self.source) from exc
        return True
