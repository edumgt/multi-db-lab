"""
Redis 게이트웨이 — LabRecordRepository 포트 구현. 값은 JSON 문자열로 저장합니다.

[Python 중급 적용 사례 — JSON 처리]
  * 직렬화  : `json.dumps(record.to_dict(), ensure_ascii=False)`
              ensure_ascii=False 로 한글이 \\uXXXX 가 아닌 원문 그대로 저장되어 redis-cli 로 읽기 쉽습니다.
  * 역직렬화: `json.loads(raw)` — 손상된 값이면 `json.JSONDecodeError`(ValueError 하위) 가 납니다.
              이를 잡아 ExternalServiceError 로 바꿔 "데이터 손상" 을 500 이 아닌 502 로 분류합니다.

[Python 중급 적용 사례 — try / except / else / finally]
  `_load()` 가 네 절을 모두 사용합니다.
    try     : 실패할 수 있는 코드 (json.loads)
    except  : 실패 처리
    else    : try 가 *성공했을 때만* 실행 — 성공 경로를 except 에 가려지지 않게 분리
    finally : 성공/실패와 무관하게 실행 — 여기서는 디버그 로그
"""

from __future__ import annotations

import json
import logging
from typing import Any, ClassVar, cast

from redis import Redis
from redis.exceptions import RedisError

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import LabRecordRepository

logger = logging.getLogger(__name__)


class RedisLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "redis"

    def __init__(self, client: Redis, key_prefix: str) -> None:
        self._client = client
        self._prefix = key_prefix

    # ── 키/JSON 헬퍼 ────────────────────────────────────────────────────────
    def _key(self, record_id: str) -> str:
        return f"{self._prefix}{record_id}"

    @staticmethod
    def _dump(record: LabRecord) -> str:
        return json.dumps(record.to_dict(), ensure_ascii=False)

    def _load(self, raw: str, *, key: str) -> LabRecord:
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError(f"Redis 값이 올바른 JSON 이 아닙니다: {key}", service=self.source) from exc
        else:
            return LabRecord.from_dict(data)
        finally:
            logger.debug("redis load key=%s bytes=%d", key, len(raw))

    # ── 포트 구현 ───────────────────────────────────────────────────────────
    def add(self, record: LabRecord) -> LabRecord:
        try:
            self._client.set(self._key(record.id), self._dump(record))
        except RedisError as exc:
            raise ExternalServiceError("Redis 저장 실패", service=self.source) from exc
        return record

    def list(self, limit: int) -> list[LabRecord]:
        try:
            keys: list[str] = []
            # SCAN 은 KEYS 와 달리 서버를 블로킹하지 않습니다. count 는 "한 번에 훑을 힌트" 일 뿐입니다.
            for key in self._client.scan_iter(match=f"{self._prefix}*", count=100):
                keys.append(key)
                if len(keys) >= limit:
                    break
            # [타입 힌트] redis-py 는 동기/비동기 클라이언트가 같은 스텁을 공유해 반환 타입이 `Awaitable | Any` 로 잡힙니다.
            # 동기 클라이언트임을 알고 있으므로 cast 로 구체 타입을 알려줍니다.
            values = cast(list[str | None], self._client.mget(keys)) if keys else []
        except RedisError as exc:
            raise ExternalServiceError("Redis 조회 실패", service=self.source) from exc
        return [self._load(raw, key=key) for key, raw in zip(keys, values) if raw]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        key = self._key(record_id)
        try:
            raw = cast(str | None, self._client.get(key))
            if raw is None:
                return None
            updated = self._load(raw, key=key).apply(patch)  # 불변 엔티티 → 새 객체
            self._client.set(key, self._dump(updated))
        except RedisError as exc:
            raise ExternalServiceError("Redis 수정 실패", service=self.source) from exc
        return updated

    def delete(self, record_id: str) -> bool:
        try:
            return bool(self._client.delete(self._key(record_id)))
        except RedisError as exc:
            raise ExternalServiceError("Redis 삭제 실패", service=self.source) from exc
