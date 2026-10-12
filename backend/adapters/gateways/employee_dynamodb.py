"""
DynamoDB 게이트웨이 — EmployeeRepository 포트 구현.

[Python 중급 적용 사례 — 예외 처리]
  boto3 는 서비스 오류를 `botocore.exceptions.ClientError` 로, 네트워크/자격증명 오류를
  `BotoCoreError` 로 던집니다. 두 가지를 튜플로 함께 잡습니다.
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from backend.domain.entities import Employee
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import EmployeeRepository


class DynamoDbEmployeeRepository(EmployeeRepository):
    def __init__(self, table: Any) -> None:  # boto3 Table 은 동적 생성 타입이라 정적 타입이 없음
        self._table = table

    def add(self, employee: Employee) -> None:
        try:
            self._table.put_item(Item=employee.to_dict())
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceError("DynamoDB 저장 실패", service="dynamodb") from exc

    def find(self, employee_id: str, name: str) -> Employee | None:
        try:
            item = self._table.get_item(Key={"id": employee_id, "name": name}).get("Item")
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceError("DynamoDB 조회 실패", service="dynamodb") from exc
        return Employee.from_dict(item) if item else None

    def delete(self, employee_id: str, name: str) -> None:
        try:
            self._table.delete_item(Key={"id": employee_id, "name": name})
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceError("DynamoDB 삭제 실패", service="dynamodb") from exc

    def list_all(self) -> list[Employee]:
        try:
            items = self._table.scan().get("Items", [])  # 실습용 전체 스캔. 운영에서는 query + GSI 권장
        except (ClientError, BotoCoreError) as exc:
            raise ExternalServiceError("DynamoDB 스캔 실패", service="dynamodb") from exc
        return [Employee.from_dict(item) for item in items]
