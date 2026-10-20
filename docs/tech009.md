> **쉽게 이해하기**
>
> - **한 줄 요약** — `with` 블록을 어떻게 빠져나가든(정상 · return · 예외) 정리 코드가 반드시 실행되게 하는 장치입니다.
> - **비유하면** — 자동문. 들어가면 열리고(enter), 나오면 무조건 닫힙니다(exit). 뛰어나가도, 넘어져도.
> - **이 프로젝트에서는** — `with SessionLocal() as db` (세션), `with engine.begin()` (성공하면 commit · 실패하면 rollback), `lifespan` (앱 시작 · 종료) 에 씁니다.
> - **기억할 것** — `@contextmanager` 를 붙이면 함수 하나로도 만들 수 있습니다. `yield` 는 딱 한 번.

**컨텍스트 매니저(`with` 문)** 는 "진입 시 준비, 종료 시 정리" 를 보장하는 파이썬의 자원 관리 도구입니다. 이 프로젝트에서는 DB 세션 · 트랜잭션 · 앱 수명주기(lifespan) 에 사용합니다.

---

### 1. `with` 문의 의미

```python
with open("f.txt") as f:
    data = f.read()
# 블록을 어떻게 벗어나든(정상 · return · 예외) f.close() 가 호출됨
```

* `__enter__()` 반환값이 `as` 변수에 바인딩되고, `__exit__(exc_type, exc, tb)` 가 종료 시 호출됩니다.
* `__exit__` 가 `True` 를 돌려주면 예외가 **억제** 됩니다(드물게 사용).

### 2. SQLAlchemy — 트랜잭션 경계

```python
# backend/adapters/gateways/lab_postgres.py
with self._engine.begin() as conn:
    conn.execute(insert(self._table).values(**record.to_dict()))
# 정상 종료 → COMMIT, 예외 → ROLLBACK, 어느 쪽이든 커넥션 반환
```

* `try/except/finally` 로 commit/rollback/close 를 손으로 쓰는 것보다 짧고 빠뜨릴 수 없습니다.

```python
# backend/main.py
with SessionLocal() as db:
    admin = build_auth_usecase(db).ensure_user(*SEED_ADMIN)
```

### 3. 제너레이터 기반 컨텍스트 매니저 — `@contextmanager`

```python
from contextlib import contextmanager

@contextmanager
def timer(label: str):
    start = time.perf_counter()
    try:
        yield                       # 여기서 with 블록 실행
    finally:
        logger.info("%s took %.3fs", label, time.perf_counter() - start)
```

* `yield` 앞 = `__enter__`, 뒤 = `__exit__`. 클래스를 만들지 않고 함수 하나로 끝납니다.

### 4. FastAPI 의존성 — "yield 의존성" 도 같은 모양

```python
# backend/infrastructure/orm.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db                    # 요청 처리
    finally:
        db.close()                  # 응답 후 반드시
```

* FastAPI 가 이 제너레이터를 컨텍스트 매니저처럼 다룹니다. 요청당 세션 하나, 커넥션 누수 없음.

### 5. 비동기 — `@asynccontextmanager` 와 lifespan

```python
# backend/main.py
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        Base.metadata.create_all(bind=engine)      # startup
        seed_data()
        yield
    finally:
        registry.close_all()                        # shutdown — startup 이 실패해도 실행
        engine.dispose()

app = FastAPI(lifespan=lifespan)
```

* `@app.on_event("startup"/"shutdown")` 은 deprecated. lifespan 하나로 **시작과 종료를 한 함수에** 둡니다.
* `try/finally` 로 감싸 startup 도중 예외가 나도 정리 코드가 실행됩니다.

### 6. Neo4j 세션

```python
# backend/adapters/gateways/graph_neo4j.py
with self._driver.session(database=self._database) as session:
    record = session.run("MERGE (n:Entity {id: $id}) ...", id=node.id).single()
```

### 7. 여러 자원을 한 번에 — `ExitStack`

```python
from contextlib import ExitStack
with ExitStack() as stack:
    conns = [stack.enter_context(engine.connect()) for engine in engines]
    ...   # 모두 역순으로 닫힘
```

* 자원 개수가 런타임에 결정될 때 사용합니다. 이 프로젝트의 `ResourceRegistry.close_all()` 은 같은 아이디어(LIFO 정리)를 앱 수명 전체에 적용한 변형입니다.

### 8. 기타 유용한 `contextlib` 도구

| 도구 | 용도 |
|---|---|
| `suppress(FileNotFoundError)` | 특정 예외를 조용히 무시 (`try/except: pass` 대체) |
| `closing(obj)` | `close()` 만 있는 객체를 with 로 |
| `redirect_stdout(f)` | 출력 리디렉션 |
| `nullcontext()` | 조건부로 컨텍스트 매니저를 쓸 때 "아무것도 안 하는" 자리표시자 |

---

"열었으면 닫는다" 를 **코드 구조로 강제** 하는 것이 컨텍스트 매니저의 가치입니다. 이 프로젝트에서 수동 `close()` 호출은 `ResourceRegistry` 내부 한 곳에만 있고, 나머지는 모두 `with` 또는 `yield` 의존성이 책임집니다.
