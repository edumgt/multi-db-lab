> **쉽게 이해하기**
>
> - **한 줄 요약** — 함수를 다루는 도구 모음입니다. `lru_cache` 는 '한 번 계산한 결과를 기억', `cached_property` 는 '속성 값을 한 번만 계산'.
> - **비유하면** — 창고 열쇠를 처음 한 번만 만들고, 그 뒤로는 같은 열쇠를 계속 재사용하는 것.
> - **이 프로젝트에서는** — `clients.py` 가 DB 클라이언트를 `lru_cache` 로 감싸 연결을 한 번만 맺고 모든 요청이 공유합니다.
> - **기억할 것** — 인자가 있는 함수에 쓰면 인자 조합마다 따로 캐시됩니다. 테스트에서는 `cache_clear()` 로 비웁니다.

`functools` 모듈은 **함수와 메서드를 다루는 고차 도구** 를 제공합니다. 이 프로젝트에서는 `lru_cache` 로 DB 클라이언트를 싱글턴으로 만들고, `cached_property` 로 설정 파생 값을 한 번만 계산합니다.

---

### 1. `@lru_cache` — 인자 없는 함수에 붙이면 "지연 초기화 싱글턴"

```python
# backend/infrastructure/clients.py
@lru_cache
def mongo_client() -> MongoClient:
    client = MongoClient(settings.mongodb_uri)
    registry.register("mongo", client.close)
    return client
```

* 첫 호출에서만 본문이 실행되고 결과가 캐시됩니다. 이후 호출은 같은 객체를 돌려줍니다.
* **지연(lazy)**: import 시점이 아니라 **첫 요청** 시점에 연결합니다. Supabase 설정이 없는 환경에서도 앱은 정상 기동하고, 해당 엔드포인트를 호출할 때만 `ConfigurationError` 가 납니다.
* 모듈 전역 변수 방식(`client = MongoClient(...)`) 과 달리 import 부작용이 없고, 테스트에서 `mongo_client.cache_clear()` 로 초기화할 수 있습니다.

#### 주의
* 인자가 있는 함수에 쓰면 **인자 조합마다** 캐시됩니다. 인자는 해시 가능해야 합니다(list · dict 불가).
* `maxsize=None` 이 기본이 아닙니다. `@lru_cache` (괄호 없음) 는 `maxsize=128`. 인자 없는 함수는 조합이 1 개라 무관합니다.
* 캐시된 객체는 프로세스가 끝날 때까지 살아 있으므로, 연결 객체는 **반드시 종료 정리** 를 짝지어야 합니다 → `ResourceRegistry`.

### 2. `@cached_property` — 인스턴스 속성을 한 번만 계산

```python
# backend/infrastructure/settings.py
class Settings(BaseSettings):
    allowed_origins: str = "http://127.0.0.1:8001,http://localhost:8001"

    @cached_property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
```

* `@property` 는 접근마다 재계산, `@cached_property` 는 **첫 접근 결과를 인스턴스 `__dict__` 에 저장**.
* 문자열 split 로직이 main.py 와 다른 곳으로 흩어지는 것을 막고, 호출 측은 그냥 속성처럼 읽습니다.
* `slots=True` dataclass 에서는 `__dict__` 가 없어 사용할 수 없습니다(이 프로젝트의 엔티티에는 쓰지 않은 이유).

### 3. `functools.partial` — 인자를 미리 고정

```python
from functools import partial
make_redis_repo = partial(RedisLabRecordRepository, client=redis_client(), key_prefix="lab_record:")
repo = make_redis_repo()
```

* 이 프로젝트는 같은 목적을 `lambda` 전략 테이블(`deps.py`) 로 표현했습니다. 인자가 많거나 재사용이 잦으면 `partial` 이 더 읽기 좋습니다.

### 4. `functools.wraps` — 데코레이터 작성 시 메타데이터 보존

```python
def logged(fn):
    @wraps(fn)                        # __name__, __doc__, __annotations__ 를 fn 에서 복사
    def wrapper(*args, **kwargs):
        logger.info("call %s", fn.__name__)
        return fn(*args, **kwargs)
    return wrapper
```

* `wraps` 를 빼먹으면 FastAPI 처럼 **애너테이션을 읽는 프레임워크** 가 wrapper 의 시그니처를 보게 되어 의존성 주입이 깨집니다.

### 5. `functools.singledispatch` — 타입별 함수 오버로딩

```python
@singledispatch
def to_json(value): return str(value)
@to_json.register
def _(value: datetime): return value.isoformat()
```

* `json.dumps(default=...)` 의 변환 함수를 타입별로 깔끔하게 등록할 때 유용합니다.

### 6. `functools.reduce` · `total_ordering`

* `reduce` 는 누적 계산(합·곱). 대부분 `sum()` · 컴프리헨션이 더 읽기 좋습니다.
* `@total_ordering` 은 `__eq__` 와 `__lt__` 만 정의하면 나머지 비교 연산자를 채워 줍니다.

---

`lru_cache` 싱글턴 + 종료 레지스트리 조합은 "리소스를 **필요할 때** 만들고 **확실히** 닫는다" 를 간결하게 표현합니다. 과거 코드의 모듈 수준 `@atexit.register` 6 개를 `registry.close_all()` 한 줄로 대체한 것이 그 결과입니다.
