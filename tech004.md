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

`abc.ABC`를 상속받고 `@abstractmethod`를 붙이면, 해당 메서드를 구현하지 않은 자식 클래스는 **인스턴스(객체)를 만드는 순간 바로 에러**(`TypeError`)를 냅니다.

* **특징**: "나는 이 규칙을 지킵니다"라고 **상속(`class MongoRepo(LabRecordRepository):`)으로 명시**해야 합니다. (명목적 서브타이핑)

```python
# backend/domain/ports.py (규칙 정의)
from abc import ABC, abstractmethod

class LabRecordRepository(ABC):
    @abstractmethod
    def add(self, record: LabRecord) -> LabRecord:
        """새 레코드를 저장합니다. (자식 클래스는 반드시 이 함수를 만들어야 함!)"""
        ...

    @abstractmethod
    def list(self, limit: int) -> list[LabRecord]:
        """목록을 조회합니다."""
        ...
```

#### 🛡️ ABC의 강력한 장점: 실수 방지
만약 깜빡하고 `list()` 메서드를 구현하지 않았다면?
```python
class IncompleteRepo(LabRecordRepository):
    def add(self, record): 
        return record
    # list 메서드를 깜빡하고 안 만듦!

repo = IncompleteRepo()  # 💥 실행 즉시 TypeError 발생! "list가 구현 안 됐습니다"
```
코드를 실제로 돌려보기 전에 빠진 기능을 확실하게 잡아줍니다.

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
