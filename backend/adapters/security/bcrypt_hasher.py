"""
bcrypt 비밀번호 해셔 — PasswordHasher 포트 구현.

[Clean Architecture 적용 사례 — 의존성 역전]
  과거 services/auth_service.py 의 모듈 수준 함수(hash_password / verify_password) 를
  포트를 구현하는 클래스로 바꿨습니다. 유스케이스는 `PasswordHasher` 타입만 알고,
  argon2 등으로 교체해도 유스케이스 코드는 변하지 않습니다.
"""

from __future__ import annotations

from passlib.context import CryptContext

from backend.domain.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        # deprecated="auto" : 더 안전한 스킴이 추가되면 기존 해시를 자동으로 "재해시 필요" 로 표시
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, raw_password: str) -> str:
        return self._ctx.hash(raw_password)

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return self._ctx.verify(raw_password, password_hash)  # 타이밍 공격에 안전한 비교
