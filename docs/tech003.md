> **쉽게 이해하기**
>
> - **한 줄 요약** — 데이터를 담는 클래스의 귀찮은 반복 코드(`__init__`, `__repr__`, `__eq__`)를 한 줄로 자동 완성해 줍니다.
> - **비유하면** — 입력 양식(폼)만 정해주면, 출력·비교·검사 도장이 자동으로 찍혀 나오는 스마트 복사기.
> - **이 프로젝트에서는** — 핵심 데이터 모델(`User`, `Post`, `LabRecord`)이 전부 dataclass이며, `frozen=True`로 중간에 데이터가 오염되는 것을 막습니다.
> - **기억할 것** — 리스트나 딕셔너리 같은 가변 기본값은 반드시 `field(default_factory=list)`로 적어야 버그가 안 납니다.

파이썬의 `@dataclass`는 데이터를 담는 클래스를 만들 때 **반복되는 보일러플레이트(상투적인 코드)를 한 방에 없애주는** 표준 라이브러리 데코레이터입니다.

---

### 1. 왜 쓸까요? (Before vs After)

#### ❌ 일반 클래스 (손목 아픈 반복 작업)
```python
class Employee:
    def __init__(self, id: str, name: str, position: str):
        self.id = id
        self.name = name
        self.position = position

    def __repr__(self):
        return f"Employee(id={self.id}, name={self.name}, position={self.position})"

    def __eq__(self, other):
        return (self.id, self.name, self.position) == (other.id, other.name, other.position)
```

#### ⭕ dataclass 적용 (단 4줄로 끝!)
```python
from dataclasses import dataclass

@dataclass
class Employee:
    id: str
    name: str
    position: str
```
위처럼 적기만 하면 파이썬이 알아서 아래 기능들을 전부 만들어 줍니다:
1. `Employee("1", "kim", "dev")` 로 생성 가능
2. `print(emp)` 하면 알아보기 쉬운 문자열 출력 (`__repr__`)
3. `emp1 == emp2` 로 값 비교 가능 (`__eq__`)

---

### 2. `frozen=True` — "한번 만든 데이터는 절대 못 바꿉니다" (불변 객체)

```python
@dataclass(frozen=True)
class LabRecord:
    id: str
    title: str
```
* **효과**: 생성된 객체의 속성을 수정하려고 하면 즉시 에러(`FrozenInstanceError`)가 발생합니다.
* **왜 필요한가요?**: DB에서 꺼낸 데이터가 유스케이스나 화면으로 전달되는 도중에 **누군가 실수로 값을 변조하는 것을 원천 차단**합니다.
* **보너스**: 불변이 되므로 `set`의 원소나 `dict`의 키로도 안전하게 사용할 수 있습니다.

---

### 3. `slots=True` — "메모리 다이어트 & 오타 방지" (파이썬 3.10+)

```python
@dataclass(slots=True)
class LabRecord:
    id: str
    title: str
```
* **메모리 절약**: 파이썬 객체 내부의 무거운 딕셔너리(`__dict__`)를 없애고 딱 정해진 칸(슬롯)만 사용합니다. 수만 건의 레코드를 다룰 때 메모리를 크게 아껴줍니다.
* **오타 즉시 검거**: 존재하지 않는 속성을 대입하면 에러가 납니다. (`record.titel = "오타"` -> `AttributeError` 발생!)

---

### 4. `field(default_factory=list)` — 흔히 하는 치명적 실수 막기

파이썬에서 기본값으로 빈 리스트 `[]`를 직접 넣는 것은 엄격히 금지되어 있습니다:
```python
# ❌ 절대 안 됨! (파이썬이 ValueError 발생시킴)
tags: list[str] = []

# ⭕ 올바른 방법
from dataclasses import field

@dataclass
class LabRecord:
    id: str
    tags: list[str] = field(default_factory=list)
```
* **이유**: `[]`를 직접 쓰면 모든 인스턴스가 하나의 리스트를 공유하는 고전적인 버그가 생기기 때문입니다. `default_factory=list`를 써야 객체가 생성될 때마다 새로운 빈 리스트가 만들어집니다.

---

### 5. `replace()` — 불변 객체를 안전하게 수정하는 방법

`frozen=True` 객체는 값을 직접 수정할 수 없습니다(`record.title = "새 제목"` 불가).
대신 일부 값만 싹 바꾼 **새로운 복사본**을 만들어 씁니다:

```python
from dataclasses import replace

old_record = LabRecord(id="1", title="원래 제목")
# title만 바뀐 새로운 객체 생성!
new_record = replace(old_record, title="새로운 제목")
```

---

### 6. dataclass vs pydantic (언제 무엇을 쓸까요?)

| 구분 | `@dataclass` (표준 내장) | `pydantic.BaseModel` (외부 패키지) |
|---|---|---|
| **주 역할** | 순수하고 가벼운 데이터 저장소 | 외부 입력값 유효성 검증 (Validation) |
| **속도/의존성**| 매우 빠름, 설치 불필요 (파이썬 기본) | 검증 기능이 많아 조금 더 무거움 |
| **이 프로젝트 적용** | `backend/domain/` (핵심 비즈니스 엔티티) | `backend/adapters/api/` (API 입출력 검증) |

> **클린 아키텍처 원칙**  
> 가장 순수해야 하는 핵심 비즈니스 영역(도메인)은 가볍고 외부 의존성이 없는 `@dataclass`로 만들고, 외부 사용자의 잘못된 입력을 걸러내야 하는 API 계층은 `Pydantic`으로 명확히 역할을 분리했습니다.
