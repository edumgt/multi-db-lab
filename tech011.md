> **쉽게 이해하기**
>
> - **한 줄 요약** — `yield` 로 값을 하나씩 꺼내 주는 함수입니다. 전부를 메모리에 올리지 않습니다.
> - **비유하면** — 자판기. 버튼을 누를 때마다 하나씩 나오고, 한꺼번에 다 쏟아내지 않습니다.
> - **이 프로젝트에서는** — `get_db()` 가 세션을 yield 하고 요청이 끝나면 닫습니다. Redis `scan_iter` 로 키를 조금씩 순회합니다.
> - **기억할 것** — 제너레이터는 한 번 다 돌면 끝입니다. 다시 쓰려면 새로 만들어야 합니다.

**제너레이터(generator)** 는 `yield` 로 값을 하나씩 내보내는 함수이며, **이터레이터 프로토콜** 은 `for` 문이 동작하는 원리입니다. 이 프로젝트에서는 요청 단위 DB 세션(`get_db`), Redis `scan_iter`, 테스트용 id 발급(`itertools.count`) 에 사용합니다.

---

### 1. 이터레이터 프로토콜

* `for x in obj` 는 내부적으로 `it = iter(obj)` 후 `next(it)` 를 `StopIteration` 까지 반복합니다.
* `__iter__` 와 `__next__` 를 구현하면 어떤 객체든 for 문에 쓸 수 있습니다. 제너레이터는 이것을 자동으로 만들어 줍니다.

### 2. 제너레이터 함수 — `yield`

```python
def countdown(n):
    while n > 0:
        yield n          # 값을 내보내고 '일시 정지'
        n -= 1

list(countdown(3))       # [3, 2, 1]
```

* 호출 즉시 실행되지 않고 **제너레이터 객체** 를 돌려줍니다. `next()` 가 호출될 때마다 다음 `yield` 까지 실행합니다.
* **지연 평가(lazy)**: 전체를 메모리에 올리지 않습니다. 100 만 건을 순회해도 한 번에 하나만 존재합니다.

### 3. 자원 관리용 제너레이터 — 한 번만 yield

```python
# backend/infrastructure/orm.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db          # FastAPI 가 이 값을 라우터에 주입하고, 응답 후 다시 next() 를 호출
    finally:
        db.close()        # 두 번째 next() 에서 StopIteration 직전 실행
```

* 반환 타입 `Generator[YieldType, SendType, ReturnType]`. send/return 을 쓰지 않으면 `None, None`.
* 더 간단히 `Iterator[Session]` 으로 써도 됩니다.

### 4. Redis `scan_iter` — 서버를 블로킹하지 않는 순회

```python
# backend/adapters/gateways/lab_redis.py
for key in self._client.scan_iter(match=f"{self._prefix}*", count=100):
    keys.append(key)
    if len(keys) >= limit:
        break             # 제너레이터는 여기서 멈추고 더 이상 서버에 요청하지 않음
```

* `KEYS *` 는 전체를 한 번에 가져오며 Redis 를 멈춥니다. `SCAN` 은 커서 기반으로 조금씩 가져오고, redis-py 가 이를 제너레이터로 감쌉니다.
* `break` 로 조기 종료가 가능한 것이 제너레이터의 장점입니다.

### 5. `itertools` — 이터레이터 조합 도구

```python
# tests/fakes.py
from itertools import count
self._ids = count(1)           # 1, 2, 3, ... 무한 제너레이터
user = User(id=next(self._ids), ...)
```

| 도구 | 용도 |
|---|---|
| `count(start)` | 무한 카운터 (DB 의 auto-increment 흉내) |
| `chain(a, b)` | 여러 이터러블을 이어 붙임 |
| `islice(it, n)` | 제너레이터에서 앞 n 개만 |
| `groupby` | 정렬된 데이터를 키별 묶음 |
| `zip_longest` | 길이가 다른 시퀀스 zip |

### 6. 제너레이터 표현식 — 메모리 절약형 컴프리헨션

```python
total = sum(len(r.content) for r in records)     # 리스트를 만들지 않음
any(r.id == "x" for r in records)                 # 찾는 즉시 중단
```

* `[...]` 대신 `(...)`. `sum`, `any`, `all`, `max`, `", ".join()` 에 바로 넘길 때 사용합니다.
  ```python
  # backend/adapters/gateways/lab_clickhouse.py
  set_clause = ", ".join(f"{key} = {{{key}:String}}" for key in changes)
  ```

### 7. `yield from` — 하위 제너레이터 위임

```python
def all_records():
    yield from mongo_repo.list(100)
    yield from redis_repo.list(100)
```

### 8. 제너레이터의 한계

* **한 번만** 순회할 수 있습니다. 두 번 돌리려면 `list()` 로 고정하세요.
* `len()` 이 없습니다.
* 예외가 나면 그 지점에서 종료되고 재시작할 수 없습니다.

---

`get_db` 의 `try / yield / finally` 패턴은 "요청 전후에 반드시 실행할 코드" 를 가장 짧게 표현하는 파이썬 관용구입니다. 같은 모양이 `@contextmanager`(tech009) 와 FastAPI 의 lifespan 에도 반복됩니다 — **한 번 yield 하는 제너레이터 = 컨텍스트 매니저** 라고 기억하면 세 가지가 한 번에 이해됩니다.
