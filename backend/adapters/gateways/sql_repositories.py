"""
SQLAlchemy ORM 게이트웨이 — UserRepository · PostRepository 포트 구현.

[Clean Architecture 적용 사례 — Interface Adapter (게이트웨이)]
  ORM 행(UserRow / PostRow) → 도메인 엔티티(User / Post) 변환을 `_to_user` / `_to_post` 가 담당합니다.
  유스케이스는 SQLAlchemy Session 의 존재를 모르며, 세션 밖으로 ORM 객체가 새지 않습니다.

[Python 중급 적용 사례 — 타입 힌트]
  * `PostSortKey` Literal 과 `_ORDER_BY: Final[dict[PostSortKey, ...]]` 를 함께 쓰면,
    Literal 에 값이 추가되었는데 dict 에 빠진 경우를 mypy 가 잡아줄 수 있습니다.
  * 키워드 전용 인자(`*, title, content`) 로 호출 측이 인자 순서를 헷갈리지 않게 강제합니다.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.domain.entities import Post, PostPage, PostSortKey, User
from backend.domain.exceptions import ExternalServiceError, NotFoundError
from backend.domain.ports import PostRepository, UserRepository
from backend.infrastructure.orm import PostRow, UserRow

_ORDER_BY: Final[dict[PostSortKey, Any]] = {
    "created_at:desc": PostRow.created_at.desc(),
    "views:desc": PostRow.views.desc(),
    "id:desc": PostRow.id.desc(),
    "id:asc": PostRow.id.asc(),
}


def _to_user(row: UserRow) -> User:
    return User(id=row.id, username=row.username, password_hash=row.password_hash)


def _to_post(row: PostRow) -> Post:
    return Post(
        id=row.id,
        title=row.title,
        content=row.content,
        views=row.views,
        owner_id=row.owner_id,
        owner_name=row.owner.username,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_username(self, username: str) -> User | None:
        try:
            row = self._db.scalar(select(UserRow).where(UserRow.username == username))
        except SQLAlchemyError as exc:
            raise ExternalServiceError("사용자 조회 실패", service="postgresql") from exc
        return _to_user(row) if row else None

    def add(self, username: str, password_hash: str) -> User:
        try:
            row = UserRow(username=username, password_hash=password_hash)
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise ExternalServiceError("사용자 저장 실패", service="postgresql") from exc
        return _to_user(row)


class SqlPostRepository(PostRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── 내부 헬퍼 ───────────────────────────────────────────────────────────
    def _base_query(self, q: str):
        query = select(PostRow).join(PostRow.owner).options(selectinload(PostRow.owner))
        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(PostRow.title.ilike(pattern), PostRow.content.ilike(pattern), UserRow.username.ilike(pattern))
            )
        return query

    def _row(self, post_id: int) -> PostRow:
        row = self._db.scalar(select(PostRow).options(selectinload(PostRow.owner)).where(PostRow.id == post_id))
        if row is None:
            raise NotFoundError("게시글을 찾을 수 없습니다.")
        return row

    def _save(self, row: PostRow) -> Post:
        try:
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise ExternalServiceError("게시글 저장 실패", service="postgresql") from exc
        return _to_post(row)

    # ── 포트 구현 ───────────────────────────────────────────────────────────
    def find_by_id(self, post_id: int) -> Post | None:
        try:
            row = self._db.scalar(select(PostRow).options(selectinload(PostRow.owner)).where(PostRow.id == post_id))
        except SQLAlchemyError as exc:
            raise ExternalServiceError("게시글 조회 실패", service="postgresql") from exc
        return _to_post(row) if row else None

    def search(self, q: str, page: int, size: int, sort: PostSortKey) -> PostPage:
        try:
            base = self._base_query(q)
            total = self._db.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = self._db.scalars(base.order_by(_ORDER_BY[sort]).offset((page - 1) * size).limit(size)).all()
        except SQLAlchemyError as exc:
            raise ExternalServiceError("게시글 검색 실패", service="postgresql") from exc
        return PostPage(items=[_to_post(r) for r in rows], total=total)

    def add(self, title: str, content: str, owner_id: int) -> Post:
        return self._save(PostRow(title=title, content=content, owner_id=owner_id))

    def update(self, post_id: int, *, title: str | None, content: str | None) -> Post:
        row = self._row(post_id)
        if title is not None:
            row.title = title
        if content is not None:
            row.content = content
        return self._save(row)

    def increment_views(self, post_id: int) -> Post:
        row = self._row(post_id)
        row.views += 1
        return self._save(row)

    def delete(self, post_id: int) -> None:
        row = self._row(post_id)
        try:
            self._db.delete(row)
            self._db.commit()
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise ExternalServiceError("게시글 삭제 실패", service="postgresql") from exc
