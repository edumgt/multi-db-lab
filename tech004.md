> **쉽게 이해하기**
>
> - **한 줄 요약** — '이 메서드들을 꼭 구현해라' 는 약속(인터페이스)을 적는 두 가지 방법입니다.
> - **비유하면** — ABC는 계약서에 서명해야 들어오는 '회원제 클럽', Protocol은 '오리처럼 걷고 꽥꽥거리면 그냥 오리로 인정'하는 열린 클럽.
> - **이 프로젝트에서는** — `ports.py` 의 `LabRecordRepository` 가 ABC 입니다. Mongo · Redis · ClickHouse 등 7개 DB 저장소가 같은 약속을 지켜서 언제든 서로 교체할 수 있습니다.
> - **기억할 것** — 구현 클래스를 내가 직접 만들면 **ABC**, 외부 라이브러리 객체처럼 건드릴 수 없는 것도 맞춰야 하면 **Protocol**.

파이썬에서 **추상 클래스(ABC)** 와 **프로토콜(Protocol)** 은 "이 클래스는 반드시 이러이러한 기능을 가져야 한다"는 **규칙(인터페이스/계약)** 을 정하는 도구입니다.

다양한 데이터베이스(PostgreSQL, MongoDB, Redis 등)를 자유롭게 바꿔 끼울 수 있는 비결이 여기에 있습니다.

---

### 1. ABC (추상 클래스) — "계약서에 서명하고 들어오세요"

**ABC** 는 *Abstract Base Class* (추상 기반 클래스) 의 약자입니다. 표준 라이브러리 `abc` 모듈이 제공하며, 핵심은 두 가지입니다.

1. `abc.ABC` 를 **상속** 한다 → "이 클래스는 계약서다" 라고 선언
2. 메서드에 `@abstractmethod` 를 붙인다 → "자식은 이 메서드를 반드시 직접 구현해라" 라고 명시

이 두 조건을 갖춘 클래스는 **직접 인스턴스를 만들 수 없고**, 추상 메서드를 하나라도 빠뜨린 자식 클래스도 **인스턴스를 만드는 순간 `TypeError`** 를 냅니다.

* **특징**: "나는 이 규칙을 지킵니다" 라고 **상속(`class MongoRepo(LabRecordRepository):`)으로 명시**해야 합니다. (명목적 서브타이핑 — 이름(상속 관계)으로 타입을 판정)

```python
# backend/domain/ports.py (규칙 정의)
from abc import ABC, abstractmethod
from typing import ClassVar

class LabRecordRepository(ABC):
    """LabRecord CRUD 계약."""

    #: 응답의 `source` 필드에 노출되는 저장소 이름. 각 구현체가 반드시 덮어씁니다.
    source: ClassVar[str] = "unknown"

    @abstractmethod
    def add(self, record: LabRecord) -> LabRecord:
        """레코드를 저장하고 저장된 모습을 돌려줍니다."""

    @abstractmethod
    def list(self, limit: int) -> list[LabRecord]:
        """최대 limit 건을 돌려줍니다."""

    @abstractmethod
    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None:
        """부분 수정. 대상이 없으면 None."""

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        """삭제 성공 여부."""
```

이 계약을 지키는 구현체는 `backend/adapters/gateways/` 에 7개 있습니다 (`MongoLabRecordRepository`, `RedisLabRecordRepository`, `ClickHouseLabRecordRepository` …). 모두 **같은 네 메서드**를 구현했기 때문에 유스케이스 입장에서는 어떤 DB 인지 구분할 필요가 없습니다.

```python
# backend/adapters/gateways/lab_mongo.py (계약 이행)
class MongoLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "mongodb"      # ← 클래스 속성도 덮어쓴다

    def add(self, record: LabRecord) -> LabRecord: ...
    def list(self, limit: int) -> list[LabRecord]: ...
    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None: ...
    def delete(self, record_id: str) -> bool: ...
```

#### 🛡️ ABC의 강력한 장점: 실수 방지
만약 깜빡하고 `list()` 메서드를 구현하지 않았다면?
```python
class IncompleteRepo(LabRecordRepository):
    def add(self, record):
        return record
    # list · update · delete 를 깜빡하고 안 만듦!

repo = IncompleteRepo()
# 💥 TypeError: Can't instantiate abstract class IncompleteRepo
#    without an implementation for abstract methods 'delete', 'list', 'update'
#    (파이썬 3.11 이하: "... with abstract methods delete, list, update")
```
에러 메시지에 **빠진 메서드 이름이 전부** 나오므로 무엇을 더 만들어야 하는지 바로 알 수 있습니다.
`add()` 를 호출해 보기도 전에, 객체를 만드는 시점(보통 앱 기동 시점)에 잡히는 것이 핵심입니다.

이 동작은 `tests/test_domain.py` 의 `test_abc_forces_full_implementation` 테스트가 실제로 검증합니다.

```python
def test_abc_forces_full_implementation() -> None:
    class Incomplete(LabRecordRepository):
        def add(self, record):
            return record

    with pytest.raises(TypeError):
        Incomplete()  # list/update/delete 미구현 → 인스턴스화 불가
```

#### ⚙️ 내부 동작: 어떻게 알아채나요?
* `abc.ABC` 는 메타클래스 `ABCMeta` 를 쓰는 빈 클래스입니다. 클래스가 만들어질 때 `ABCMeta` 가 `@abstractmethod` 붙은 이름을 모아 `__abstractmethods__` 라는 **frozenset** 에 기록합니다.
* 자식 클래스가 그 이름을 **재정의하면 집합에서 빠지고**, 집합이 비어 있어야 인스턴스를 만들 수 있습니다.
* `IncompleteRepo.__abstractmethods__` 를 출력하면 `frozenset({'list', 'update', 'delete'})` 처럼 **아직 남은 숙제** 를 직접 볼 수 있습니다.

#### 📌 자주 헷갈리는 포인트
| 상황 | 결과 |
|---|---|
| `LabRecordRepository()` 처럼 추상 클래스를 직접 생성 | `TypeError` — 추상 클래스는 "틀" 이지 "물건" 이 아님 |
| 자식이 일부만 구현하고, 손자가 나머지를 구현 | 자식은 여전히 추상(생성 불가), **손자부터** 생성 가능 |
| 메서드 이름은 같지만 인자가 다르게 구현 | ABC 는 **이름만** 확인하므로 통과함 → 시그니처 검사는 `mypy` 가 담당 |
| `@abstractmethod` 는 붙였지만 `ABC` 를 상속하지 않음 | 아무 효과 없음 — 데코레이터만으로는 강제되지 않음 |
| 추상 메서드가 **하나도 없는** `ABC` 자식 | 그냥 일반 클래스처럼 생성 가능 |

#### 🧩 추상 클래스에도 "일반 메서드" 를 둘 수 있습니다
ABC 는 전부 비어 있어야 하는 것이 아닙니다. 공통 로직을 부모에 한 번만 두고, 다른 부분만 자식이 채우는 **템플릿 메서드** 패턴에 자주 쓰입니다.

```python
class LabRecordRepository(ABC):
    @abstractmethod
    def list(self, limit: int) -> list[LabRecord]: ...

    def first(self) -> LabRecord | None:          # 일반 메서드 — 자식이 구현한 list() 를 활용
        rows = self.list(limit=1)
        return rows[0] if rows else None
```
이 프로젝트의 포트는 "계약은 최소로" 라는 원칙에 따라 추상 메서드만 두었지만, `source: ClassVar[str]` 처럼 **클래스 속성** 으로 공통 규격(저장소 이름)을 선언한 것은 같은 맥락입니다.

#### 🎛️ 다른 데코레이터와 함께 쓰기
`@abstractmethod` 는 **가장 안쪽(아래)** 에 둡니다.
```python
class Port(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...          # 추상 프로퍼티

    @classmethod
    @abstractmethod
    def from_env(cls) -> "Port": ...    # 추상 클래스 메서드

    @staticmethod
    @abstractmethod
    def validate(raw: str) -> bool: ... # 추상 정적 메서드
```
(`abstractproperty` 같은 옛 이름은 더 이상 쓰지 않습니다.)

#### ✅ ABC 는 `isinstance` 와 잘 어울립니다
```python
repo = MongoLabRecordRepository(...)
isinstance(repo, LabRecordRepository)   # True — 상속했으니 당연히
```
반대로 상속하지 않은 클래스는 메서드가 전부 같아도 `False` 입니다. 이 "엄격함" 이 ABC 의 장점이자, 외부 라이브러리 객체에는 쓰기 어려운 이유입니다 (3번 Protocol 참고).

#### 🧪 테스트에서의 가치
`tests/fakes.py` 의 `InMemoryLabRecordRepository` 도 같은 ABC 를 상속합니다. 덕분에 유스케이스 테스트는 **DB 없이** 돌아가고, 포트에 메서드를 하나 추가하면 가짜 객체도 **빠뜨릴 수 없게** 강제됩니다 — 진짜 어댑터와 가짜가 서로 어긋나는 사고를 ABC 가 막아 줍니다.

---

### 2. 추상 메서드 본문의 `...` 은 무슨 뜻인가요?

추상 메서드는 어차피 자식 클래스에서 진짜 내용을 채울 것이기 때문에, 본문에는 아무것도 적지 않습니다.
* `pass` 또는 `...` (Ellipsis) 을 적거나, 설명문(docstring)만 남겨둡니다.
* 이 프로젝트는 설명이 필요한 곳은 **docstring**, 자명한 곳은 `...` 로 통일하여 IDE 툴팁에 도움말이 잘 나오도록 했습니다.

---

### 3. Protocol (프로토콜) — "오리처럼 걷고 꽥꽥거리면 오리다"

파이썬 3.8에 도입된 **Protocol**은 굳이 상속(`(Closeable)`)을 받지 않아도, **그 메서드만 가지고 있으면 같은 종류로 인정**해 주는 방식입니다. (덕 타이핑, 구조적 서브타이핑)

* **비유**: 특정 클럽 회원증이 없어도, "정장과 넥타이만 매고 오면 누구나 입장 가능!"한 방식입니다.

```python
# backend/domain/ports.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Closeable(Protocol):
    def close(self) -> object: ...
```

#### 💡 언제 유용할까요? (외부 라이브러리 연결할 때)
`MongoClient`, `RedisClient`, `PostgresEngine` 등은 남들이 만든 외부 라이브러리라서 우리가 마음대로 `class MongoClient(Closeable):` 처럼 상속을 붙일 수 없습니다.
하지만 이 객체들 모두 우연히도 `close()` 메서드를 가지고 있습니다!
따라서 상속 선언 없이도 **전부 `Closeable` 타입으로 묶어서 한 번에 정리**할 수 있습니다.

---

### 4. 한눈에 비교: ABC vs Protocol 언제 무엇을 쓸까요?

| 기준 | ABC (추상 클래스) | Protocol (프로토콜) |
|---|---|---|
| **동작 방식** | 명시적 상속 필수 (`class A(ABC):`) | 메서드만 같으면 상속 없어도 OK |
| **언제 쓰나요?** | 내가 직접 만드는 프로젝트 핵심 계층 (DB 게이트웨이, 리포지토리) | 외부 라이브러리 객체나 가벼운 콜백 함수 규격 |
| **장점** | 상속 관계가 뚜렷하여 구조를 파악하기 쉬움 | 기존 코드를 전혀 수정하지 않고도 유연하게 호환 |

---

### 5. 클린 아키텍처와의 연결 — "플러그인처럼 DB 갈아 끼우기"

1. **규칙(포트)을 핵심 도메인에 둡니다**:
   - `backend/domain/ports.py`에 `LabRecordRepository` (ABC)를 만듭니다.
2. **비즈니스 로직(유스케이스)은 구체적인 DB를 모릅니다**:
   - 유스케이스는 오직 `LabRecordRepository` 약속만 믿고 일합니다.
3. **결과**:
   - 운영할 때는 진짜 MongoDB(`MongoLabRecordRepository`)를 꽂고,
   - 단위 테스트를 돌릴 때는 DB 없이 메모리 가짜 객체(`InMemoryLabRecordRepository`)를 꽂아 0.01초 만에 테스트할 수 있습니다!
