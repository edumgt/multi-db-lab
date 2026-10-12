> **쉽게 이해하기**
>
> - **한 줄 요약** — 인스턴스 메서드(self: 객체 데이터) · classmethod(cls: 대안 생성자) · staticmethod(둘 다 안 씀: 도우미) · property(계산값을 속성처럼) 를 구분합니다.
> - **비유하면** — 자동차로 치면 '달리다'(self), '공장에서 만들기'(cls), '연비 계산 공식'(static), '현재 속도'(property).
> - **이 프로젝트에서는** — `Post.create(...)` classmethod 가 기본값을 채워 엔티티를 만들고, `settings.allowed_origin_list` property 가 문자열 설정을 리스트로 바꿉니다.
> - **기억할 것** — property 는 가볍고 부작용 없는 계산에만 씁니다.

파이썬 클래스의 **메서드 종류 세 가지(인스턴스 · `@classmethod` · `@staticmethod`)** 와 **`@property`** 는 "이 메서드가 무엇에 접근하는가" 를 선언하는 장치입니다. 이 프로젝트의 엔티티 · 유스케이스 · 게이트웨이에서 각각 쓰이는 자리가 다릅니다.

---

### 1. 인스턴스 메서드 — `self`

```python
# backend/domain/entities.py
def apply(self, patch: LabRecordPatch) -> LabRecord:
    return replace(self, **patch.changes())
```

* 인스턴스 상태를 읽거나(불변 객체는 읽기만) 새 객체를 만듭니다. 가장 기본.

### 2. `@classmethod` — `cls` : 대안 생성자(Alternative Constructor)

```python
@classmethod
def from_dict(cls, raw: Mapping[str, Any]) -> LabRecord:
    return cls(id=str(raw["id"]), title=str(raw["title"]), ...)
```

* "dict 로부터 만든다" 처럼 **생성 방법이 여러 개** 일 때 `__init__` 을 복잡하게 만들지 않고 이름 있는 생성자를 제공합니다.
* `cls(...)` 를 쓰므로 서브클래스에서 호출하면 **서브클래스 인스턴스** 가 만들어집니다(`LabRecord` 대신 하드코딩하면 안 되는 이유).
* 표준 라이브러리 예: `dict.fromkeys()`, `datetime.fromisoformat()`, `Path.cwd()`.

### 3. `@staticmethod` — 클래스 네임스페이스 안의 순수 함수

```python
# backend/adapters/gateways/lab_redis.py
@staticmethod
def _dump(record: LabRecord) -> str:
    return json.dumps(record.to_dict(), ensure_ascii=False)

# backend/adapters/gateways/lab_cassandra.py
@staticmethod
def _row_to_record(row: Any) -> LabRecord: ...
```

* `self` 도 `cls` 도 필요 없지만 **그 클래스와 관련된** 도우미. 모듈 수준 함수로 빼도 되지만 "Redis 게이트웨이 전용 직렬화" 라는 소속을 드러냅니다.
* 테스트에서 `RedisLabRecordRepository._dump(record)` 처럼 인스턴스 없이 호출할 수 있습니다.

### 4. `@property` — 메서드를 속성처럼

```python
# backend/usecases/lab_record_usecase.py
@property
def source(self) -> str:
    return self._repo.source
```

* 호출 측은 `uc.source` 로 읽습니다(괄호 없음). 내부 구현(`_repo` 위임) 을 숨기고, 나중에 계산 방식이 바뀌어도 호출 코드는 그대로입니다.
* setter 를 정의하지 않으면 **읽기 전용** 속성이 됩니다 — 유스케이스의 `source` 를 밖에서 바꿀 수 없습니다.
* 무거운 계산을 property 에 넣지 마세요. 접근마다 실행됩니다. 캐시가 필요하면 `cached_property`(tech008).

### 5. 이름 규칙 — 밑줄

| 표기 | 의미 |
|---|---|
| `_repo` | 내부용(private 관례). 밖에서 접근 가능하지만 "건드리지 말라" 는 신호. `from m import *` 에서 제외 |
| `__secret` | 네임 맹글링(`_ClassName__secret`). 서브클래스와의 이름 충돌 방지용. 보안 목적 아님 |
| `__init__`, `__repr__` | 던더(dunder) 메서드. 파이썬이 호출하는 프로토콜 |
| `_` (단독) | "쓰지 않는 값" — `def list_posts(_: CurrentUser, ...)` |

* 이 프로젝트의 유스케이스·게이트웨이는 협력자를 모두 `self._repo`, `self._client` 로 저장해 **생성자로만 주입** 되는 것을 표현합니다.

### 6. `ClassVar` 와 클래스 속성 상속

```python
class DomainError(Exception):
    default_detail: str = "요청을 처리할 수 없습니다."
    def __init__(self, detail=None):
        self.detail = detail or self.default_detail       # 서브클래스의 값이 보임

class NotFoundError(DomainError):
    default_detail = "리소스를 찾을 수 없습니다."         # 한 줄로 메시지 변경
```

* `self.default_detail` 은 인스턴스 → 클래스 → 부모 클래스 순으로 탐색(MRO) 되므로 서브클래스가 덮어쓴 값이 적용됩니다.
* `type(exc).__mro__` 를 순회하는 `status_code_for()`(error_handlers.py) 도 같은 탐색 순서를 이용합니다.

### 7. 선택 가이드

| 질문 | 답 |
|---|---|
| 인스턴스 데이터가 필요한가? | 인스턴스 메서드 |
| 인스턴스 없이 **그 클래스를 만들어** 돌려주나? | `@classmethod` |
| 인스턴스도 클래스도 필요 없는 도우미인가? | `@staticmethod` (또는 모듈 함수) |
| 계산된 값을 **속성처럼 읽게** 하고 싶은가? | `@property` |

---

`from_dict` 가 `@classmethod` 인 덕분에 7 개 게이트웨이는 각 DB 의 결과를 `LabRecord.from_dict(row)` 한 줄로 엔티티로 바꿉니다. 메서드 종류를 올바르게 고르는 것은 문법 문제가 아니라 **"이 코드가 무엇에 의존하는가" 를 선언하는 설계 행위** 입니다.
