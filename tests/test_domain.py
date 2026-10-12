"""도메인 계층 테스트 — 엔티티 불변성, JSON 왕복, 예외 계층, ABC 강제."""

from __future__ import annotations

import dataclasses
import json

import pytest

from backend.domain.entities import LabRecord, LabRecordPatch
from backend.domain.exceptions import DomainError, ExternalServiceError, NotFoundError
from backend.domain.ports import LabRecordRepository


def test_entity_is_immutable_and_json_roundtrips() -> None:
    record = LabRecord(id="1", title="제목", content="본문", tags=["x"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.title = "changed"  # type: ignore[misc]

    # [JSON 처리] dumps → loads → from_dict 왕복이 원본과 같아야 합니다.
    text = json.dumps(record.to_dict(), ensure_ascii=False)
    assert "제목" in text  # ensure_ascii=False 로 한글이 이스케이프되지 않음
    assert LabRecord.from_dict(json.loads(text)) == record


def test_patch_changes_and_apply() -> None:
    patch = LabRecordPatch(title="n")
    assert patch.changes() == {"title": "n"}
    assert LabRecordPatch().is_empty()
    assert LabRecord(id="1", title="a", content="b").apply(patch).title == "n"


def test_exception_hierarchy_and_chaining() -> None:
    assert issubclass(NotFoundError, DomainError)
    try:
        try:
            raise KeyError("id")
        except KeyError as exc:
            raise ExternalServiceError("wrapped", service="redis") from exc
    except ExternalServiceError as exc:
        assert isinstance(exc.__cause__, KeyError)  # `raise ... from exc` 체이닝
        assert exc.service == "redis" and exc.detail == "wrapped"


def test_abc_forces_full_implementation() -> None:
    class Incomplete(LabRecordRepository):
        def add(self, record):  # type: ignore[override]
            return record

    with pytest.raises(TypeError):
        Incomplete()  # list/update/delete 미구현 → 인스턴스화 불가
