> **쉽게 이해하기**
>
> - **한 줄 요약** — 함수나 메서드를 일반 변수처럼 딕셔너리에 담거나 다른 함수의 인자(콜백)로 넘겨서 실행할 수 있습니다.
> - **비유하면** — 요리 레시피 카드(함수)를 메뉴판(dict)에 꽂아 두고, 손님이 주문하면 꺼내서 요리하는 것.
> - **이 프로젝트에서는** — DB 종류별로 저장소를 고르는 팩토리 테이블(`LAB_REPOSITORY_FACTORIES`)과 서버 종료 시 DB 연결을 닫는 콜백 등록(`registry.register("mongo", client.close)`)에 쓰입니다.
> - **기억할 것** — 함수 뒤에 괄호`()`를 붙이지 않고 이름만 쓰면 "실행"이 아니라 "함수 자체를 전달"하는 것입니다.

파이썬에서 함수는 **일급 객체(First-class Object)** 입니다. 숫자나 문자열처럼 변수에 담을 수도 있고, 다른 함수의 인자로 넘길 수도 있으며, 딕셔너리의 값으로 저장할 수도 있습니다.

함수를 인자로 받거나 함수를 돌려주는 함수를 **고차 함수(Higher-Order Function)** 라고 부르며, 일급 함수 성질이 있어야 가능한 기법입니다. 먼저 고차 함수의 전체 그림을 잡고, 이어서 이 프로젝트가 실제로 쓰는 3가지 기법(클로저, 전략 테이블, 바운드 메서드 콜백)을 정리합니다.

---

### 1. 고차 함수(Higher-Order Function) — "함수를 다루는 함수"

**고차 함수** 는 다음 둘 중 하나 이상을 하는 함수입니다.

1. **함수를 인자로 받는다** — "무엇을 할지" 를 호출하는 쪽이 끼워 넣을 수 있게 한다 (콜백 · 전략)
2. **함수를 결과로 돌려준다** — 설정값을 미리 채워 둔 "맞춤 함수" 를 찍어낸다 (팩토리 · 클로저 · 데코레이터)

함수가 일급 객체이기 때문에 가능한 일이며, 이 프로젝트에는 두 종류가 모두 있습니다.

| 종류 | 이 프로젝트의 예 | 어디에 |
|---|---|---|
| 함수를 **받는** 고차 함수 | `registry.register("mongo", client.close)` | `infrastructure/clients.py` |
| | `Depends(provider)` — FastAPI 가 요청마다 `provider()` 를 호출 | `adapters/api/lab_router.py` |
| 함수를 **돌려주는** 고차 함수 | `get_lab_usecase("mongo")` → 인자 없는 `_provide` 함수 | `adapters/api/deps.py` |
| **둘 다** (받아서 새 함수를 돌려줌) | `@lru_cache` · `@sub.post("")` 데코레이터 | `clients.py` · 모든 라우터 |

#### 1-1. 표준 라이브러리의 대표 고차 함수

```python
records = [{"id": "b", "title": "zeta", "views": 3}, {"id": "a", "title": "alpha", "views": 9}]

sorted(records, key=lambda r: r["title"])          # key 자리에 "비교 기준을 만드는 함수" 를 넘김
max(records, key=lambda r: r["views"])              # 가장 많이 본 레코드
list(map(str.upper, ["a", "b"]))                    # ['A', 'B'] — 각 원소에 함수 적용
list(filter(None, ["", "x"]))                       # ['x']      — 참인 것만 남김 (None 은 "그 자체로 판단")
functools.reduce(lambda acc, n: acc + n, [1, 2, 3]) # 6          — 누적
```

* `key=` 에는 **값 하나를 받아 비교용 값을 돌려주는 함수** 를 넘깁니다. `lambda r: r["title"]` 대신 `operator.itemgetter("title")`, 객체라면 `operator.attrgetter("title")` 을 쓰면 더 빠르고 읽기 쉽습니다.
* `map` · `filter` 는 **지연 평가(lazy)** 이터레이터를 돌려주므로 `list()` 로 감싸야 결과가 나옵니다 (tech011 제너레이터 참고).
* 파이썬에서는 `map(f, xs)` · `filter(p, xs)` 보다 **컴프리헨션** `[f(x) for x in xs if p(x)]` 이 관용적입니다. 이 프로젝트도 `lab_redis.py` 의 `[self._load(raw, key=key) for key, raw in zip(keys, values) if raw]` 처럼 컴프리헨션을 씁니다. `map` 은 `map(str.upper, xs)` 처럼 **이미 있는 함수를 그대로 넘길 때** 만 간결합니다.

#### 1-2. 데코레이터 = "함수를 받아 함수를 돌려주는" 고차 함수

`@` 문법은 고차 함수 호출의 **설탕(syntactic sugar)** 입니다.

```python
@lru_cache
def mongo_collection() -> Collection: ...

# 위 코드는 아래와 완전히 같습니다
def mongo_collection() -> Collection: ...
mongo_collection = lru_cache(mongo_collection)     # 함수를 받아 → 캐시가 붙은 새 함수를 돌려받아 → 같은 이름에 다시 묶음
```

직접 만들 때의 기본 꼴입니다. `functools.wraps` 를 빼먹으면 `__name__` · docstring 이 `wrapper` 로 바뀌어 FastAPI 문서와 로그에 엉뚱한 이름이 찍힙니다.

```python
from functools import wraps

def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)                                      # 원래 함수의 이름 · docstring · 시그니처 정보를 복사
    def wrapper(*args, **kwargs) -> T:
        logger.info("call %s", fn.__name__)
        return fn(*args, **kwargs)
    return wrapper

@logged
def add(a: int, b: int) -> int:
    return a + b

add(1, 2)          # 로그: call add  → 3
add.__name__       # 'add' (wraps 덕분. 없으면 'wrapper')
```

`@sub.post("", response_model=LabRecordRead)` 처럼 **괄호가 붙은 데코레이터** 는 한 단계 더 있는 "데코레이터 팩토리" 입니다. `sub.post("")` 가 먼저 호출되어 데코레이터를 **돌려주고**, 그 데코레이터가 핸들러 함수를 **받습니다** — 고차 함수가 고차 함수를 돌려주는 2단 구조입니다.

```python
def route(path: str):                 # 1단: 설정값을 받아
    def decorator(fn):                # 2단: 함수를 받아
        fn.path = path                #      (함수는 객체라 속성을 붙일 수 있음)
        return fn                     #      함수를 돌려줌
    return decorator

@route("/x")
def handler(): ...
handler.path   # '/x'
```

#### 1-3. `lambda` — 한 줄 익명 함수, 언제 쓰고 언제 피할까

```python
"mongo": lambda: MongoLabRecordRepository(clients.mongo_collection()),
```

* `lambda 인자: 표현식` — **표현식 하나** 만 올 수 있고 `return` · 여러 줄 · 주석 · docstring 이 불가합니다.
* **쓰기 좋은 곳**: `key=` 인자, 전략 테이블의 값처럼 "한 줄짜리 함수를 그 자리에서 바로 넘길 때". 이름을 붙일 가치가 없을 만큼 짧을 때입니다.
* **`def` 로 바꿀 때**: 두 줄 이상이 되거나, 에러 트레이스백에서 이름이 보여야 하거나, 테스트에서 직접 import 해야 할 때. `name = lambda: ...` 처럼 **변수에 담는 람다는 그냥 `def` 로** 쓰는 것이 PEP 8 권고입니다 (트레이스백에 `<lambda>` 만 찍힘).

⚠️ **반복문 안의 람다 — 늦은 바인딩(late binding) 함정**

```python
fs = [lambda: i for i in range(3)]
[f() for f in fs]                 # [2, 2, 2]  — 전부 마지막 i 를 봄!
```
람다는 만들어질 때 `i` 의 **값** 을 복사하지 않고 **변수 `i` 자체** 를 참조합니다. 호출 시점의 `i` 는 이미 2 입니다. 고치는 방법은 두 가지입니다.

```python
fs = [lambda i=i: i for i in range(3)]            # ① 기본 인자로 "지금 값" 을 고정
def make(i): return lambda: i                     # ② 함수 호출로 새 스코프를 만들어 가둠 (클로저)
fs = [make(i) for i in range(3)]                  # [0, 1, 2]
```
이 프로젝트의 `LAB_REPOSITORY_FACTORIES` 는 **딕셔너리 리터럴에 람다를 하나씩 직접 적었기 때문에** 이 문제가 없습니다. 만약 `for source in SOURCES: table[source] = lambda: build(source)` 처럼 반복문으로 채웠다면 전부 마지막 DB 를 가리키는 버그가 났을 것입니다. `get_lab_usecase(source)` 가 **함수 호출로 `source` 를 가두는 ②번 방식** 인 것도 같은 이유입니다.

#### 1-4. 함수를 돌려주는 두 가지 방법 — 클로저 vs `functools.partial`

"인자 일부를 미리 채운 함수" 를 만들 때는 클로저 외에 `partial` 도 있습니다.

```python
from functools import partial

to_int_from_binary = partial(int, base=2)       # int(x, base=2) 를 미리 채워 둔 함수
to_int_from_binary("101")                       # 5

# deps.py 의 클로저를 partial 로 흉내 내면
def build_usecase(factory): return LabRecordUseCase(factory())
provider = partial(build_usecase, LAB_REPOSITORY_FACTORIES["mongo"])   # 동작은 하지만 __name__ 이 없음
```

| | 클로저 (`def _provide(): ...`) | `functools.partial` |
|---|---|---|
| 적합한 경우 | 호출 시점에 **추가 로직** 이 필요할 때 (`factory()` 를 새로 호출, 예외 변환 등) | 인자만 고정하면 끝일 때 |
| `__name__` | 있음 — `_provide.__name__ = f"get_{source}_lab_usecase"` 로 바꿀 수도 있음 | **없음** (partial 객체) — OpenAPI · 디버깅 시 이름이 안 보임 |
| 타입 검사 | `Callable[[], LabRecordUseCase]` 로 정확히 표현 | mypy 가 인자 고정을 비교적 잘 추론 |

이 프로젝트가 `get_lab_usecase` 를 클로저로 쓴 이유: ① 호출마다 `factory()` 로 **새 저장소 객체** 를 만들어야 하고, ② FastAPI 문서에 `get_mongo_lab_usecase` 같은 **읽을 수 있는 이름** 을 남기고 싶었기 때문입니다. 두 조건 모두 partial 로는 어렵습니다.

#### 1-5. 고차 함수의 타입 힌트 — `Callable`

```python
from typing import Callable

Callable[[], LabRecordRepository]        # 인자 없음 → LabRecordRepository 를 돌려줌 (팩토리)
Callable[[str], None]                     # str 하나 받고 → 아무것도 안 돌려줌 (콜백)
Callable[[str, int], bool]                # 두 인자
Callable[..., object]                     # 인자는 아무것이나 (`...`), 반환만 명시
```

* 대괄호 **첫 칸은 인자 타입의 리스트**, 둘째 칸은 반환 타입입니다. 인자가 없으면 빈 리스트 `[]`.
* 바운드 메서드 `client.close` 는 `self` 가 이미 묶여 있으므로 `Callable[[], object]` 에 그대로 들어맞습니다 — `ResourceRegistry.register` 의 시그니처가 이것입니다.
* 키워드 인자나 기본값까지 표현하려면 `Callable` 로는 부족하고, `__call__` 메서드를 가진 `Protocol` 을 씁니다 (tech004 참고).
* 파이썬 3.12 부터는 `type RepoFactory = Callable[[], LabRecordRepository]` 로 별칭을 만들어 전략 테이블 타입 `dict[str, RepoFactory]` 를 짧게 쓸 수 있습니다.

#### 1-6. 한 장 요약

| 하고 싶은 것 | 고차 함수 도구 |
|---|---|
| 정렬 · 최대/최소 기준 바꾸기 | `sorted / max / min` 의 `key=` |
| 원소마다 같은 변환 | 컴프리헨션 (기존 함수를 그대로 쓸 땐 `map`) |
| "나중에 이걸 실행해 줘" 를 등록 | 콜백 인자 (`register(name, closer)`) |
| 설정값을 품은 함수를 찍어내기 | 클로저 팩토리 (`get_lab_usecase`) · `partial` |
| 기존 함수에 기능을 덧씌우기 | 데코레이터 (`@lru_cache`, `@wraps` 로 직접 제작) |
| 문자열 → 동작 매핑 | 전략 테이블 `dict[str, Callable]` (3번) |

---

### 2. 클로저(Closure) — "바깥 변수를 기억하는 함수"

함수 안에 또 다른 함수를 만들 때, 안쪽 함수가 **바깥쪽 함수의 변수를 가방에 챙겨서 기억하는 것**을 클로저라고 합니다.

```python
# backend/adapters/api/deps.py
def get_lab_usecase(source: str) -> Callable[[], LabRecordUseCase]:
    factory = LAB_REPOSITORY_FACTORIES[source]

    def _provide() -> LabRecordUseCase:
        # 바깥 함수가 끝난 뒤에도 factory와 source를 잊지 않고 '기억'해서 사용!
        return LabRecordUseCase(factory())
        
    return _provide  # 실행하지 않고 함수 자체를 반환
```

* **왜 쓰나요?**: FastAPI의 `Depends()`는 인자가 없는 함수만 받습니다. 그래서 "어떤 DB인지(`source`)를 미리 기억해 둔 인자 없는 함수"를 동적으로 찍어내기 위해 클로저를 사용했습니다.

---

### 3. 전략 테이블(Strategy Table) — 지저분한 `if/elif` 없애기

데이터베이스 종류가 7개일 때, `if/elif` 문으로 분기하면 코드가 길고 지저분해집니다.
파이썬에서는 **딕셔너리의 값 자리에 함수를 직접 넣어두는 '전략 테이블'** 로 깔끔하게 해결합니다.

#### ❌ 적용 전 (지저분한 분기문)
```python
if source == "mongo":
    repo = MongoLabRecordRepository(...)
elif source == "redis":
    repo = RedisLabRecordRepository(...)
elif source == "postgres":
    repo = PostgresLabRecordRepository(...)
# DB가 늘어날 때마다 if 문이 끝없이 늘어남...
```

#### ⭕ 적용 후: 딕셔너리에 함수(람다)를 모아두기
```python
# backend/adapters/api/deps.py
LAB_REPOSITORY_FACTORIES: Final[dict[str, Callable[[], LabRecordRepository]]] = {
    "mongo":    lambda: MongoLabRecordRepository(clients.mongo_collection()),
    "postgres": lambda: PostgresLabRecordRepository(...),
    "redis":    lambda: RedisLabRecordRepository(...),
}

# 꺼내서 호출할 때는 단 한 줄!
repo_factory = LAB_REPOSITORY_FACTORIES[source]
repo = repo_factory()
```
* **새로운 DB 추가가 쉬움**: 새 DB가 추가되어도 기존 로직을 건드리지 않고 딕셔너리에 딱 한 줄만 추가하면 됩니다. (개방-폐쇄 원칙, OCP)

---

### 4. 바운드 메서드(Bound Method)와 콜백(Callback) 등록 패턴

#### 💡 바운드 메서드란?
클래스의 인스턴스를 통해 메서드를 가리키면, 그 메서드는 **해당 인스턴스에 묶인(Bound) 상태**가 됩니다.
즉, 함수 자체뿐만 아니라 **그 함수가 실행될 때 참조할 객체(`self`)의 데이터까지 함께 패키징된 상태**입니다.

```python
class Greeter:
    def __init__(self, name: str):
        self.name = name

    def say_hello(self, message: str):
        print(f"{self.name} says: {message}")

g = Greeter("Alice")
# 괄호 없이 메서드 이름만 조회!
print(g.say_hello) 
# 출력: <bound method Greeter.say_hello of <Greeter object>>
```
`g.say_hello`는 단순히 함수만 있는 것이 아니라, `"Alice"`라는 인스턴스 정보까지 품고 있는 일급 객체이므로 **변수나 다른 함수의 인자로 전달**할 수 있습니다.

---

#### 📢 코드 예시: 이벤트 버스와 알림 콜백 등록

어떤 이벤트가 발생했을 때 등록된 메서드들을 차례대로 호출하는 시스템을 만들어 보겠습니다:

```python
from typing import Callable   # list 는 내장 타입이라 import 하지 않습니다 (파이썬 3.9+)

class EventDispatcher:
    def __init__(self):
        # 콜백으로 등록될 함수/메서드 목록 (Callable 타입 힌트 사용)
        self._listeners: list[Callable[[str], None]] = []

    def register(self, callback: Callable[[str], None]) -> None:
        """콜백 함수나 바운드 메서드를 등록"""
        self._listeners.append(callback)

    def trigger(self, event_data: str) -> None:
        """이벤트 발생 시 등록된 모든 콜백 실행"""
        for listener in self._listeners:
            listener(event_data)


class UserNotifier:
    def __init__(self, channel: str):
        self.channel = channel

    def notify(self, message: str) -> None:
        """인스턴스의 상태(channel)를 사용하는 메서드"""
        print(f"[{self.channel}] 알림 전송: {message}")


# --- 사용하기 ---
dispatcher = EventDispatcher()

email_bot = UserNotifier("Email")
slack_bot = UserNotifier("Slack")

# 1. 인스턴스의 '바운드 메서드'를 값으로 넘겨 콜백 등록 (괄호 없음!)
dispatcher.register(email_bot.notify)
dispatcher.register(slack_bot.notify)

# 2. 이벤트 발생 시 각 객체의 메서드가 자기 상태(Email, Slack)를 유지하며 실행됨!
dispatcher.trigger("시스템 점검이 완료되었습니다.")
# 출력:
# [Email] 알림 전송: 시스템 점검이 완료되었습니다.
# [Slack] 알림 전송: 시스템 점검이 완료되었습니다.
```

---

#### 🔌 이 프로젝트에서의 실제 적용: 자원 정리 레지스트리

이 프로젝트의 자원 관리(`backend/infrastructure/clients.py`)에서 바로 이 패턴을 사용합니다:

```python
# 괄호 없이 client.close 메서드 '자체'를 등록!
registry.register("mongo", client.close)
registry.register("redis", redis_client.close)

# 나중에 서버가 꺼질 때(lifespan 종료 시) 등록된 콜백들을 한꺼번에 호출:
# -> client.close()가 알아서 실행되어 자원을 안전하게 해제합니다.
```

---

### 5. 바운드 메서드 콜백의 3대 장점

1. **상태 유지와 캡슐화**:
   - 일반 함수는 전역 변수나 외부 변수에 의존해야 하지만, 바운드 메서드는 객체 내부의 데이터(`self.channel`, `self.client`)를 그대로 품은 채 콜백으로 동작합니다.
2. **명확한 타입 힌트 (`Callable`)**:
   - `Callable[[인자타입], 반환타입]` 형태로 콜백의 규격을 정적으로 안전하게 검증할 수 있습니다.
3. **클린 아키텍처 의존성 역전**:
   - 상위 계층(유스케이스, 디스패처)이 하위 구현체(Slack, Email, Mongo)의 내부를 알 필요 없이, "필요할 때 이 콜백을 실행해 줘"라는 약속만으로 유연하게 결합할 수 있습니다.

---

### 💡 한눈에 정리하기

* **일급 함수**: 함수를 변수에 넣거나 인자로 넘길 수 있는 성질
* **고차 함수**: 함수를 인자로 받거나(`key=`, 콜백) 함수를 돌려주는(클로저 · 데코레이터) 함수 — 일급 함수 성질 위에 세워진 모든 기법의 공통 이름
* **전략 테이블**: `if/elif` 대신 `{"키": 함수}` 딕셔너리로 동적 분기
* **바운드 메서드 콜백**: `인스턴스.메서드`(괄호 없음)를 넘겨 객체의 상태를 유지한 채 나중에 실행시키는 강력한 패턴
