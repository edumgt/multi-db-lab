> **쉽게 이해하기**
>
> - **한 줄 요약** — 데이터를 담는 클래스의 `__init__` · `__repr__` · `__eq__` 를 자동으로 만들어 주는 데코레이터입니다.
> - **비유하면** — 양식(폼) 을 정하면 입력창 · 출력 · 비교 기능이 자동으로 딸려오는 것.
> - **이 프로젝트에서는** — 도메인 엔티티(User · Post · LabRecord) 는 전부 dataclass 이고, `frozen=True` 로 값을 실수로 바꾸는 것을 막습니다.
> - **기억할 것** — 리스트 같은 가변 기본값은 `field(default_factory=list)` 로 씁니다.

파이썬의 `dataclasses` 모듈은 **데이터를 담는 클래스의 반복 코드(`__init__`, `__repr__`, `__eq__`)를 자동 생성**해 줍니다. 이 프로젝트의 도메인 엔티티(`backend/domain/entities.py`)는 전부 dataclass 입니다.

---

### 1. 기본 동작

```python
@dataclass
class Employee:
    id: str
    name: str
    position: str
```

* 위 선언만으로 `Employee("1", "kim", "dev")`, `==` 비교, 읽기 좋은 `repr` 이 생깁니다.
* 필드 순서 = 생성자 인자 순서. 타입 힌트는 필수(없으면 필드로 인식되지 않음).

### 2. `frozen=True` — 불변 객체

* 생성 후 속성 대입을 막습니다. 대입 시 `dataclasses.FrozenInstanceError`.
* 여러 계층(게이트웨이 → 유스케이스 → 프리젠터)을 오가는 엔티티가 **중간에 몰래 바뀌는 일**을 원천 차단합니다.
* 부수 효과로 `__hash__`가 생성되어 set 원소나 dict 키로 쓸 수 있습니다.

> ```python
> # tests/test_domain.py
> record = LabRecord(id="1", title="제목", content="본문")
> with pytest.raises(dataclasses.FrozenInstanceError):
>     record.title = "changed"
> ```

### 3. `slots=True` — 메모리 절약과 오타 방지 (3.10+)

* 인스턴스마다 `__dict__`를 만들지 않고 고정 슬롯을 사용합니다. 수십만 건 레코드를 다루면 메모리 차이가 체감됩니다.
* 선언되지 않은 속성을 대입하면 `AttributeError` → `record.titel = ...` 같은 오타를 즉시 잡습니다.

### 4. `field(default_factory=list)` — 가변 기본값의 올바른 처리

* `tags: list[str] = []` 는 **금지**됩니다(`ValueError: mutable default`). 모든 인스턴스가 같은 리스트를 공유하는 고전적 버그를 막기 위해서입니다.
* `default_factory` 에 호출 가능한 객체를 주면 인스턴스마다 새 리스트가 만들어집니다.

> ```python
> # backend/domain/entities.py
> @dataclass(frozen=True, slots=True)
> class LabRecord:
>     id: str
>     title: str
>     content: str
>     tags: list[str] = field(default_factory=list)
> ```

### 5. `replace()` — 불변 객체의 "수정"

* frozen 객체는 바꿀 수 없으므로 **일부 필드만 바꾼 새 객체**를 만듭니다.

> ```python
> from dataclasses import replace
>
> def apply(self, patch: LabRecordPatch) -> LabRecord:
>     return replace(self, **patch.changes())      # {"title": "new"} → title 만 바뀐 새 LabRecord
> ```
> Redis 게이트웨이의 PATCH 구현이 정확히 이 패턴입니다: `self._load(raw).apply(patch)` → 새 객체를 다시 저장.

### 6. `asdict()` 대신 명시적 `to_dict()` 를 쓴 이유

* `dataclasses.asdict()` 는 편리하지만 **모든 필드를 재귀적으로 복사**하고, 어떤 키가 외부로 나가는지 코드에 드러나지 않습니다.
* 외부 저장소(JSON, DynamoDB Item)로 나가는 모양은 계약이므로 `to_dict()` / `from_dict()` 를 손으로 작성해 "무엇이 밖으로 나가는가"를 한눈에 보이게 했습니다.

### 7. dataclass vs pydantic BaseModel

| 구분 | dataclass | pydantic BaseModel |
|---|---|---|
| 역할 | 순수 데이터 구조 | 외부 입력 **검증** + 직렬화 |
| 의존성 | 표준 라이브러리 | 서드파티 |
| 이 프로젝트 | `domain/entities.py` (안쪽 원) | `adapters/api/schemas/` (HTTP 경계) |

도메인이 pydantic 에 의존하지 않도록 **안쪽은 dataclass, 바깥은 pydantic** 으로 역할을 나눴습니다.

---

`frozen=True, slots=True` 조합은 "값 객체(Value Object)" 를 표현하는 현대 파이썬의 표준 관용구입니다. `LabRecordPatch` 처럼 "변경 의도" 자체를 값 객체로 만들면 `is_empty()` 같은 규칙을 한곳에 둘 수 있어 7 개 DB 라우터의 중복 검사를 없앨 수 있었습니다.
