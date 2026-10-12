파이썬에서 **추상 클래스(ABC)** 와 **프로토콜(Protocol)** 은 "이런 메서드를 가져야 한다"는 계약을 표현하는 두 가지 방법입니다. 이 프로젝트의 `backend/domain/ports.py` 는 ABC 를 주로 쓰고, Protocol 예시를 하나 두었습니다.

---

### 1. ABC — 명목적(nominal) 서브타이핑

* `abc.ABC` 를 상속하고 `@abstractmethod` 를 붙인 메서드가 하나라도 구현되지 않으면 **인스턴스화 시점**에 `TypeError` 가 납니다.
* "이 클래스는 저 인터페이스를 구현한다" 를 **상속으로 명시**해야 합니다.

> ```python
> # backend/domain/ports.py
> class LabRecordRepository(ABC):
>     source: ClassVar[str] = "unknown"
>
>     @abstractmethod
>     def add(self, record: LabRecord) -> LabRecord: ...
>     @abstractmethod
>     def list(self, limit: int) -> list[LabRecord]: ...
>     @abstractmethod
>     def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None: ...
>     @abstractmethod
>     def delete(self, record_id: str) -> bool: ...
> ```
> ```python
> # tests/test_domain.py — 미구현을 잡아내는 테스트
> class Incomplete(LabRecordRepository):
>     def add(self, record): return record
>
> with pytest.raises(TypeError):
>     Incomplete()        # list/update/delete 미구현
> ```

### 2. 추상 메서드 본문은 왜 `...` 인가

* 본문은 호출되지 않으므로 `pass` / `...` / docstring 어느 것이든 됩니다.
* 이 프로젝트는 설명이 필요한 메서드는 **docstring 만**, 자명한 것은 `...` 로 통일했습니다. docstring 은 그대로 IDE 툴팁에 나타납니다.

### 3. 추상 속성 — `ClassVar` 와 기본값

* `source: ClassVar[str] = "unknown"` 처럼 **클래스 변수**로 둔 뒤 구현체가 덮어씁니다.
* `@property` + `@abstractmethod` 로 강제할 수도 있지만, 응답 `source` 필드처럼 단순 상수는 ClassVar 가 더 읽기 쉽습니다.

### 4. Protocol — 구조적(structural) 서브타이핑 (덕 타이핑의 정적 버전)

* 상속 없이 **"이 메서드들이 있으면 통과"** 합니다. 서드파티 클래스(수정 불가)에 타입을 입힐 때 유용합니다.
* `@runtime_checkable` 을 붙이면 `isinstance()` 도 가능해집니다(메서드 **존재 여부만** 검사, 시그니처는 안 봄).

> ```python
> # backend/domain/ports.py
> @runtime_checkable
> class Closeable(Protocol):
>     def close(self) -> object: ...
>
> # MongoClient · Redis · OpenSearch · Driver 는 모두 Closeable 을 상속하지 않지만 만족합니다.
> ```

### 5. 언제 무엇을 쓰나

| 상황 | 선택 |
|---|---|
| 내가 설계한 계약을 **내 코드**가 구현 (포트/게이트웨이) | **ABC** — 구현 누락을 런타임 초기에 잡고, 상속 선언 자체가 문서가 됨 |
| 서드파티 객체에 공통 타입을 부여 | **Protocol** |
| 기본 구현(템플릿 메서드)을 상속으로 공유 | ABC |
| 콜백 하나짜리 간단한 계약 | Protocol 또는 `Callable[...]` |

### 6. 클린 아키텍처와의 관계 — 의존성 역전

* 포트(ABC)는 **사용하는 쪽(유스케이스)이 소유**합니다. 구현(게이트웨이)은 바깥 원에 있습니다.
* 결과: `usecases/` 는 `adapters/` 를 한 줄도 import 하지 않고, 테스트는 `tests/fakes.py` 의 인메모리 구현을 꽂아 DB 없이 돌아갑니다.

> ```python
> # 운영: deps.py
> LabRecordUseCase(MongoLabRecordRepository(clients.mongo_collection()))
> # 테스트: test_usecases.py
> LabRecordUseCase(InMemoryLabRecordRepository())
> ```

---

ABC 는 "계약을 어긴 어댑터" 를 import 직후가 아니라 **첫 인스턴스화** 때 잡습니다. 그래서 이 프로젝트는 `tests/fakes.py` 의 가짜 구현도 같은 ABC 를 상속시켜, 테스트 더블이 실제 계약과 어긋나는 흔한 문제까지 언어 수준에서 막았습니다.
