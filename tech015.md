`ast` 모듈은 파이썬 소스 코드를 **추상 구문 트리(Abstract Syntax Tree)** 로 파싱해 프로그램이 코드를 분석할 수 있게 합니다. 이 프로젝트는 `tests/test_architecture.py` 에서 **계층 간 import 방향** 을 자동 검사하는 데 사용합니다.

---

### 1. 왜 정규식이 아니라 AST 인가

```python
# 주석에 적힌 문장 — 정규식/문자열 검색은 이것도 '위반' 으로 잡음
# 과거 라우터에 있던 `raise HTTPException(404)` 를 유스케이스로 옮김.
```

* 실제로 이 프로젝트에서 `"HTTPException" not in text` 검사가 **docstring 때문에 오탐** 을 냈습니다.
* AST 는 주석·문자열을 코드와 구분하므로 "정말 import 했는가 / 정말 그 이름을 썼는가" 만 봅니다.

### 2. 파싱과 순회

```python
import ast
from pathlib import Path

tree = ast.parse(Path("backend/usecases/post_usecase.py").read_text(encoding="utf-8"))
for node in ast.walk(tree):                # 모든 노드를 깊이 우선으로
    if isinstance(node, ast.Import):           # import a, b
        names = [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom):     # from x.y import z
        module = node.module                   # "x.y"
```

* `ast.walk` 는 트리 전체를 평탄하게 돌려줍니다. 구조를 따라가며 처리하려면 `ast.NodeVisitor` 를 상속합니다.

### 3. 이 프로젝트의 의존성 방향 검사

```python
# tests/test_architecture.py
ALLOWED_INTERNAL = {
    "domain": set(),
    "usecases": {"domain"},
    "adapters": {"domain", "usecases", "infrastructure", "adapters"},
    "infrastructure": {"domain", "infrastructure"},
}

@pytest.mark.parametrize("layer", list(ALLOWED_INTERNAL))
def test_layer_imports_point_inward(layer: str) -> None:
    for file in (BACKEND / layer).rglob("*.py"):
        for name in _imports(file):
            if name.startswith("backend."):
                target = name.split(".")[1]              # "backend.domain.entities" → "domain"
                assert target in ALLOWED_INTERNAL[layer] or target == layer
```

* 누군가 `usecases/` 에서 `from backend.adapters...` 를 추가하면 **테스트가 실패** 합니다. 아키텍처 규칙이 문서가 아닌 코드가 됩니다.
* 상용 도구로는 `import-linter`(계약 파일로 선언) 가 같은 일을 합니다. 원리를 배우기 위해 직접 작성했습니다.

### 4. 이름 사용 검사 — `ast.Name`

```python
used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
assert "HTTPException" not in used_names
```

* 변수·함수·클래스 참조는 `ast.Name(id=...)`. 속성 접근(`fastapi.HTTPException`) 은 `ast.Attribute(attr=...)` 로 따로 잡아야 합니다.

### 5. 자주 쓰는 노드

| 노드 | 소스 |
|---|---|
| `ast.FunctionDef` / `AsyncFunctionDef` | `def f(...)` — `.name`, `.args`, `.decorator_list`, `.returns` |
| `ast.ClassDef` | `class C(Base)` — `.bases` |
| `ast.Call` | `f(x)` — `.func`, `.args`, `.keywords` |
| `ast.Constant` | 리터럴 — `.value` |
| `ast.Raise` | `raise X` |
| `ast.Try` | try 문 — `.handlers`(ExceptHandler), `.orelse`, `.finalbody` |

### 6. 다른 활용 예

* **데코레이터 검사**: "모든 라우터 함수에 `response_model` 이 있는가"
  ```python
  for node in ast.walk(tree):
      if isinstance(node, ast.FunctionDef):
          for deco in node.decorator_list:
              if isinstance(deco, ast.Call) and not any(k.arg == "response_model" for k in deco.keywords): ...
  ```
* **타입 힌트 누락 찾기**: `node.returns is None` 인 FunctionDef.
* **`except Exception` 금지**: `ast.ExceptHandler` 의 `.type` 이 `Name(id="Exception")` 인데 `# noqa` 가 없는 경우.
* `ast.literal_eval("[1, 2]")` — `eval` 없이 리터럴만 안전하게 평가.

### 7. `ast.unparse` — 트리를 다시 코드로 (3.9+)

```python
print(ast.unparse(node))      # 노드를 소스 문자열로 — 디버깅·코드 생성에 유용
print(ast.dump(tree, indent=2))   # 트리 구조 확인
```

### 8. 한계

* 동적 import(`importlib.import_module("backend." + name)`) 는 잡지 못합니다.
* 문법 오류가 있는 파일은 `SyntaxError` 로 파싱 실패 — 테스트가 그 사실 자체를 알려 주므로 오히려 유용합니다.

---

좋은 아키텍처는 **지켜지는지 확인할 수 있어야** 유지됩니다. 30 줄짜리 AST 테스트 하나가 "domain 은 프레임워크를 모른다 / usecases 는 HTTP 를 모른다" 는 두 문장을 매 커밋마다 증명합니다. ruff · mypy · black 같은 도구도 모두 같은 `ast` 위에서 동작합니다.
