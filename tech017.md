> **쉽게 이해하기**
>
> - **한 줄 요약** — `assert` 만으로 테스트를 쓰는 표준 도구입니다. 픽스처(준비물) · 파라미터화(같은 테스트, 여러 입력) · 예외 검증을 제공합니다.
> - **비유하면** — 자동 채점기. 답안(함수) 을 넣으면 정답표(assert) 와 비교해 줍니다.
> - **이 프로젝트에서는** — DB 없이 가짜 저장소(`tests/fakes.py`) 로 유스케이스를 2 초 안에 검사합니다. `pytest.raises(NotFoundError)` 로 '예외가 나야 성공' 을 표현합니다.
> - **기억할 것** — 테스트 함수는 `test_` 로, 파일은 `test_*.py` 로 시작해야 pytest 가 찾습니다.

**pytest** 는 파이썬의 사실상 표준 테스트 프레임워크입니다. `assert` 문만으로 테스트를 쓰고, 픽스처 · 파라미터화 · 예외 검증을 제공합니다. 이 프로젝트의 `tests/` 는 DB 없이 2 초 안에 17 개 테스트를 돌립니다.

---

### 1. 기본 규칙

* 파일명 `test_*.py`, 함수명 `test_*` 이면 자동 수집됩니다.
* 검증은 평범한 `assert`. 실패 시 pytest 가 양쪽 값을 **자동으로 풀어서** 보여줍니다(assertion rewriting).

```python
# tests/test_usecases.py
def test_lab_update_rejects_empty_patch() -> None:
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    with pytest.raises(ValidationError):
        uc.update("any", LabRecordPatch())
```

### 2. `pytest.raises` — 예외가 나야 성공

```python
with pytest.raises(NotFoundError):
    uc.delete("missing")

with pytest.raises(TypeError):
    Incomplete()                 # ABC 미구현 → 인스턴스화 불가
```

* `as exc_info` 로 예외 객체를 받아 속성을 추가 검증할 수 있습니다: `exc_info.value.detail`.
* `match="정규식"` 으로 메시지도 검사 가능.

### 3. `@pytest.mark.parametrize` — 같은 테스트를 여러 입력으로

```python
# tests/test_architecture.py
@pytest.mark.parametrize("layer", ["domain", "usecases", "adapters", "infrastructure"])
def test_layer_imports_point_inward(layer: str) -> None: ...
```

* 4 개의 독립 테스트로 보고됩니다(`test_layer_imports_point_inward[domain]` …). 하나가 실패해도 나머지는 계속 실행됩니다.

### 4. `conftest.py` — 공통 설정

```python
# tests/conftest.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))          # `import backend` 가 되도록
```

* 같은 디렉터리 이하의 모든 테스트에 자동 적용됩니다. 픽스처를 여기에 정의하면 import 없이 쓸 수 있습니다.

### 5. 픽스처 — 준비/정리 코드 재사용

```python
@pytest.fixture
def auth() -> AuthUseCase:
    return AuthUseCase(InMemoryUserRepository(), PlainTextHasher(), StaticTokenProvider())

def test_login(auth: AuthUseCase) -> None:        # 인자 이름으로 주입
    auth.ensure_user("admin", "pw")
    assert auth.authenticate(auth.login("admin", "pw")).username == "admin"
```

* `yield` 픽스처는 테스트 후 정리 코드를 실행합니다(컨텍스트 매니저와 같은 모양 — tech009).
* `scope="session"` 으로 비싼 자원(DB 컨테이너) 을 한 번만 만들 수 있습니다.
* 내장 픽스처: `tmp_path`(임시 디렉터리), `caplog`(로그 캡처), `monkeypatch`(환경변수·속성 임시 변경).

### 6. 테스트 더블 — 포트의 인메모리 구현

```python
# tests/fakes.py
class InMemoryLabRecordRepository(LabRecordRepository):     # 실제 포트(ABC) 를 상속
    source: ClassVar[str] = "memory"
    def __init__(self) -> None:
        self._rows: dict[str, LabRecord] = {}
    ...
```

* `unittest.mock.MagicMock` 대신 **진짜 계약(ABC) 을 구현한 가짜** 를 씁니다. 포트에 메서드가 추가되면 가짜도 함께 컴파일 오류(TypeError) 가 나므로 테스트가 실제 코드와 어긋나지 않습니다.
* `PlainTextHasher` 는 bcrypt(수백 ms) 를 피해 테스트를 빠르게 합니다. **운영 코드에서 절대 사용 금지** 라고 docstring 에 명시했습니다.

### 7. FastAPI 통합 테스트 — `TestClient`

```python
from fastapi.testclient import TestClient
client = TestClient(app)                   # lifespan 미실행 → PostgreSQL 없이 lab 엔드포인트 확인 가능
r = client.patch("/lab/redis/records/t1", json={})
assert r.status_code == 400 and r.json()["error"] == "ValidationError"

with TestClient(app) as client: ...         # with 를 쓰면 lifespan(startup/shutdown) 실행
```

* 의존성 교체: `app.dependency_overrides[get_lab_usecase("redis")] = lambda: LabRecordUseCase(InMemoryLabRecordRepository())` 로 실제 Redis 없이 라우터까지 테스트할 수 있습니다.

### 8. 유용한 실행 옵션

```bash
pytest tests -q                 # 간결 출력
pytest -x                       # 첫 실패에서 중단
pytest -k "lab and not limit"   # 이름으로 선택
pytest --lf                     # 마지막에 실패한 것만
pytest -vv                      # assert 비교 전체 출력
pytest --durations=5            # 느린 테스트 5 개
```

### 9. 테스트 피라미드와 이 프로젝트

| 층 | 대상 | 속도 | 파일 |
|---|---|---|---|
| 단위 | 엔티티 · 예외 · 유스케이스 | ms | `test_domain.py`, `test_usecases.py` |
| 아키텍처 | import 방향 | ms | `test_architecture.py` |
| 통합 | 게이트웨이 + 실제 DB | 초 | (TestClient + 로컬 컨테이너로 수동 검증) |

---

클린 아키텍처의 가장 즉각적인 보상은 **테스트 속도** 입니다. 비즈니스 규칙이 포트(ABC) 뒤에 있으므로 13 개 DB 중 어느 것도 띄우지 않고 규칙 전체를 검증할 수 있습니다. `pytest tests` 가 2 초면, 개발자는 저장할 때마다 돌립니다.
