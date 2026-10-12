"""
기술 문서 컨트롤러 — /api/docs/tech/* (프로젝트 루트의 techNNN.md 를 프론트엔드 offcanvas 에 제공)

[Clean Architecture 적용 사례]
  파일 시스템 접근은 Frameworks & Drivers 에 속하므로 어댑터 계층에 둡니다. 없는 문서는 HTTPException 이 아니라
  도메인 예외 NotFoundError 로 알리고, 404 변환은 error_handlers 가 담당합니다.

[Python 중급 적용 사례]
  * `re.fullmatch` 로 doc_id 를 검증해 경로 탐색(`../`) 을 차단합니다.
  * `Path.glob` + `sorted` 로 문서 목록을 파일명 순으로 만듭니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from fastapi import APIRouter
from pydantic import BaseModel

from backend.domain.exceptions import NotFoundError

router = APIRouter(prefix="/api/docs", tags=["docs"])

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_DOC_ID_PATTERN: Final = re.compile(r"tech\d{3}")

# 문서 제목 — 메뉴 표시용. 목록에 없는 파일은 첫 줄을 잘라 제목으로 씁니다.
_TITLES: Final[dict[str, str]] = {
    "tech001": "__init__.py 와 패키지",
    "tech002": "from __future__ import annotations",
    "tech003": "dataclasses",
    "tech004": "ABC 와 Protocol",
    "tech005": "타입 힌트 (Type Hints)",
    "tech006": "예외 처리와 커스텀 예외 계층",
    "tech007": "json 모듈 — 직렬화/역직렬화",
    "tech008": "functools — lru_cache · cached_property",
    "tech009": "컨텍스트 매니저 (with)",
    "tech010": "일급 함수 · 클로저 · 전략 테이블",
    "tech011": "제너레이터 · 이터레이터",
    "tech012": "메서드 종류와 @property",
    "tech013": "함수 인자 전달 방식",
    "tech014": "logging 모듈",
    "tech015": "ast 모듈 — 아키텍처 테스트",
    "tech016": "pydantic · pydantic-settings",
    "tech017": "pytest",
    "tech018": "문자열 포매팅 — f-string · %s · 바인딩",
}


class TechDocSummary(BaseModel):
    id: str
    title: str
    summary: str


class TechDocRead(TechDocSummary):
    content: str


def _doc_path(doc_id: str) -> Path:
    return PROJECT_ROOT / f"{doc_id}.md"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return ""


def _summary_of(doc_id: str, text: str) -> TechDocSummary:
    first = _first_line(text)
    title = _TITLES.get(doc_id) or (first[:40] + ("…" if len(first) > 40 else ""))
    return TechDocSummary(id=doc_id, title=title, summary=first)


@router.get("/tech", response_model=list[TechDocSummary])
def list_tech_docs() -> list[TechDocSummary]:
    docs: list[TechDocSummary] = []
    for path in sorted(PROJECT_ROOT.glob("tech*.md")):
        if _DOC_ID_PATTERN.fullmatch(path.stem):
            docs.append(_summary_of(path.stem, path.read_text(encoding="utf-8")))
    return docs


@router.get("/tech/{doc_id}", response_model=TechDocRead)
def read_tech_doc(doc_id: str) -> TechDocRead:
    if not _DOC_ID_PATTERN.fullmatch(doc_id) or not _doc_path(doc_id).is_file():
        raise NotFoundError(f"문서를 찾을 수 없습니다: {doc_id}")
    text = _doc_path(doc_id).read_text(encoding="utf-8")
    summary = _summary_of(doc_id, text)
    return TechDocRead(id=summary.id, title=summary.title, summary=summary.summary, content=text)
