"""
LabRecord 유스케이스 — 7 개 저장소 라우터가 공유하는 단 하나의 비즈니스 로직.

[Clean Architecture 적용 사례 — Use Case]
  과거 lab_router.py 에는 아래 로직이 DB 마다 복사되어 7 번 반복돼 있었습니다.
      changes = {k: v for k, v in payload.model_dump().items() if v is not None}
      if not changes: raise HTTPException(400, "수정할 필드가 없습니다.")
      ...
      if not result: raise HTTPException(404, "... 레코드를 찾을 수 없습니다.")
  이제 이 규칙은 여기 *한 곳* 에만 있고, 저장소는 생성자로 주입됩니다.

[Python 중급 적용 사례 — 클래스 · 타입 힌트]
  * 생성자 주입(Constructor Injection): `repo: LabRecordRepository` — 추상 타입으로 선언.
  * `@property` 로 읽기 전용 파생 값(source 이름)을 노출.
  * 반환 타입을 모두 명시해 호출 측(라우터)이 presenter 변환을 안전하게 하도록 돕습니다.
"""

from __future__ import annotations

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import NotFoundError, ValidationError
from backend.domain.ports import LabRecordRepository


class LabRecordUseCase:
    def __init__(self, repo: LabRecordRepository) -> None:
        self._repo = repo

    @property
    def source(self) -> str:
        """응답 `source` 필드에 쓰일 저장소 이름 (구현체의 ClassVar 를 그대로 노출)."""
        return self._repo.source

    def create(self, record: LabRecord) -> LabRecord:
        return self._repo.add(record)

    def list(self, limit: int = 20) -> list[LabRecord]:
        # 비즈니스 규칙: limit 은 1~200 으로 고정. (라우터의 Query(ge=1, le=200) 과 이중 방어)
        if not 1 <= limit <= 200:
            raise ValidationError("limit 은 1 이상 200 이하여야 합니다.")
        return self._repo.list(limit)

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord:
        if patch.is_empty():
            raise ValidationError("수정할 필드가 없습니다.")
        updated = self._repo.update(record_id, patch)
        if updated is None:
            raise NotFoundError(f"{self.source} 레코드를 찾을 수 없습니다: {record_id}")
        return updated

    def delete(self, record_id: str) -> None:
        if not self._repo.delete(record_id):
            raise NotFoundError(f"{self.source} 레코드를 찾을 수 없습니다: {record_id}")
