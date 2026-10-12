"""
PostgreSQL(SQLAlchemy Core) 게이트웨이 — LabRecordRepository 포트 구현.

[Python 중급 적용 사례 — 예외 처리]
  SQLAlchemy 의 모든 DB 오류는 `SQLAlchemyError` 하위이므로 한 번에 잡습니다.
  `with engine.begin() as conn:` 컨텍스트 매니저는 블록을 정상 종료하면 commit, 예외면 rollback 합니다
  — try/finally 를 직접 쓰지 않아도 자원 정리가 보장되는 패턴입니다.
"""

from __future__ import annotations

from typing import Any, ClassVar, Mapping, cast

from sqlalchemy import Engine, Table, delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository


class PostgresLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "postgresql"

    def __init__(self, engine: Engine, table: Table) -> None:
        self._engine = engine
        self._table = table

    @staticmethod
    def _from_row(row: Mapping[Any, Any]) -> LabRecord:
        # [타입 힌트] SQLAlchemy RowMapping 의 키 타입은 `str | Column` 이라 Mapping[str, Any] 와 어긋납니다.
        # 런타임에는 문자열 키이므로 `typing.cast` 로 "이 값은 이 타입이다" 라고 검사기에게만 알려줍니다 (런타임 비용 0).
        return LabRecord.from_dict(cast(Mapping[str, Any], row))

    def add(self, record: LabRecord) -> LabRecord:
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(self._table).values(**record.to_dict()))
        except SQLAlchemyError as exc:
            raise ExternalServiceError("PostgreSQL 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            with self._engine.begin() as conn:
                rows = conn.execute(select(self._table).limit(limit)).mappings().all()
        except SQLAlchemyError as exc:
            raise ExternalServiceError("PostgreSQL 조회 실패", service=self.source) from exc
        return [self._from_row(row) for row in rows]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        try:
            with self._engine.begin() as conn:
                row = (
                    conn.execute(
                        update(self._table)
                        .where(self._table.c.id == record_id)
                        .values(**patch.changes())
                        .returning(self._table)  # RETURNING 으로 왕복 1 회 절약
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise ExternalServiceError("PostgreSQL 수정 실패", service=self.source) from exc
        return self._from_row(row) if row else None

    def delete(self, record_id: str) -> bool:
        try:
            with self._engine.begin() as conn:
                result = conn.execute(delete(self._table).where(self._table.c.id == record_id))
        except SQLAlchemyError as exc:
            raise ExternalServiceError("PostgreSQL 삭제 실패", service=self.source) from exc
        return (result.rowcount or 0) > 0
