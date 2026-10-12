> **쉽게 이해하기**
>
> - **한 줄 요약** — 변수 · 인자 · 반환값의 타입을 적어 두면 IDE 와 mypy 가 실수를 미리 잡아 줍니다. 실행 속도나 동작에는 영향이 없습니다.
> - **비유하면** — 전선에 붙이는 색깔 라벨. 전기는 똑같이 흐르지만 잘못 연결하면 눈에 바로 보입니다.
> - **이 프로젝트에서는** — `str | None` · `list[str]` · `Literal["pagerank", "degree"]` 로 허용 값을 타입에 고정합니다. `mypy backend` 는 오류 0 입니다.
> - **기억할 것** — 3.10 이상에서는 `Optional[X]` 대신 `X | None` 을 씁니다.

파이썬 **타입 힌트(Type Hints)** 는 실행에 영향을 주지 않지만, `mypy` 같은 정적 검사기와 IDE 가 코드를 이해하는 근거가 됩니다. 이 프로젝트는 `mypy backend` 가 46 개 파일에서 오류 0 을 유지합니다. 사용한 기능을 정리합니다.

---

### 1. 기본 — 내장 제네릭과 `X | None` (3.10+)

```python
def find(self, employee_id: str, name: str) -> Employee | None: ...
tags: list[str]
payload: dict[str, Any]
```

* `typing.List`, `Optional[...]` 대신 내장 `list[...]`, `X | None` 을 씁니다.

### 2. `Literal` — 허용 값 집합을 타입으로

```python
# backend/domain/entities.py
type PostSortKey = Literal["created_at:desc", "views:desc", "id:desc", "id:asc"]
```

* 라우터의 Query 파라미터, 유스케이스, 게이트웨이의 `_ORDER_BY` dict 가 **같은 별칭**을 공유합니다.
* FastAPI 는 Literal 을 보고 허용되지 않은 값을 422 로 거절하고, mypy 는 오타를 정적으로 잡습니다.

### 3. `type` 문 — 타입 별칭 (PEP 695, 3.12+)

```python
type JsonObject = Mapping[str, Any]
type GraphAlgorithm = Literal["pagerank", "degree"]
```

* 이전의 `JsonObject: TypeAlias = ...` 보다 간결하고, 지연 평가되어 전방 참조에도 안전합니다.

### 4. `ClassVar` — 인스턴스가 아닌 클래스 속성

```python
class MongoLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "mongodb"
```

* dataclass 에서는 ClassVar 필드가 생성자 인자에서 **제외**됩니다. 검사기는 `instance.source = ...` 대입을 경고합니다.

### 5. `Final` — 재대입 금지 상수

```python
# backend/adapters/gateways/lab_clickhouse.py
COLUMNS: Final[tuple[str, ...]] = ("id", "title", "content", "tags")
```

* 이후 `COLUMNS = ...` 를 쓰면 mypy 오류. 런타임 강제는 없지만 의도를 명확히 합니다.

### 6. 추상 컬렉션 — `Mapping` · `Sequence` · `Iterable`

```python
@classmethod
def from_dict(cls, raw: Mapping[str, Any]) -> LabRecord: ...      # dict · RowMapping · pymongo 문서 모두 OK
def upsert(self, vector_id: str, values: Sequence[float], ...) -> None: ...   # list · tuple 모두 OK
def lab_records(records: Iterable[LabRecord], *, source: str) -> list[LabRecordRead]: ...
```

* **입력은 넓게(추상), 출력은 좁게(구체)** 가 원칙입니다. `Mapping` 은 읽기 전용이라는 의도도 전달합니다.

### 7. `Callable` — 함수 타입

```python
# backend/adapters/api/deps.py
LAB_REPOSITORY_FACTORIES: Final[dict[str, Callable[[], LabRecordRepository]]] = {
    "mongo": lambda: MongoLabRecordRepository(clients.mongo_collection()),
    ...
}
```

* `Callable[[인자타입들], 반환타입]`. 인자가 없으면 `[]`.

### 8. `Annotated` — 타입에 메타데이터 붙이기

```python
CurrentUser = Annotated[User, Depends(get_current_user)]
limit: Annotated[int, Query(ge=1, le=200)] = 20
```

* 검사기는 첫 인자(`User`, `int`)만 보고, FastAPI 는 두 번째 인자(의존성·검증 규칙)를 읽습니다. 한 선언으로 두 도구를 만족시킵니다.

### 9. `cast` — 검사기에게만 알려주기

```python
# backend/adapters/gateways/lab_redis.py
values = cast(list[str | None], self._client.mget(keys))
```

* 런타임 비용 0. 서드파티 스텁이 부정확할 때(redis-py 는 동기/비동기가 같은 스텁 → `Awaitable | Any`) 사용합니다.
* 남용 금지: cast 가 거짓이면 검사기는 속지만 런타임은 터집니다. 이 프로젝트는 cast 마다 **이유를 주석**으로 남겼습니다.

### 10. 키워드 전용 인자 `*`

```python
def update(self, post_id: int, *, title: str | None, content: str | None) -> Post: ...
```

* `*` 뒤의 인자는 반드시 이름으로 넘겨야 합니다. `update(1, "a", "b")` 처럼 순서를 헷갈리는 실수를 막습니다.

### 11. `Protocol` · `runtime_checkable`

* tech004 참고. 구조적 타입.

### 12. mypy 설정 — 계층별 엄격도

```ini
# mypy.ini
[mypy-backend.domain.*]
disallow_untyped_defs = True      # 도메인·유스케이스는 타입 누락 자체를 오류로
[mypy-backend.usecases.*]
disallow_untyped_defs = True
```

* 안쪽 원일수록 엄격하게, 서드파티와 맞닿는 바깥 원은 `ignore_missing_imports` 로 현실적으로.

---

타입 힌트는 "문서" 가 아니라 **실행되는 검사** 여야 가치가 있습니다. `pip install -r requirements-dev.txt && mypy backend` 를 CI 에 넣으면, `Literal` 에 정렬 키를 추가했는데 `_ORDER_BY` dict 를 빠뜨리는 류의 버그를 코드 리뷰 전에 잡을 수 있습니다.
