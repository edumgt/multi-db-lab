"""유스케이스 단위 테스트 — DB · 네트워크 · FastAPI 없이 비즈니스 규칙만 검증합니다."""

from __future__ import annotations

import pytest

from backend.domain.entities import LabRecord, LabRecordPatch, User
from backend.domain.exceptions import AuthenticationError, NotFoundError, PermissionDeniedError, ValidationError
from backend.usecases import AuthUseCase, LabRecordUseCase, PostUseCase
from tests.fakes import (
    InMemoryLabRecordRepository,
    InMemoryPostRepository,
    InMemoryUserRepository,
    PlainTextHasher,
    StaticTokenProvider,
)


# ── LabRecordUseCase ─────────────────────────────────────────────────────────
def test_lab_create_list_update_delete_roundtrip() -> None:
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    uc.create(LabRecord(id="r1", title="t", content="c", tags=["a"]))

    assert [r.id for r in uc.list()] == ["r1"]
    assert uc.source == "memory"

    updated = uc.update("r1", LabRecordPatch(title="new"))
    assert updated.title == "new" and updated.content == "c"  # 부분 수정: content 유지

    uc.delete("r1")
    assert uc.list() == []


def test_lab_update_rejects_empty_patch() -> None:
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    with pytest.raises(ValidationError):
        uc.update("any", LabRecordPatch())


def test_lab_update_and_delete_missing_raise_not_found() -> None:
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    with pytest.raises(NotFoundError):
        uc.update("missing", LabRecordPatch(title="x"))
    with pytest.raises(NotFoundError):
        uc.delete("missing")


def test_lab_list_limit_is_validated() -> None:
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    with pytest.raises(ValidationError):
        uc.list(0)


# ── AuthUseCase ──────────────────────────────────────────────────────────────
def _auth() -> AuthUseCase:
    return AuthUseCase(InMemoryUserRepository(), PlainTextHasher(), StaticTokenProvider())


def test_login_then_authenticate() -> None:
    auth = _auth()
    auth.ensure_user("admin", "pw")
    token = auth.login("admin", "pw")
    assert auth.authenticate(token).username == "admin"


def test_login_wrong_password_and_bad_token() -> None:
    auth = _auth()
    auth.ensure_user("admin", "pw")
    with pytest.raises(AuthenticationError):
        auth.login("admin", "wrong")
    with pytest.raises(AuthenticationError):
        auth.authenticate("garbage")


# ── PostUseCase ──────────────────────────────────────────────────────────────
def test_post_owner_rules() -> None:
    posts = PostUseCase(InMemoryPostRepository())
    owner = User(id=1, username="a", password_hash="x")
    other = User(id=2, username="b", password_hash="x")

    created = posts.create_post("hello", "world", owner)
    assert posts.get_post(created.id, inc_view=True).views == 1

    with pytest.raises(PermissionDeniedError):
        posts.update_post(created.id, title="hack", content=None, actor=other)
    with pytest.raises(PermissionDeniedError):
        posts.delete_post(created.id, actor=other)

    assert posts.update_post(created.id, title="edited", content=None, actor=owner).title == "edited"
    assert posts.delete_post(created.id, actor=owner) == created.id
    with pytest.raises(NotFoundError):
        posts.get_post(created.id)
