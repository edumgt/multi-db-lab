> **쉽게 이해하기**
>
> - **한 줄 요약** — 인스턴스 메서드(self) · classmethod(cls) · staticmethod · property · 던더(dunder) 메서드의 차이를 이해하고 알맞게 사용합니다.
> - **비유하면** — 자동차로 치면 '운전하기'(self), '공장에서 조립하기'(cls), '연비 계산기'(static), '계기판 속도계'(property), '엑셀 페달 밟기/시동 걸기'(던더).
> - **이 프로젝트에서는** — `Post.create(...)` classmethod가 엔티티를 만들고, `settings.allowed_origin_list` property가 설정을 리스트로 바꾸며, `__init__`/`__repr__` 던더 메서드가 객체를 다룹니다.
> - **기억할 것** — 내 객체가 `print()`나 `+`, `len()` 같은 파이썬 기본 문법과 자연스럽게 어울리게 하려면 알맞은 던더 메서드를 만듭니다.

파이썬 클래스 안에는 목적에 따라 다양한 형태의 메서드가 존재합니다.

"이 메서드가 누구의 데이터에 접근하는가?", "파이썬 기본 문법(`+`, `len()` 등)과 어떻게 상호작용하는가?"에 따라 알맞은 메서드를 고르는 방법을 알기 쉽게 정리합니다.

---

### 1. 인스턴스 메서드 — `self` (내 데이터 다루기)

가장 기본적이고 흔하게 쓰는 메서드입니다. 첫 번째 인자로 **현재 객체 자신(`self`)** 을 받아서 인스턴스의 속성을 읽거나 변경합니다.

```python
# backend/domain/entities.py
def apply(self, patch: LabRecordPatch) -> LabRecord:
    # self(현재 객체)의 데이터를 기반으로 수정된 새 객체 생성
    return replace(self, **patch.changes())
```

---

### 2. `@classmethod` — `cls` (다양한 방식으로 객체 조립하기)

인스턴스(`self`)가 아니라 **클래스 자체(`cls`)** 를 첫 번째 인자로 받습니다.
주로 **"다양한 방법으로 객체를 생성(대안 생성자)"** 할 때 사용합니다.

```python
# backend/domain/entities.py
@classmethod
def from_dict(cls, raw: Mapping[str, Any]) -> LabRecord:
    """딕셔너리 데이터를 받아 LabRecord 객체를 조립합니다."""
    return cls(id=str(raw["id"]), title=str(raw["title"]), content=str(raw["content"]))
```

* **왜 쓰나요?**: `__init__` 하나만으로는 "DB row로 만들기", "JSON으로 만들기" 등 다양한 생성 방식을 깔끔하게 담기 어렵기 때문입니다.
* **표준 라이브러리 예시**: `datetime.fromisoformat()`, `dict.fromkeys()`

---

### 3. `@staticmethod` — 클래스 안에 둔 순수 도우미 함수

`self`도 `cls`도 필요 없는, 클래스 내부에 소속된 독립적인 함수입니다.

```python
# backend/adapters/gateways/lab_redis.py
@staticmethod
def _dump(record: LabRecord) -> str:
    """Redis 저장용으로 레코드를 JSON 문자열로 변환하는 도우미 함수"""
    return json.dumps(record.to_dict(), ensure_ascii=False)
```

* 객체의 상태를 건드리지 않지만, "이 함수는 Redis 게이트웨이와 밀접한 도우미다"라는 소속감을 명확히 표현할 때 씁니다.

---

### 4. `@property` — 메서드를 변수처럼 읽기

괄호`()`를 붙여서 호출하지 않고, 마치 일반 변수(속성)처럼 값을 읽을 수 있게 만듭니다.

```python
# backend/usecases/lab_record_usecase.py
@property
def source(self) -> str:
    return self._repo.source
```
* **사용법**: `uc.source()` 대신 `uc.source` 로 읽습니다.
* **장점**:
  1. 외부에서는 일반 변수처럼 편하게 읽지만, 내부에서는 계산 로직을 숨길 수 있습니다.
  2. setter를 만들지 않으면 외부에서 값을 함부로 못 바꾸는 **읽기 전용 속성**이 됩니다.

---

### 5. 던더(Dunder) 메서드 — 파이썬의 마법(매직) 메서드

**던더(Dunder)** 는 **Double Underscore**의 줄임말로, 이름 앞뒤에 두 개의 밑줄(`__`)이 붙는 특수한 메서드들을 통칭합니다. 파이썬에서는 **매직 메서드(Magic Method)** 또는 **특수 메서드(Special Method)** 라고도 부릅니다.

파이썬의 내장 함수(`len()`, `str()` 등)나 연산자(`+`, `==` 등)가 우리가 만든 클래스와 자연스럽게 어울려 동작하도록 백그라운드에서 호출되는 핵심 메커니즘입니다.

#### 🛠️ 주요 던더 메서드 종류

1. **객체 생성 및 초기화**
   * `__init__(self, ...)`: 객체가 생성될 때 호출되는 초기화 메서드 (생성자 역할)
   * `__del__(self)`: 객체가 메모리에서 사라질 때 호출되는 소멸자

2. **문자열 표현 (출력하기)**
   * `__str__(self)`: 일반 사용자가 보기 편한 문자열 반환 (`print()` 또는 `str()` 호출 시 실행)
   * `__repr__(self)`: 개발자 디버깅용 공식 문자열 반환 (콘솔에서 객체를 쳤을 때 표시되는 형태)

3. **연산자 오버로딩 (기호 쓰기)**
   * `__add__(self, other)`: `+` 덧셈 기호를 쓸 때 호출
   * `__eq__(self, other)`: `==` 같은지 비교할 때 호출

4. **컨테이너 및 길이 조작**
   * `__len__(self)`: `len(obj)` 함수를 쓸 때 호출
   * `__getitem__(self, key)`: `obj[key]` 처럼 대괄호 인덱싱을 쓸 때 호출

---

#### 🧪 쉬운 코드 예시: 벡터(Vector) 덧셈과 출력

던더 메서드를 만들어두면, 우리가 만든 클래스끼리 `+` 기호로 더하거나 `print()`로 예쁘게 출력할 수 있습니다:

```python
class Vector:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __str__(self) -> str:
        """print() 함수로 출력할 때 사람이 보기 편한 문자열"""
        return f"Vector(x={self.x}, y={self.y})"

    def __add__(self, other: "Vector") -> "Vector":
        """+ 연산자를 만났을 때 두 벡터를 더한 새 벡터를 반환"""
        return Vector(self.x + other.x, self.y + other.y)

# 사용하기
v1 = Vector(2, 3)
v2 = Vector(4, 5)

# 내부적으로 v1.__add__(v2) 가 호출됩니다!
v3 = v1 + v2  

# 내부적으로 v3.__str__() 이 호출됩니다!
print(v3)  # 출력: Vector(x=6, y=8)
```

---

#### 🏛️ 클린 아키텍처 및 중급 파이썬에서의 의미

던더 메서드를 잘 활용하면 코드가 훨씬 **파이썬스럽고(Pythonic)** 직관적이게 됩니다.
특히 파이썬의 표준 인터페이스 규격을 맞출 때 던더 메서드가 필수적으로 쓰입니다:
* `for ... in` 반복문 지원: `__iter__`, `__next__` (tech011)
* `with` 문 자원 관리 지원: `__enter__`, `__exit__` (tech009)
* 데이터클래스 비교 및 해시 지원: `__eq__`, `__hash__` (tech003)

---

### 6. 변수/메서드 밑줄(`_`) 이름 규칙 한눈에 보기

| 표기 | 의미 | 쉬운 비유 |
|---|---|---|
| `_repo` | 내부 전용 (Private 관례) | "밖에서 손대지 마세요" 라는 노란색 주의 스티커 |
| `__secret` | 이름 맹글링 (충돌 방지) | 자식 클래스와 이름이 겹치지 않게 파이썬이 이름을 바꿔서 보관 |
| `__init__`, `__add__` | **던더(Dunder) 메서드** | 파이썬 시스템이 뒤에서 자동으로 실행해 주는 특수 버튼 |
| `_` (단독) | 버리는 값 | "이 값은 안 쓸 거니까 무시하세요" (`for _ in range(5)`) |

---

### 7. 한눈에 보는 메서드 선택 가이드

| 상황 | 어떤 메서드를 쓸까요? |
|---|---|
| 인스턴스의 데이터(`self`)를 읽거나 다뤄야 할 때 | **인스턴스 메서드** |
| "딕셔너리나 파일로부터 새 객체 만들기"처럼 생성 방법이 다양할 때 | **`@classmethod`** |
| 객체 데이터는 안 쓰지만, 클래스에 속한 편리한 계산/변환 도구일 때 | **`@staticmethod`** |
| 계산 결과를 일반 변수처럼 괄호 없이 깔끔하게 읽고 싶을 때 | **`@property`** |
| `print()`, `+`, `len()`, `with` 등 파이썬 기본 문법과 연결할 때 | **던더(Dunder) 메서드** |
