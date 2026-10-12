"""Employee 컨트롤러 — /employees/* (DynamoDB). 404 판단은 EmployeeUseCase.get 이 담당합니다."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from backend.adapters.api import presenters
from backend.adapters.api.deps import EmployeeUC
from backend.adapters.api.schemas.employee import EmployeeCreate, EmployeeRead

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, employees: EmployeeUC) -> dict[str, str]:
    employees.create(payload.to_entity())
    return {"message": "Employee added to DynamoDB."}


@router.get("/{employee_id}/{name}", response_model=EmployeeRead)
def get_employee(employee_id: str, name: str, employees: EmployeeUC) -> EmployeeRead:
    return presenters.employee(employees.get(employee_id, name))


@router.delete("/{employee_id}/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str, name: str, employees: EmployeeUC) -> Response:
    employees.delete(employee_id, name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[EmployeeRead])
def list_employees(employees: EmployeeUC) -> list[EmployeeRead]:
    return [presenters.employee(e) for e in employees.list_all()]
