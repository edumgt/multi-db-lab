"""
게시글 유스케이스.

[Clean Architecture 적용 사례 — 프레임워크 예외 제거]
  과거 services/post_service.py:
      from fastapi import HTTPException
      raise HTTPException(status_code=403, detail="본인 글만 수정할 수 있습니다.")
  현재:
      raise PermissionDeniedError("본인 글만 수정할 수 있습니다.")
  HTTP 403 으로 바꾸는 책임은 adapters/api/error_handlers.py 로 이동했습니다.

[Python 중급 적용 사례 — 클래스]
  * `_get_or_raise` 처럼 밑줄로 시작하는 메서드는 "내부 전용" 관례입니다.
  * 엔티티 메서드 `post.is_owned_by(user)` 를 호출해 규칙을 엔티티에 위임합니다(Tell, don't ask).
"""

from __future__ import annotations

from backend.domain.entities import Post, PostPage, PostSortKey, User
from backend.domain.exceptions import NotFoundError, PermissionDeniedError
from backend.domain.ports import PostRepository


class PostUseCase:
    def __init__(self, repo: PostRepository) -> None:
        self._repo = repo

    def list_posts(self, q: str, page: int, size: int, sort: PostSortKey) -> PostPage:
        return self._repo.search(q, page, size, sort)

    def get_post(self, post_id: int, *, inc_view: bool = False) -> Post:
        post = self._get_or_raise(post_id)
        if inc_view:
            post = self._repo.increment_views(post.id)
        return post

    def create_post(self, title: str, content: str, owner: User) -> Post:
        return self._repo.add(title=title, content=content, owner_id=owner.id)

    def update_post(self, post_id: int, *, title: str | None, content: str | None, actor: User) -> Post:
        post = self._get_or_raise(post_id)
        if not post.is_owned_by(actor):
            raise PermissionDeniedError("본인 글만 수정할 수 있습니다.")
        return self._repo.update(post_id, title=title, content=content)

    def delete_post(self, post_id: int, *, actor: User) -> int:
        post = self._get_or_raise(post_id)
        if not post.is_owned_by(actor):
            raise PermissionDeniedError("본인 글만 삭제할 수 있습니다.")
        self._repo.delete(post_id)
        return post_id

    def _get_or_raise(self, post_id: int) -> Post:
        post = self._repo.find_by_id(post_id)
        if post is None:
            raise NotFoundError("게시글을 찾을 수 없습니다.")
        return post
