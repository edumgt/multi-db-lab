"""docs_router — docs/techNNN.md 목록/본문 제공과 경로 탐색 차단을 검증합니다 (DB 불필요)."""

from __future__ import annotations

import pytest

from backend.adapters.api.docs_router import list_tech_docs, read_tech_doc
from backend.domain.exceptions import NotFoundError


def test_list_returns_tech_docs_in_order() -> None:
    docs = list_tech_docs()
    assert docs, "techNNN.md 가 하나도 없음"
    assert [d.id for d in docs] == sorted(d.id for d in docs)
    assert docs[0].id == "tech001"
    assert all(d.title and d.summary for d in docs)


def test_read_returns_markdown_content() -> None:
    doc = read_tech_doc("tech001")
    assert doc.id == "tech001"
    assert "__init__" in doc.content


@pytest.mark.parametrize("bad_id", ["tech999", "../Readme", "tech001/../tech002", "Readme"])
def test_read_rejects_unknown_or_traversal(bad_id: str) -> None:
    with pytest.raises(NotFoundError):
        read_tech_doc(bad_id)
