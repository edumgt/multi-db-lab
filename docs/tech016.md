> **쉽게 이해하기**
>
> - **한 줄 요약** — 타입 힌트를 '실행 시 검증 규칙' 으로 바꾸는 라이브러리입니다. pydantic-settings 는 같은 방식으로 환경변수를 읽습니다.
> - **비유하면** — 공항 보안검색대. 밖에서 들어오는 요청(HTTP) 과 설정(환경변수) 은 여기서만 검사하고, 안쪽(도메인) 은 다시 검사하지 않습니다.
> - **이 프로젝트에서는** — `schemas/` 의 `LabRecordCreate` (`Field(min_length=1)`) 와 `settings.py` 의 `APP_` 접두사 환경변수가 전부입니다.
> - **기억할 것** — 도메인 엔티티는 dataclass, HTTP 경계만 pydantic.

**pydantic** 은 타입 힌트를 **런타임 검증 규칙** 으로 바꾸는 라이브러리이고, **pydantic-settings** 는 같은 원리로 환경변수를 읽습니다. 이 프로젝트는 HTTP 경계(`backend/adapters/api/schemas/`) 와 설정(`backend/infrastructure/settings.py`) 두 곳에서만 pydantic 을 사용합니다 — 도메인은 pydantic 을 모릅니다.

---

### 1. BaseModel — 타입 힌트가 곧 검증 규칙

```python
# backend/adapters/api/schemas/lab.py
class LabRecordCreate(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
```

* 잘못된 JSON(`"tags": "a"`) 은 FastAPI 가 **422 Unprocessable Entity** 로 거절합니다. 유스케이스에는 유효한 값만 도달합니다.
* `Field()` 로 길이 · 범위(`ge`, `le`) · 설명 · 예시를 선언합니다. OpenAPI 문서에 그대로 반영됩니다.
* v2 에서는 문자열 · 리스트 모두 `min_length` / `max_length` 로 길이를 제약합니다 (v1 의 `min_items` 는 사라졌습니다 — 7번 참고).

### 2. `Literal` 과 범위 제약

```python
class VectorQueryRequest(BaseModel):
    values: list[float] = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)

class GraphAnalysisRequest(BaseModel):
    algorithm: GraphAlgorithm = "pagerank"        # Literal["pagerank", "degree"] — 도메인 별칭 재사용
```

* 도메인의 `Literal` 별칭을 스키마에서 **그대로 import** 해 두 계층의 허용 값이 어긋날 수 없게 했습니다.

### 3. 스키마 → 엔티티 변환 메서드

```python
class LabRecordUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None

    def to_patch(self) -> LabRecordPatch:
        return LabRecordPatch(title=self.title, content=self.content, tags=self.tags)
```

* pydantic 모델이 **도메인 객체를 만들어 돌려주는** 방향은 허용(바깥 → 안쪽). 반대로 도메인이 pydantic 을 import 하면 의존성 규칙 위반입니다.
* `model_dump()` 로 dict 를 만들어 라우터에서 `if v is not None` 필터링하던 과거 코드는 `to_patch()` + `LabRecordPatch.changes()` 로 옮겨졌습니다.

### 4. 응답 모델 — `response_model`

```python
@sub.get("", response_model=list[LabRecordRead])
def list_records(...) -> list[LabRecordRead]: ...
```

* 응답에서 **선언된 필드만** 내보냅니다(ORM 객체의 `password_hash` 같은 필드가 새는 것을 방지).
* `datetime` 은 ISO 8601 문자열로 자동 직렬화됩니다(`PostOut.created_at`).

### 5. pydantic-settings — 환경변수를 타입 있게

```python
# backend/infrastructure/settings.py
class Settings(BaseSettings):
    clickhouse_port: int = 8123
    vector_provider: VectorProviderName = "pinecone"       # Literal["pinecone", "weaviate", "qdrant"]
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

settings = Settings()
```

* `APP_CLICKHOUSE_PORT=abc` → 기동 즉시 `ValidationError`. "포트가 문자열이라 300 줄 뒤에서 터지는" 상황을 없앱니다.
* `APP_VECTOR_PROVIDER=pinecon`(오타) 도 기동 시 잡힙니다.
* 우선순위: **실제 환경변수 > `.env` 파일 > 코드 기본값**. docker-compose 의 `environment:` 가 `.env` 를 덮어씁니다.
* `extra="ignore"`: 선언하지 않은 `APP_*` 변수가 있어도 무시. `forbid` 로 바꾸면 오타 변수를 잡을 수 있습니다.

### 6. 파생 값은 `cached_property` 로

```python
@cached_property
def allowed_origin_list(self) -> list[str]:
    return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
```

* 쉼표 구분 문자열 → 리스트 변환을 설정 객체 안에 두면 main.py 가 split 로직을 몰라도 됩니다.
* pydantic v2 의 `BaseSettings` 는 `cached_property` 를 필드로 오인하지 않습니다.

### 7. pydantic 2.0 — 무엇이 달라졌고 이 프로젝트는 어디에 기대고 있나

이 프로젝트는 `pydantic-settings==2.8.1` 을 통해 **pydantic 2.x** 를 사용합니다 (FastAPI 0.100 이후는 v2 전용). 2023년 6월에 나온 v2 는 단순 업그레이드가 아니라 **검증 엔진을 Rust(`pydantic-core`) 로 다시 쓴 메이저 변경** 이어서, 메서드 이름 · 기본 동작 · 에러 모양이 모두 바뀌었습니다. 아래는 이 프로젝트 코드가 v2 문법에 기대고 있는 지점을 중심으로 정리한 것입니다.

#### 7-1. 왜 바뀌었나 — 성능과 일관성
* 검증 로직이 Rust 로 내려가 v1 대비 **5 ~ 50배** 빨라졌습니다. FastAPI 가 요청마다 스키마를 검증하므로 체감 효과가 큽니다.
* v1 은 "되는 대로 변환해 주는" 느슨함이 버그의 원천이었습니다. v2 는 **lax(기본) / strict** 두 모드를 명확히 나누고, lax 모드에서도 위험한 변환은 끊었습니다 (7-3 참고).
* 이름 충돌을 피하려고 모델 메서드를 전부 `model_` 접두사로 통일했습니다 (`dict()` 라는 이름은 사용자가 `dict` 라는 필드를 만들면 충돌했음).

#### 7-2. 이름 변경표 — 옛 문서 · 블로그를 볼 때 머릿속에서 바꿔 읽기

| v1 | v2 | 비고 |
|---|---|---|
| `.dict()` | `.model_dump()` | `mode="json"` 으로 JSON 호환 타입(datetime → 문자열)으로 덤프 |
| `.json()` | `.model_dump_json()` | 문자열 반환 |
| `.parse_obj(d)` | `.model_validate(d)` | dict → 모델 |
| `.parse_raw(s)` | `.model_validate_json(s)` | JSON 문자열 → 모델 (Rust 가 직접 파싱, 가장 빠름) |
| `.from_orm(obj)` | `.model_validate(obj, from_attributes=True)` | `ConfigDict(from_attributes=True)` 와 함께 |
| `.copy()` | `.model_copy(update=...)` | |
| `.construct()` | `.model_construct()` | 검증 생략 생성 |
| `.schema()` | `.model_json_schema()` | OpenAPI 에 쓰이는 JSON Schema |
| `.__fields__` | `.model_fields` | 필드 메타데이터 |
| `.update_forward_refs()` | `.model_rebuild()` | 순환 참조 해소 |
| `class Config:` | `model_config = ConfigDict(...)` | 설정은 `SettingsConfigDict(...)` |
| `@validator("f")` | `@field_validator("f")` | 항상 `@classmethod` 와 함께 |
| `@root_validator` | `@model_validator(mode="after")` | 필드 간 교차 검증 |
| `Field(min_items=1)` | `Field(min_length=1)` | **list 도 `min_length`** — 이 프로젝트 `values: list[float] = Field(min_length=1)` |
| `Field(regex=...)` | `Field(pattern=...)` | |
| `Field(const=True)` | `Literal["bearer"]` | `LoginResponse.token_type` 이 이 방식 |
| `Field(allow_mutation=False)` | `ConfigDict(frozen=True)` | |
| `parse_obj_as(list[M], data)` | `TypeAdapter(list[M]).validate_python(data)` | 모델이 아닌 타입 검증 |
| `pydantic.BaseSettings` | `pydantic_settings.BaseSettings` | **별도 패키지** (`pip install pydantic-settings`) |

> 옛 이름을 쓰면 v2 에서도 당장은 동작하지만 `PydanticDeprecatedSince20` 경고가 나고, v3 에서 제거됩니다.

#### 7-3. 기본 동작 변화 — 조용히 결과가 달라지는 것들
가장 주의할 부분입니다. 코드가 에러 없이 돌지만 **값이 달라지는** 경우가 있습니다.

1. **`int → str` 자동 변환 중단**
   ```python
   class LabRecordCreate(BaseModel):
       id: str = Field(min_length=1)

   LabRecordCreate(id=123, title="t", content="c")
   # v1: id="123" 으로 조용히 변환
   # v2: ValidationError — Input should be a valid string
   ```
   JSON 에 `"id": 123` 을 보내면 v2 는 422 를 돌려줍니다. 숫자 → 문자열은 lax 모드에서도 허용하지 않습니다. 반대로 `"8123"` → `int` (문자열 → 숫자) 는 여전히 허용되므로 환경변수 파싱(`APP_CLICKHOUSE_PORT="8123"`) 은 그대로 동작합니다.

2. **`Optional` 필드가 더 이상 자동으로 선택이 아님**
   ```python
   class LabRecordUpdate(BaseModel):
       title: str | None            # v1: 생략 가능(None). v2: 필수! 생략하면 "Field required"
       title: str | None = None     # v2 에서 "생략 가능" 을 원하면 반드시 기본값을 적어야 함
   ```
   이 프로젝트의 `LabRecordUpdate` · `PostUpdate` 가 전부 `= None` 을 명시한 이유입니다. "None 을 허용한다" 와 "생략할 수 있다" 를 v2 는 **별개** 로 봅니다.

3. **`Field(default=None, min_length=1)` 의 의미**
   `PostUpdate.title: str | None = Field(default=None, min_length=1, max_length=120)` 은 "생략하거나 None 이면 통과, 값을 주면 1 ~ 120자" 라는 뜻입니다. v2 는 제약을 `None` 에는 적용하지 않고 `str` 쪽에만 적용합니다.

4. **기본값은 검증하지 않음** (`validate_default=False` 가 기본). `top_k: int = Field(default=3, ge=1, le=20)` 의 3 은 그대로 신뢰합니다. 기본값까지 검증하려면 `Field(validate_default=True)`.

5. **`model_dump()` 가 중첩 모델까지 전부 dict 로** 바꿉니다. v1 의 `.dict()` 와 같지만, `mode="json"` 을 주면 `datetime` · `Decimal` · `UUID` 까지 JSON 으로 바로 넣을 수 있는 원시 타입으로 바꿔 줍니다 (FastAPI 응답은 내부적으로 이 모드를 사용).

6. **에러 객체 모양이 바뀜** — `.errors()` 각 항목에 `type` · `loc` · `msg` · `input` 이 들어가고, `url` 로 공식 문서 링크가 붙습니다. FastAPI 422 응답의 `detail` 이 그대로 이 리스트입니다.
   ```json
   {"detail": [{"type": "string_too_short", "loc": ["body", "title"],
                "msg": "String should have at least 1 character",
                "input": "", "ctx": {"min_length": 1},
                "url": "https://errors.pydantic.dev/2.14/v/string_too_short"}]}
   ```
   `type` 값(`string_too_short` · `missing` · `literal_error` · `string_type` …) 이 기계가 읽을 수 있는 코드이므로, 프론트엔드에서 에러를 필드별로 표시할 때 `msg` 대신 이 코드를 기준으로 분기하면 pydantic 버전이 올라가 문구가 바뀌어도 안전합니다.

#### 7-4. v2 검증기 — 이 프로젝트가 안 쓴 이유와, 쓸 때의 모양
```python
from pydantic import BaseModel, Field, field_validator, model_validator

class GraphEdgeCreate(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    weight: float = 1.0

    @field_validator("source", "target")          # 필드 하나(여럿)의 값 검사 · 정규화
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")                # 필드 간 관계 검사
    def no_self_loop(self) -> "GraphEdgeCreate":
        if self.source == self.target:
            raise ValueError("self-loop 은 허용하지 않습니다")
        return self
```
* `mode="before"` 는 원시 입력(dict) 단계, `mode="after"`(기본) 는 타입 변환이 끝난 뒤 실행됩니다.
* `@field_validator` 는 **반드시 `@classmethod`** 로 — v1 과 달리 인스턴스가 아직 없는 시점에 호출됩니다.
* 이 프로젝트는 self-loop 검사를 스키마가 아닌 **유스케이스(`graph_usecase.py`)** 에 두었습니다. "self-loop 금지" 는 HTTP 형식이 아니라 **비즈니스 규칙** 이어서, HTTP 가 아닌 다른 입구(CLI · 배치)에서도 지켜져야 하기 때문입니다. 스키마 검증기는 **공백 제거 · 대소문자 통일 같은 형식 정리** 에만 쓰는 것이 이 프로젝트의 기준입니다.

#### 7-5. `computed_field` · `Annotated` · `TypeAdapter`
```python
from typing import Annotated
from pydantic import computed_field, TypeAdapter

class PostOut(BaseModel):
    title: str
    content: str

    @computed_field                                # 직렬화에 포함되는 파생 값 (v1 에는 없던 기능)
    @property
    def preview(self) -> str:
        return self.content[:40]

Limit = Annotated[int, Field(ge=1, le=200)]        # 제약을 타입 별칭으로 재사용

TypeAdapter(list[LabRecordRead]).validate_python(rows)   # BaseModel 없는 타입도 검증
```
* FastAPI 라우터의 `Annotated[int, Query(ge=1, le=200)]` (lab_router.py) 는 내부에서 pydantic `Field` 제약으로 변환됩니다. 같은 엔진이 바디 · 쿼리 · 경로 파라미터를 전부 검증합니다.
* `type VectorProviderName = Literal[...]` (파이썬 3.12 의 `type` 문) 도 v2 가 그대로 해석합니다 — `settings.py` 가 이 방식입니다.

#### 7-6. pydantic-settings 2.x 가 별도 패키지인 이유와 v2 전용 옵션
* v1 의 `BaseSettings` 는 pydantic 본체에 있었지만, 환경변수 · `.env` · 비밀 파일 읽기는 "검증" 과 다른 관심사여서 v2 에서 **`pydantic-settings`** 로 분리되었습니다. 본체는 가벼워지고, 설정 패키지는 독립적으로 버전이 올라갑니다.
* 설정은 `SettingsConfigDict` 로 적습니다 (일반 모델의 `ConfigDict` 를 확장한 것). 이 프로젝트가 쓰는 옵션과 자주 함께 쓰는 옵션:

| 옵션 | 이 프로젝트 | 뜻 |
|---|---|---|
| `env_prefix="APP_"` | ✅ | `clickhouse_port` ↔ `APP_CLICKHOUSE_PORT` |
| `env_file=".env"` | ✅ | 파일에서도 읽음 (실제 환경변수가 우선) |
| `extra="ignore"` | ✅ | 선언 안 한 `APP_*` 는 무시. `"forbid"` 면 오타 변수 발견 |
| `case_sensitive=False` | 기본값 | `app_clickhouse_port` 도 인식 |
| `env_nested_delimiter="__"` | 미사용 | `APP_DB__HOST` → `db.host` 처럼 중첩 모델에 매핑 |
| `env_file_encoding="utf-8"` | 기본값 | `.env` 인코딩 |
| `secrets_dir="/run/secrets"` | 미사용 | Docker secrets 파일 읽기 |

* `list[str]` 타입 필드는 환경변수 값을 **JSON 으로 파싱** 합니다 (`APP_HOSTS='["a","b"]'`). 이 프로젝트는 운영자가 `a,b` 처럼 쉼표로 적는 편이 자연스러워, 필드는 `str` 로 받고 6번의 `cached_property` 에서 나눕니다.
* `Settings()` 생성 시점에 모든 변환 · 검증이 끝납니다. 그래서 `settings = Settings()` 를 모듈 최상단에 두면 **import 되는 순간** 잘못된 설정이 드러납니다 — 의도된 "빨리 실패(fail fast)" 입니다.

#### 7-7. 마이그레이션 메모
* 공식 도구 **`bump-pydantic`** 이 `.dict()` → `.model_dump()` 같은 기계적 변경을 대부분 자동으로 바꿔 줍니다.
* 급하면 `from pydantic.v1 import BaseModel` 로 v1 API 를 그대로 쓸 수 있지만, FastAPI 스키마에는 v2 모델만 쓸 수 있으므로 과도기용입니다.
* 검색 결과가 v1 문서인지 확인하는 요령: `class Config:` · `.dict()` · `@validator` 가 보이면 v1 입니다. 공식 문서는 `docs.pydantic.dev/latest/` 가 v2, `/1.10/` 가 v1 입니다.

### 8. dataclass 와의 역할 분담

| | dataclass (`domain/entities.py`) | pydantic (`adapters/api/schemas/`) |
|---|---|---|
| 검증 | 없음 — 이미 검증된 값만 받음 | 외부 입력 검증 |
| 의존성 | 표준 라이브러리 | 서드파티 |
| 변경 가능성 | frozen | 기본 mutable |
| 위치 | 안쪽 원 | HTTP 경계 |

---

pydantic 의 가치는 **"경계에서 한 번 검증하면 안쪽은 믿을 수 있다"** 는 보장입니다. 그래서 유스케이스의 검사는 비즈니스 규칙(빈 PATCH, self-loop) 에만 집중하고, 타입 · 길이 · 범위 같은 형식 검사는 전부 스키마에 맡겼습니다.
