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

### 7. v1 → v2 변경점 (자주 걸리는 것)

| v1 | v2 |
|---|---|
| `.dict()` | `.model_dump()` |
| `.parse_obj()` | `.model_validate()` |
| `class Config:` | `model_config = ConfigDict(...)` |
| `@validator` | `@field_validator` |
| `BaseSettings` (pydantic 본체) | `pydantic_settings.BaseSettings` (별도 패키지) |

### 8. dataclass 와의 역할 분담

| | dataclass (`domain/entities.py`) | pydantic (`adapters/api/schemas/`) |
|---|---|---|
| 검증 | 없음 — 이미 검증된 값만 받음 | 외부 입력 검증 |
| 의존성 | 표준 라이브러리 | 서드파티 |
| 변경 가능성 | frozen | 기본 mutable |
| 위치 | 안쪽 원 | HTTP 경계 |

---

pydantic 의 가치는 **"경계에서 한 번 검증하면 안쪽은 믿을 수 있다"** 는 보장입니다. 그래서 유스케이스의 검사는 비즈니스 규칙(빈 PATCH, self-loop) 에만 집중하고, 타입 · 길이 · 범위 같은 형식 검사는 전부 스키마에 맡겼습니다.
