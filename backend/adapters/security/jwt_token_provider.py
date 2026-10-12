"""
JWT 토큰 제공자 — TokenProvider 포트 구현 (python-jose).

[Python 중급 적용 사례 — 예외 처리 · JSON 처리]
  * JWT 는 Base64 로 감싼 *JSON* 입니다. `jwt.decode` 는 서명 검증 후 payload 를 dict 로 돌려줍니다.
  * 만료·서명 불일치·형식 오류는 모두 `JWTError` 하위 → 하나만 잡아 None 을 돌려주고,
    "왜 실패했는지" 는 로깅만 합니다. 클라이언트에게 실패 원인을 세세히 알려주면 공격 힌트가 됩니다.
  * `payload.get("sub")` 가 str 이 아닐 수도 있으니 isinstance 로 방어적 검사를 합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from backend.domain.ports import TokenProvider

logger = logging.getLogger(__name__)


class JwtTokenProvider(TokenProvider):
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._expire = timedelta(minutes=expire_minutes)

    def issue(self, subject: str) -> str:
        claims = {"sub": subject, "exp": datetime.now(timezone.utc) + self._expire}
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def subject_of(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            logger.debug("jwt decode failed: %s", exc)
            return None
        subject = payload.get("sub")
        return subject if isinstance(subject, str) else None
