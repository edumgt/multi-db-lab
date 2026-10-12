"""
인증 유스케이스 — "로그인" 과 "토큰으로 사용자 식별" 이라는 두 가지 애플리케이션 규칙.

[Clean Architecture 적용 사례 — 의존성 역전]
  bcrypt(passlib) 와 JWT(python-jose) 는 교체 가능한 기술입니다.
  유스케이스는 `PasswordHasher` · `TokenProvider` 포트만 알고,
  구현체(adapters/security/) 는 조립 시점에 주입됩니다.
  → 테스트에서는 해시를 평문 비교하는 FakeHasher 를 꽂아 bcrypt 비용(수백 ms) 없이 검증할 수 있습니다.
"""

from __future__ import annotations

from backend.domain.entities import User
from backend.domain.exceptions import AuthenticationError
from backend.domain.ports import PasswordHasher, TokenProvider, UserRepository


class AuthUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenProvider) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    def login(self, username: str, password: str) -> str:
        """자격 증명이 맞으면 액세스 토큰을 돌려줍니다."""
        user = self._users.find_by_username(username)
        # 사용자 존재 여부와 비밀번호 오류를 구분해 알려주지 않습니다(계정 열거 공격 방지).
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("아이디 또는 비밀번호가 올바르지 않습니다.")
        return self._tokens.issue(subject=user.username)

    def authenticate(self, token: str) -> User:
        """Bearer 토큰 → User. 라우터의 `get_current_user` 의존성이 호출합니다."""
        username = self._tokens.subject_of(token)
        if username is None:
            raise AuthenticationError()
        user = self._users.find_by_username(username)
        if user is None:
            raise AuthenticationError()
        return user

    def ensure_user(self, username: str, password: str) -> User:
        """시드 데이터용: 없으면 만들고 있으면 그대로 돌려줍니다 (멱등)."""
        existing = self._users.find_by_username(username)
        if existing is not None:
            return existing
        return self._users.add(username, self._hasher.hash(password))
