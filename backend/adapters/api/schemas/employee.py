from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domain.entities import Employee


class EmployeeCreate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    position: str = Field(min_length=1)

    def to_entity(self) -> Employee:
        """[Interface Adapter] HTTP 입력 → 도메인 엔티티. 라우터가 아니라 스키마가 변환 책임을 가집니다."""
        return Employee(id=self.id, name=self.name, position=self.position)


class EmployeeRead(EmployeeCreate):
    pass
