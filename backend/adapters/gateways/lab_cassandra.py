"""
Cassandra 게이트웨이 — LabRecordRepository 포트 구현 (CQL).

[Python 중급 적용 사례 — 예외 처리]
  cassandra-driver 의 예외 루트는 `cassandra.DriverException` 입니다. 연결 끊김(NoHostAvailable),
  타임아웃(OperationTimedOut), 쿼리 오류(InvalidRequest) 가 모두 이 아래에 있습니다.
"""

from __future__ import annotations

from typing import Any, ClassVar

from cassandra import DriverException
from cassandra.cluster import Session

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository


class CassandraLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "cassandra"

    def __init__(self, session: Session, table_name: str) -> None:
        self._session = session
        self._table = table_name

    @staticmethod
    def _row_to_record(row: Any) -> LabRecord:
        # cassandra Row 는 namedtuple 류라 속성 접근. tags 가 NULL 이면 None 이므로 `or []` 로 방어.
        return LabRecord(id=row.id, title=row.title, content=row.content, tags=list(row.tags or []))

    def add(self, record: LabRecord) -> LabRecord:
        try:
            self._session.execute(
                f"INSERT INTO {self._table} (id, title, content, tags) VALUES (%s, %s, %s, %s)",
                (record.id, record.title, record.content, record.tags),
            )
        except DriverException as exc:
            raise ExternalServiceError("Cassandra 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            rows = self._session.execute(f"SELECT id, title, content, tags FROM {self._table} LIMIT %s", (limit,))
            return [self._row_to_record(row) for row in rows]
        except DriverException as exc:
            raise ExternalServiceError("Cassandra 조회 실패", service=self.source) from exc

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        changes = patch.changes()
        try:
            if self._session.execute(f"SELECT id FROM {self._table} WHERE id = %s", (record_id,)).one() is None:
                return None
            set_clause = ", ".join(f"{key} = %s" for key in changes)
            self._session.execute(
                f"UPDATE {self._table} SET {set_clause} WHERE id = %s", (*changes.values(), record_id)
            )
            row = self._session.execute(
                f"SELECT id, title, content, tags FROM {self._table} WHERE id = %s", (record_id,)
            ).one()
        except DriverException as exc:
            raise ExternalServiceError("Cassandra 수정 실패", service=self.source) from exc
        return self._row_to_record(row) if row else None

    def delete(self, record_id: str) -> bool:
        try:
            if self._session.execute(f"SELECT id FROM {self._table} WHERE id = %s", (record_id,)).one() is None:
                return False
            self._session.execute(f"DELETE FROM {self._table} WHERE id = %s", (record_id,))
        except DriverException as exc:
            raise ExternalServiceError("Cassandra 삭제 실패", service=self.source) from exc
        return True
