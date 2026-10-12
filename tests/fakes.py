"""
테스트용 인메모리 어댑터 — 포트(ABC)를 구현하는 "가짜" 구현체.

[Clean Architecture 가 주는 실질적 이득]
  유스케이스가 추상 포트에만 의존하므로, 실제 DB 없이 dict 하나로 구현한 저장소를 꽂아
  비즈니스 규칙(빈 PATCH 거절, 404, 403 …) 을 밀리초 단위로 검증할 수 있습니다.

[Python 중급 — 추상 인터페이스]
  포트의 @abstractmethod 를 하나라도 빠뜨리면 아래 클래스들은 인스턴스화되지 않습니다.
  즉 "테스트 더블이 실제 계약과 어긋나는" 흔한 문제를 언어 수준에서 막아 줍니다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import ClassVar

from backend.domain.entities import LabRecord, LabRecordPatch, Post, PostPage, PostSortKey, User
from backend.domain.exceptions import NotFoundError
from backend.domain.ports import LabRecordRepository, PasswordHasher, PostRepository, TokenProvider, UserRepository


class InMemoryLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "memory"

    def __init__(self) -> None:
        self._rows: dict[str, LabRecord] = {}

    def add(self, record: LabRecord) -> LabRecord:
        self._rows[record.id] = record
        return record

    def list(self, limit: int) -> list[LabRecord]:
        return list(self._rows.values())[:limit]

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        current = self._rows.get(record_id)
        if current is None:
            return None
        updated = current.apply(patch)
        self._rows[record_id] = updated
        return updated

    def delete(self, record_id: str) -> bool:
        return self._rows.pop(record_id, None) is not None


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._ids = count(1)

    def find_by_username(self, username: str) -> User | None:
        return self._users.get(username)

    def add(self, username: str, password_hash: str) -> User:
        user = User(id=next(self._ids), username=username, password_hash=password_hash)
        self._users[username] = user
        return user


class PlainTextHasher(PasswordHasher):
    """테스트 전용 — bcrypt 비용 없이 평문 비교. 운영 코드에서는 절대 사용 금지."""

    def hash(self, raw_password: str) -> str:
        return f"plain:{raw_password}"

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return password_hash == f"plain:{raw_password}"


class StaticTokenProvider(TokenProvider):
    def issue(self, subject: str) -> str:
        return f"token-for-{subject}"

    def subject_of(self, token: str) -> str | None:
        prefix = "token-for-"
        return token[len(prefix):] if token.startswith(prefix) else None


class InMemoryPostRepository(PostRepository):
    def __init__(self) -> None:
        self._posts: dict[int, Post] = {}
        self._ids = count(1)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def find_by_id(self, post_id: int) -> Post | None:
        return self._posts.get(post_id)

    def search(self, q: str, page: int, size: int, sort: PostSortKey) -> PostPage:
        rows = [p for p in self._posts.values() if q.lower() in (p.title + p.content).lower()]
        return PostPage(items=rows[(page - 1) * size : page * size], total=len(rows))

    def add(self, title: str, content: str, owner_id: int) -> Post:
        now = self._now()
        post = Post(
            id=next(self._ids), title=title, content=content, views=0, owner_id=owner_id,
            owner_name=f"user{owner_id}", created_at=now, updated_at=now,
        )
        self._posts[post.id] = post
        return post

    def _require(self, post_id: int) -> Post:
        post = self._posts.get(post_id)
        if post is None:
            raise NotFoundError()
        return post

    def update(self, post_id: int, *, title: str | None, content: str | None) -> Post:
        from dataclasses import replace

        post = self._require(post_id)
        updated = replace(
            post,
            title=title if title is not None else post.title,
            content=content if content is not None else post.content,
            updated_at=self._now(),
        )
        self._posts[post_id] = updated
        return updated

    def increment_views(self, post_id: int) -> Post:
        from dataclasses import replace

        post = self._require(post_id)
        updated = replace(post, views=post.views + 1)
        self._posts[post_id] = updated
        return updated

    def delete(self, post_id: int) -> None:
        self._require(post_id)
        del self._posts[post_id]
