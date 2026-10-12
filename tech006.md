파이썬 **예외 처리**는 `try / except / else / finally` 네 절과 **커스텀 예외 계층**, 그리고 `raise ... from ...` 체이닝으로 구성됩니다. 이 프로젝트는 "드라이버 예외를 도메인 예외로 번역한다"는 원칙으로 13 개 게이트웨이를 통일했습니다.

---

### 1. 네 절의 역할

| 절 | 실행 조건 | 용도 |
|---|---|---|
| `try` | 항상 | 실패할 수 있는 코드 **만** 짧게 |
| `except` | 예외 발생 시 | 처리 또는 변환 |
| `else` | 예외가 **없었을 때만** | 성공 경로. `try` 안에 넣으면 그 코드의 예외까지 잡혀 버리는 것을 방지 |
| `finally` | 항상 | 자원 정리·로깅 |

> ```python
> # backend/adapters/gateways/lab_redis.py
> def _load(self, raw: str, *, key: str) -> LabRecord:
>     try:
>         data: dict[str, Any] = json.loads(raw)
>     except json.JSONDecodeError as exc:
>         raise ExternalServiceError(f"Redis 값이 올바른 JSON 이 아닙니다: {key}", service=self.source) from exc
>     else:
>         return LabRecord.from_dict(data)      # from_dict 의 KeyError 는 여기서 잡히지 않음 — 의도된 것
>     finally:
>         logger.debug("redis load key=%s bytes=%d", key, len(raw))
> ```

### 2. 커스텀 예외 계층 설계

```python
# backend/domain/exceptions.py
class DomainError(Exception):
    default_detail: str = "요청을 처리할 수 없습니다."
    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)

class NotFoundError(DomainError):        default_detail = "리소스를 찾을 수 없습니다."
class ValidationError(DomainError):      default_detail = "요청 값이 올바르지 않습니다."
class PermissionDeniedError(DomainError): ...
class AuthenticationError(DomainError): ...
class ConfigurationError(DomainError): ...
class ExternalServiceError(DomainError):
    def __init__(self, detail=None, *, service: str = "unknown"):
        self.service = service
        super().__init__(detail)
```

* **루트 하나** 를 두면 `except DomainError` 로 모두 잡을 수 있고, 구체 타입으로 세분 처리도 가능합니다.
* 메시지를 **클래스 속성(`default_detail`)** 으로 두면 서브클래스가 한 줄로 기본 메시지를 바꿉니다.
* 예외 객체에 **구조화된 속성**(`detail`, `service`) 을 두면 `str(exc)` 파싱 없이 응답을 구성할 수 있습니다.

### 3. `raise ... from exc` — 예외 체이닝

* 원인 예외가 `__cause__` 에 보존되어 로그에 "The above exception was the direct cause of the following exception" 이 함께 찍힙니다.
* `from None` 을 쓰면 원인을 **의도적으로 숨깁니다**(보안상 내부 정보 노출을 막을 때).

> ```python
> try:
>     self._collection.insert_one(record.to_dict())
> except PyMongoError as exc:
>     raise ExternalServiceError("MongoDB 저장 실패", service=self.source) from exc
> ```

### 4. 드라이버별 "루트 예외" 를 하나만 잡기

| 드라이버 | 잡은 예외 | 파일 |
|---|---|---|
| pymongo | `PyMongoError` | `lab_mongo.py` |
| SQLAlchemy | `SQLAlchemyError` | `lab_postgres.py`, `sql_repositories.py` |
| redis-py | `RedisError` | `lab_redis.py` |
| opensearch-py | `OpenSearchException` (단, `NotFoundError` 는 먼저 별도 처리) | `lab_opensearch.py` |
| clickhouse-connect | `ClickHouseError` | `lab_clickhouse.py` |
| cassandra-driver | `DriverException` | `lab_cassandra.py` |
| neo4j | `Neo4jError`, `ServiceUnavailable` | `graph_neo4j.py` |
| boto3 | `ClientError`, `BotoCoreError` | `employee_dynamodb.py` |
| supabase | `APIError`, `OSError` | `lab_supabase.py` |

* 라이브러리 문서에서 **예외 계층의 루트** 를 찾아 그것만 잡습니다. `except Exception` 은 `KeyboardInterrupt` 를 제외한 모든 것을 삼켜 버그를 숨깁니다.

### 5. 구체 예외 먼저, 넓은 예외 나중

```python
# backend/adapters/gateways/lab_opensearch.py
try:
    response = self._client.search(...)
except OpenSearchNotFound:           # "인덱스 없음" 은 정상 흐름 → 빈 목록
    return []
except OpenSearchException as exc:   # 그 외는 장애
    raise ExternalServiceError(...) from exc
```

* `except` 절은 **위에서부터** 매칭됩니다. 순서를 바꾸면 `NotFound` 절은 영원히 실행되지 않습니다.

### 6. "알고 있는 경우만 무시" — 조건부 재발생

```python
# backend/adapters/gateways/graph_neo4j.py
try:
    session.run("CALL gds.graph.drop($graph_name, false) ...").consume()
except ClientError as exc:
    if "does not exist" not in str(exc):
        raise                        # 인자 없는 raise = 현재 예외를 그대로 재발생 (스택 보존)
```

### 7. 정리 단계에서의 예외 격리

```python
# backend/infrastructure/clients.py
def close_all(self) -> None:
    while self._closers:
        name, closer = self._closers.pop()
        try:
            closer()
        except Exception:            # noqa: BLE001 — 한 자원의 실패가 나머지 정리를 막으면 안 됨
            logger.exception("failed to close %s", name)
```

* `except Exception` 이 정당한 **드문 경우**: 종료 루틴. 반드시 로그를 남기고(`logger.exception` 은 스택 포함) 주석으로 이유를 적습니다.

### 8. 예외 → HTTP 상태코드 변환은 바깥에서

```python
# backend/adapters/api/error_handlers.py
_STATUS_BY_EXCEPTION = {NotFoundError: 404, ValidationError: 400, PermissionDeniedError: 403,
                        AuthenticationError: 401, ExternalServiceError: 502, DomainError: 500, ...}

def status_code_for(exc: DomainError) -> int:
    for klass in type(exc).__mro__:          # 가장 구체적인 조상부터 탐색
        if klass in _STATUS_BY_EXCEPTION:
            return _STATUS_BY_EXCEPTION[klass]
```

* 도메인·유스케이스에는 숫자 404 가 **한 번도** 등장하지 않습니다. 같은 유스케이스를 CLI 에서 쓰면 다른 변환기를 붙이면 됩니다.

---

좋은 예외 처리의 핵심은 "어디서 잡고 어디서 변환할 것인가" 를 계층별로 정해 두는 것입니다. 이 프로젝트의 규칙은 간단합니다 — **게이트웨이는 드라이버 예외를 도메인 예외로, 에러 핸들러는 도메인 예외를 HTTP 로, 유스케이스는 도메인 예외만 던진다.**
