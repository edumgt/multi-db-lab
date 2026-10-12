"""
Supabase 게이트웨이 — LabRecordRepository 포트 구현 (PostgREST 를 HTTP 로 호출).

[Python 중급 적용 사례 — 예외 처리]
  supabase-py 는 HTTP 오류를 `postgrest.exceptions.APIError` 로 던집니다. 네트워크 단절 등은
  httpx 예외로 올라올 수 있어 `(APIError, OSError)` 튜플로 함께 잡습니다.
"""

from __future__ import annotations

from typing import ClassVar

from postgrest.exceptions import APIError
from supabase import Client

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository


class SupabaseLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "supabase"

    def __init__(self, client: Client, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def _table(self):
        return self._client.table(self._table_name)

    def add(self, record: LabRecord) -> LabRecord:
        try:
            self._table().insert(record.to_dict()).execute()
        except (APIError, OSError) as exc:
            raise ExternalServiceError("Supabase 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            response = self._table().select("*").limit(limit).execute()
        except (APIError, OSError) as exc:
            raise ExternalServiceError("Supabase 조회 실패", service=self.source) from exc
        return [LabRecord.from_dict(item) for item in response.data]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        try:
            response = self._table().update(patch.changes()).eq("id", record_id).execute()
        except (APIError, OSError) as exc:
            raise ExternalServiceError("Supabase 수정 실패", service=self.source) from exc
        return LabRecord.from_dict(response.data[0]) if response.data else None

    def delete(self, record_id: str) -> bool:
        try:
            response = self._table().delete().eq("id", record_id).execute()
        except (APIError, OSError) as exc:
            raise ExternalServiceError("Supabase 삭제 실패", service=self.source) from exc
        return bool(response.data)
