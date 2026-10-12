파이썬 내장 `json` 모듈은 파이썬 객체와 JSON 문자열 사이의 **직렬화(`dumps`) · 역직렬화(`loads`)** 를 담당합니다. 이 프로젝트에서는 Redis 저장 값, JWT payload, 오류 응답 본문에 쓰입니다.

---

### 1. 기본 매핑

| Python | JSON |
|---|---|
| `dict` | object |
| `list`, `tuple` | array |
| `str` | string |
| `int`, `float` | number |
| `True` / `False` / `None` | `true` / `false` / `null` |

* `datetime`, `UUID`, `Decimal`, `set`, dataclass 는 **기본 변환 불가** → `TypeError: Object of type ... is not JSON serializable`.

### 2. `json.dumps()` 주요 옵션

```python
# backend/adapters/gateways/lab_redis.py
json.dumps(record.to_dict(), ensure_ascii=False)
```

* `ensure_ascii=False`: 한글을 `한글` 로 이스케이프하지 않고 원문 그대로 씁니다. 저장 용량이 줄고 `redis-cli` 로 읽을 때 사람이 읽을 수 있습니다.
* `indent=2`: 보기 좋은 출력(로그·디버깅용). 저장용에는 쓰지 않습니다.
* `sort_keys=True`: 키 정렬. 해시 비교·캐시 키 생성에 유용.
* `default=함수`: 변환 불가 타입을 만났을 때 호출됩니다.
  ```python
  json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o))
  ```
* `separators=(",", ":")`: 공백 제거로 최소 크기.

### 3. `json.loads()` 와 실패 처리

```python
try:
    data: dict[str, Any] = json.loads(raw)
except json.JSONDecodeError as exc:          # ValueError 의 서브클래스
    raise ExternalServiceError(...) from exc
```

* `JSONDecodeError` 는 `.msg`, `.pos`, `.lineno`, `.colno` 속성으로 **어디가 깨졌는지** 알려줍니다.
* `loads` 의 결과 타입은 입력에 따라 dict 일 수도, list 일 수도, 문자열일 수도 있습니다. 신뢰할 수 없는 입력이면 `isinstance(data, dict)` 를 확인하세요.

### 4. 엔티티 ↔ JSON 호환 dict

```python
# backend/domain/entities.py
def to_dict(self) -> dict[str, Any]:
    return {"id": self.id, "title": self.title, "content": self.content, "tags": list(self.tags)}

@classmethod
def from_dict(cls, raw: Mapping[str, Any]) -> LabRecord:
    return cls(id=str(raw["id"]), title=str(raw["title"]), content=str(raw["content"]),
               tags=[str(tag) for tag in (raw.get("tags") or [])])
```

* `to_dict()` 는 **JSON 기본 타입만** 돌려주므로 `json.dumps` 에 바로 넘길 수 있습니다.
* `from_dict()` 는 `str(...)` 로 방어적 변환을 하고 `tags` 누락/`None` 을 빈 리스트로 처리합니다.
* **왕복 테스트**(`tests/test_domain.py`): `from_dict(json.loads(json.dumps(r.to_dict()))) == r`.

### 5. `decode_responses=True` 와의 조합

```python
redis.from_url(settings.redis_url, decode_responses=True)
```

* 기본 Redis 클라이언트는 `bytes` 를 돌려줍니다. `json.loads` 는 bytes 도 받지만, 문자열로 받으면 타입이 단순해지고 `len(raw)` 같은 로깅도 바로 됩니다.

### 6. 웹 프레임워크의 JSON

* **pydantic**(요청/응답 스키마) 이 검증 + 직렬화를 담당합니다. `datetime` 도 ISO 8601 로 자동 변환합니다.
* 직접 응답을 만들 땐 `JSONResponse`:
  ```python
  # backend/adapters/api/error_handlers.py
  return JSONResponse(status_code=code, content={"detail": exc.detail, "error": type(exc).__name__})
  ```
* JWT(`python-jose`) 도 내부적으로 JSON payload 를 Base64 로 감쌉니다. `jwt.decode` 가 돌려주는 것은 `dict` 입니다.

### 7. 파일 입출력 — `dump` / `load` (s 없는 버전)

```python
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, indent=2)
with open("data.json", encoding="utf-8") as f:
    obj = json.load(f)
```

* `encoding="utf-8"` 을 **항상** 명시하세요. Windows 기본 인코딩(cp949) 과 충돌하는 고전적 문제를 피할 수 있습니다.

### 8. 성능이 중요하면

* `orjson` (Rust 구현, dataclass·datetime 네이티브 지원) 이 표준 `json` 보다 수 배 빠릅니다. FastAPI 는 `ORJSONResponse` 를 제공합니다.

---

JSON 처리의 핵심은 **경계에서 한 번만** 변환하는 것입니다. 이 프로젝트는 Redis 게이트웨이 `_dump/_load`, pydantic 스키마, 에러 핸들러 세 지점에만 JSON 변환이 있고, 유스케이스와 도메인은 JSON 의 존재를 모릅니다.
