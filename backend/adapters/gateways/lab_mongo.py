"""
MongoDB 게이트웨이 — LabRecordRepository 포트 구현.

[Python 중급 적용 사례 — 추상 인터페이스]
  `class MongoLabRecordRepository(LabRecordRepository)` 로 포트를 상속하고 add/list/update/delete 를
  모두 구현합니다. 하나라도 빠지면 deps.py 에서 인스턴스를 만들 때 TypeError 가 납니다.

[Python 중급 적용 사례 — 예외 처리]
  pymongo 의 모든 오류는 `PyMongoError` 를 상속하므로 이것 하나만 잡아 ExternalServiceError 로 변환합니다.
  `raise ... from exc` 로 원인을 체이닝하면 로그에 "The above exception was the direct cause..." 가 남습니다.
"""

from __future__ import annotations

from typing import ClassVar

from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository


class MongoLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "mongodb"

    def __init__(self, collection: Collection) -> None:
        self._collection = collection

    def add(self, record: LabRecord) -> LabRecord:
        try:
            self._collection.insert_one(record.to_dict())
        except PyMongoError as exc:
            raise ExternalServiceError("MongoDB 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            # {"_id": 0} : ObjectId 는 JSON 직렬화가 안 되므로 projection 단계에서 제외합니다.
            docs = self._collection.find({}, {"_id": 0}).limit(limit)
            return [LabRecord.from_dict(doc) for doc in docs]
        except PyMongoError as exc:
            raise ExternalServiceError("MongoDB 조회 실패", service=self.source) from exc

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        try:
            doc = self._collection.find_one_and_update(
                {"id": record_id},
                {"$set": patch.changes()},  # $set 은 지정한 필드만 바꾸므로 PATCH 의미론과 일치
                projection={"_id": 0},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            raise ExternalServiceError("MongoDB 수정 실패", service=self.source) from exc
        return LabRecord.from_dict(doc) if doc else None

    def delete(self, record_id: str) -> bool:
        try:
            result = self._collection.delete_one({"id": record_id})
        except PyMongoError as exc:
            raise ExternalServiceError("MongoDB 삭제 실패", service=self.source) from exc
        return result.deleted_count > 0
