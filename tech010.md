파이썬에서 함수는 **일급 객체(first-class object)** 입니다. 변수에 담고, 인자로 넘기고, 반환하고, dict 의 값으로 둘 수 있습니다. 이 프로젝트의 의존성 조립(`backend/adapters/api/deps.py`) 과 라우터 생성(`lab_router.py`) 은 이 성질을 적극적으로 사용합니다.

---

### 1. 클로저(Closure) — 바깥 변수를 기억하는 함수

```python
# backend/adapters/api/deps.py
def get_lab_usecase(source: str) -> Callable[[], LabRecordUseCase]:
    factory = LAB_REPOSITORY_FACTORIES[source]

    def _provide() -> LabRecordUseCase:
        return LabRecordUseCase(factory())        # factory, source 를 '기억'
    _provide.__name__ = f"get_{source}_lab_usecase"
    return _provide
```

* `_provide` 는 `get_lab_usecase` 가 끝난 뒤에도 `factory` 를 참조합니다. 이것이 클로저입니다.
* FastAPI `Depends()` 는 **인자 없는 함수** 를 원하므로, "source 가 고정된 함수" 를 동적으로 만들어 주는 **팩토리 함수** 가 필요했습니다.
* `__name__` 을 바꿔 둔 이유: 디버깅·OpenAPI 에서 7 개 함수가 전부 `_provide` 로 보이면 구분이 안 됩니다.

### 2. 전략 테이블 — `if/elif` 대신 dict 의 값으로 함수

```python
LAB_REPOSITORY_FACTORIES: Final[dict[str, Callable[[], LabRecordRepository]]] = {
    "mongo":      lambda: MongoLabRecordRepository(clients.mongo_collection()),
    "postgres":   lambda: PostgresLabRecordRepository(clients.lab_postgres_engine(), clients.lab_records_table),
    "redis":      lambda: RedisLabRecordRepository(clients.redis_client(), settings.redis_key_prefix),
    ...
}
```

* `lambda:` 로 감싼 이유 — dict 를 만드는 **import 시점** 에 클라이언트를 생성하지 않고, 키를 조회해 **호출할 때** 생성하기 위해서입니다(지연 평가).
* 과거 코드의 `if provider == "pinecone": ... elif provider == "weaviate": ...` 체인은 `VECTOR_STORE_FACTORIES` dict 한 개로 바뀌었습니다. 새 provider 추가 = 한 줄 추가(개방-폐쇄 원칙).

### 3. 함수를 돌려주는 함수로 라우터 생성

```python
# backend/adapters/api/lab_router.py
def _build_record_router(source: str) -> APIRouter:
    sub = APIRouter(prefix=f"/{source}/records")
    provider = get_lab_usecase(source)

    @sub.post("")
    def create_record(payload: LabRecordCreate, uc: LabRecordUseCase = Depends(provider)):
        return presenters.lab_record(uc.create(payload.to_entity()), source=uc.source)
    ...
    return sub

for _source in LAB_REPOSITORY_FACTORIES:          # dict 의 키가 곧 URL 세그먼트
    router.include_router(_build_record_router(_source))
```

* 28 개였던 라우터 함수가 4 개 정의 × 7 회 호출로 줄었습니다.
* 루프 변수 캡처 함정: `for s in ...: def f(): return s` 처럼 **루프 변수를 직접 클로저에 넣으면** 마지막 값만 남습니다. 함수 호출(`_build_record_router(_source)`) 로 감싸면 호출마다 새 스코프가 생겨 안전합니다.

### 4. 콜백 등록 — bound method 를 값으로

```python
# backend/infrastructure/clients.py
registry.register("mongo", client.close)         # 호출하지 않고 메서드 '자체' 를 등록
...
closer()                                          # 나중에 호출
```

* `client.close` (괄호 없음) 는 바운드 메서드 객체. `client.close()` 와 혼동하지 마세요.
* Cassandra 처럼 두 단계 정리가 필요하면 지역 함수를 만들어 등록합니다.
  ```python
  def _shutdown() -> None:
      session.shutdown(); cluster.shutdown()
  registry.register("cassandra", _shutdown)
  ```

### 5. 고차 함수 표준 도구

| 도구 | 예 |
|---|---|
| `map` / `filter` | 보통 컴프리헨션이 더 읽기 좋음 |
| `sorted(key=...)` | `sorted(posts, key=lambda p: p.views, reverse=True)` |
| `functools.partial` | 인자 일부 고정 (tech008) |
| 데코레이터 | 함수를 받아 함수를 돌려주는 함수 — `@router.get`, `@lru_cache`, `@abstractmethod` 모두 데코레이터 |

### 6. `nonlocal` — 클로저가 바깥 변수를 **수정** 할 때

```python
def counter():
    n = 0
    def inc():
        nonlocal n          # 없으면 n 은 inc 의 지역 변수로 취급되어 UnboundLocalError
        n += 1
        return n
    return inc
```

* 읽기만 할 때는 필요 없고, 재대입할 때만 필요합니다. 이 프로젝트의 클로저는 모두 읽기 전용입니다.

---

"함수를 값처럼 다룬다" 는 감각이 생기면, 분기문 대신 테이블을, 복사-붙여넣기 대신 생성 함수를 쓰게 됩니다. 500 줄의 `lab_router.py` 가 100 줄로 줄어든 핵심 기법이 바로 클로저와 전략 테이블입니다.
