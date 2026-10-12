"""
아키텍처 테스트 — "의존성 방향" 이 코드 수준에서 지켜지는지 import 문을 스캔해 검증합니다.

규칙:
  domain         → (표준 라이브러리만)
  usecases       → domain
  adapters       → domain, usecases, infrastructure, adapters
  infrastructure → domain.exceptions, infrastructure   (usecases/adapters 금지)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"

THIRD_PARTY_FORBIDDEN_IN_DOMAIN = {"fastapi", "sqlalchemy", "pydantic", "pymongo", "redis", "boto3", "neo4j"}

ALLOWED_INTERNAL = {
    "domain": set(),
    "usecases": {"domain"},
    "adapters": {"domain", "usecases", "infrastructure", "adapters"},
    "infrastructure": {"domain", "infrastructure"},
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _layer_files(layer: str) -> list[Path]:
    return sorted((BACKEND / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", list(ALLOWED_INTERNAL))
def test_layer_imports_point_inward(layer: str) -> None:
    for file in _layer_files(layer):
        for name in _imports(file):
            if name.startswith("backend."):
                target = name.split(".")[1]
                assert target in ALLOWED_INTERNAL[layer] or target == layer, (
                    f"{file.relative_to(BACKEND)} imports backend.{target} — {layer} 계층에서 금지"
                )


def test_domain_has_no_framework_imports() -> None:
    for file in _layer_files("domain"):
        top_levels = {name.split(".")[0] for name in _imports(file)}
        leaked = top_levels & THIRD_PARTY_FORBIDDEN_IN_DOMAIN
        assert not leaked, f"{file.name} 이 프레임워크를 import 합니다: {leaked}"


def test_usecases_do_not_know_http() -> None:
    """유스케이스 코드(주석 제외)에 FastAPI import 나 HTTPException 사용이 없어야 합니다."""
    for file in _layer_files("usecases"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        assert not any(name.split(".")[0] == "fastapi" for name in _imports(file)), f"{file.name} imports fastapi"
        used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert "HTTPException" not in used_names, f"{file.name} 이 HTTPException 을 사용합니다"
