> **쉽게 이해하기**
>
> - **한 줄 요약** — 함수나 메서드를 일반 변수처럼 딕셔너리에 담거나 다른 함수의 인자(콜백)로 넘겨서 실행할 수 있습니다.
> - **비유하면** — 요리 레시피 카드(함수)를 메뉴판(dict)에 꽂아 두고, 손님이 주문하면 꺼내서 요리하는 것.
> - **이 프로젝트에서는** — DB 종류별로 저장소를 고르는 팩토리 테이블(`LAB_REPOSITORY_FACTORIES`)과 서버 종료 시 DB 연결을 닫는 콜백 등록(`registry.register("mongo", client.close)`)에 쓰입니다.
> - **기억할 것** — 함수 뒤에 괄호`()`를 붙이지 않고 이름만 쓰면 "실행"이 아니라 "함수 자체를 전달"하는 것입니다.

파이썬에서 함수는 **일급 객체(First-class Object)** 입니다. 숫자나 문자열처럼 변수에 담을 수도 있고, 다른 함수의 인자로 넘길 수도 있으며, 딕셔너리의 값으로 저장할 수도 있습니다.

이 강력한 성질을 활용하는 3가지 핵심 기법(클로저, 전략 테이블, 바운드 메서드 콜백)을 알기 쉽게 정리합니다.

---

### 1. 클로저(Closure) — "바깥 변수를 기억하는 함수"

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

### 2. 전략 테이블(Strategy Table) — 지저분한 `if/elif` 없애기

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

### 3. 바운드 메서드(Bound Method)와 콜백(Callback) 등록 패턴

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
from typing import Callable, list

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

### 4. 바운드 메서드 콜백의 3대 장점

1. **상태 유지와 캡슐화**:
   - 일반 함수는 전역 변수나 외부 변수에 의존해야 하지만, 바운드 메서드는 객체 내부의 데이터(`self.channel`, `self.client`)를 그대로 품은 채 콜백으로 동작합니다.
2. **명확한 타입 힌트 (`Callable`)**:
   - `Callable[[인자타입], 반환타입]` 형태로 콜백의 규격을 정적으로 안전하게 검증할 수 있습니다.
3. **클린 아키텍처 의존성 역전**:
   - 상위 계층(유스케이스, 디스패처)이 하위 구현체(Slack, Email, Mongo)의 내부를 알 필요 없이, "필요할 때 이 콜백을 실행해 줘"라는 약속만으로 유연하게 결합할 수 있습니다.

---

### 💡 한눈에 정리하기

* **일급 함수**: 함수를 변수에 넣거나 인자로 넘길 수 있는 성질
* **전략 테이블**: `if/elif` 대신 `{"키": 함수}` 딕셔너리로 동적 분기
* **바운드 메서드 콜백**: `인스턴스.메서드`(괄호 없음)를 넘겨 객체의 상태를 유지한 채 나중에 실행시키는 강력한 패턴
