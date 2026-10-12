"""
게시글 컨트롤러 — /api/posts/*

[Python 중급 적용 사례 — 타입 힌트]
  `Annotated[PostSortKey, Query(...)]` : 도메인의 Literal 별칭을 그대로 Query 파라미터 타입으로 사용.
  허용되지 않은 sort 값은 FastAPI 가 422 로 거절하므로 유스케이스에는 유효한 값만 도달합니다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from backend.adapters.api import presenters
from backend.adapters.api.deps import CurrentUser, PostUC
from backend.adapters.api.schemas.post import PostCreate, PostListResponse, PostOut, PostUpdate
from backend.domain.entities import PostSortKey

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
def list_posts(
    _: CurrentUser,  # 로그인 필수. 값은 쓰지 않으므로 밑줄 이름으로 의도를 표시
    posts: PostUC,
    q: Annotated[str, Query(description="title/content/owner 검색어")] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    sort: Annotated[PostSortKey, Query()] = "id:desc",
) -> PostListResponse:
    return presenters.post_page(posts.list_posts(q, page, size, sort))


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: int, _: CurrentUser, posts: PostUC, inc_view: Annotated[bool, Query()] = False) -> PostOut:
    return presenters.post(posts.get_post(post_id, inc_view=inc_view))


@router.post("", response_model=PostOut, status_code=201)
def create_post(payload: PostCreate, current_user: CurrentUser, posts: PostUC) -> PostOut:
    return presenters.post(posts.create_post(payload.title, payload.content, owner=current_user))


@router.put("/{post_id}", response_model=PostOut)
def update_post(post_id: int, payload: PostUpdate, current_user: CurrentUser, posts: PostUC) -> PostOut:
    updated = posts.update_post(post_id, title=payload.title, content=payload.content, actor=current_user)
    return presenters.post(updated)


@router.delete("/{post_id}")
def delete_post(post_id: int, current_user: CurrentUser, posts: PostUC) -> dict[str, object]:
    deleted_id = posts.delete_post(post_id, actor=current_user)
    return {"ok": True, "deleted_id": deleted_id}
