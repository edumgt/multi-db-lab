"""Employee 유스케이스 — DynamoDB 구현을 모르는 애플리케이션 규칙."""

from __future__ import annotations

from backend.domain.entities import Employee
from backend.domain.exceptions import NotFoundError
from backend.domain.ports import EmployeeRepository


class EmployeeUseCase:
    def __init__(self, repo: EmployeeRepository) -> None:
        self._repo = repo

    def create(self, employee: Employee) -> None:
        self._repo.add(employee)

    def get(self, employee_id: str, name: str) -> Employee:
        found = self._repo.find(employee_id, name)
        if found is None:
            # 과거 라우터에 있던 `if not item: raise HTTPException(404)` 를 유스케이스로 옮김.
            raise NotFoundError("Employee not found")
        return found

    def delete(self, employee_id: str, name: str) -> None:
        self._repo.delete(employee_id, name)

    def list_all(self) -> list[Employee]:
        return self._repo.list_all()
