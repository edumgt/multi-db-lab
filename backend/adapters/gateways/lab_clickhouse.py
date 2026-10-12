"""
ClickHouse 게이트웨이 — LabRecordRepository 포트 구현.

ClickHouse 는 OLAP 엔진이라 행 단위 UPDATE/DELETE 가 "mutation"(비동기 재작성) 입니다.
실습에서는 `mutations_sync=1` 로 동기 실행해 바로 조회되게 합니다.

[Python 중급 적용 사례 — 타입 힌트]
  `Final` 로 컬럼 목록을 상수로 고정합니다. 재대입하면 mypy 가 오류를 냅니다.
"""

from __future__ import annotations

from typing import ClassVar, Final

from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository

COLUMNS: Final[tuple[str, ...]] = ("id", "title", "content", "tags")


class ClickHouseLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "clickhouse"

    def __init__(self, client: Client, table_name: str) -> None:
        self._client = client
        self._table = table_name

    def _select_one(self, record_id: str) -> LabRecord | None:
        result = self._client.query(
            f"SELECT {', '.join(COLUMNS)} FROM {self._table} WHERE id = {{id:String}}",
            parameters={"id": record_id},
        )
        if not result.result_rows:
            return None
        return LabRecord.from_dict(dict(zip(result.column_names, result.result_rows[0])))

    def add(self, record: LabRecord) -> LabRecord:
        data = record.to_dict()
        try:
            self._client.insert(self._table, [[data[col] for col in COLUMNS]], column_names=list(COLUMNS))
        except ClickHouseError as exc:
            raise ExternalServiceError("ClickHouse 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            result = self._client.query(
                f"SELECT {', '.join(COLUMNS)} FROM {self._table} LIMIT {{limit:UInt32}}",
                parameters={"limit": limit},
            )
        except ClickHouseError as exc:
            raise ExternalServiceError("ClickHouse 조회 실패", service=self.source) from exc
        return [LabRecord.from_dict(dict(zip(result.column_names, row))) for row in result.result_rows]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        changes = patch.changes()
        try:
            if self._select_one(record_id) is None:
                return None
            # 파라미터 바인딩({key:Type}) 으로 값은 안전하게 전달하고, 컬럼명은 COLUMNS 화이트리스트 안의 값만 사용됩니다.
            set_clause = ", ".join(
                f"{key} = {{{key}:Array(String)}}" if key == "tags" else f"{key} = {{{key}:String}}"
                for key in changes
                if key in COLUMNS
            )
            self._client.command(
                f"ALTER TABLE {self._table} UPDATE {set_clause} WHERE id = {{id:String}}",
                parameters={**changes, "id": record_id},
                settings={"mutations_sync": 1},
            )
            return self._select_one(record_id)
        except ClickHouseError as exc:
            raise ExternalServiceError("ClickHouse 수정 실패", service=self.source) from exc

    def delete(self, record_id: str) -> bool:
        try:
            if self._select_one(record_id) is None:
                return False
            self._client.command(
                f"ALTER TABLE {self._table} DELETE WHERE id = {{id:String}}",
                parameters={"id": record_id},
                settings={"mutations_sync": 1},
            )
        except ClickHouseError as exc:
            raise ExternalServiceError("ClickHouse 삭제 실패", service=self.source) from exc
        return True
