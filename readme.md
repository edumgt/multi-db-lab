# FastAPI Grid Lab

> Korean guide: [readme-kr.md](readme-kr.md) · technical notes: [docs/](docs/) · LLM index: [llms.txt](llms.txt)

A hands-on multi-database lab that wires **PostgreSQL, MongoDB, DynamoDB, Supabase, Pinecone, Weaviate, Neo4j, Redis, OpenSearch, ClickHouse, Cassandra, and Qdrant** into one FastAPI backend.
The frontend is an HTML + vanilla JS SPA with login, AG Grid CRUD, and a **canvas multi-DB engine** (drop a DB icon on the canvas, connect it to the Grid node, and that database's rows are fetched and merged into the grid).

---

## Contents

1. [Stack](#stack)
2. [Backend architecture](#backend-architecture)
3. [Intermediate Python and Clean Architecture](#intermediate-python-and-clean-architecture)
4. [Dependencies in detail](#dependencies-in-detail)
5. [Environment variables](#environment-variables)
6. [Project layout](#project-layout)
7. [How to run](#how-to-run)
8. [API summary](#api-summary)
9. [Multi-DB engine (canvas)](#multi-db-engine-canvas)

---

## Stack

### Backend

| Area | Technology | Version | Role |
|---|---|---|---|
| Language | Python | 3.12 | Server |
| Web framework | FastAPI | 0.115 | REST API |
| ASGI server | Uvicorn | 0.34 | Async HTTP server |
| ORM | SQLAlchemy | 2.0 | PostgreSQL models and queries |
| DB driver | psycopg[binary] | 3.2 | PostgreSQL connections |
| Auth | python-jose | 3.3 | JWT issue and verify |
| Hashing | passlib[bcrypt] | 1.7 | Password hashing |
| Settings | pydantic-settings | 2.8 | Env parsing (`APP_` prefix) |
| AWS SDK | boto3 | 1.37 | DynamoDB CRUD |
| MongoDB driver | pymongo | 4.10 | MongoDB CRUD |
| Supabase client | supabase-py | 2.11 | Supabase REST API |
| Vector DB (cloud) | pinecone | 5.4 | Vector store and search |
| Vector DB (self-host) | weaviate-client | 4.9 | Vector store and search |
| Graph DB | neo4j | 5.26 | Graph store and analysis |
| Key-value (OSS) | redis | 5.2 | Cache / key-value store |
| Search (OSS) | opensearch-py | 2.8 | Document search and indexing |
| OLAP (OSS) | clickhouse-connect | 0.8 | Columnar analytics |
| Wide-column (OSS) | cassandra-driver | 3.29 | CQL wide-column store |
| Vector DB (OSS) | qdrant-client | 1.12 | Vector store and search |

### Databases

| Kind | Technology | Role |
|---|---|---|
| RDBMS | PostgreSQL 16 | Users, posts, lab_records |
| Document | MongoDB | Lab documents |
| Key-value / wide-column | AWS DynamoDB | Employee entities |
| BaaS | Supabase (PostgreSQL) | lab_records table |
| Vector | Pinecone | Cloud vector index |
| Vector | Weaviate | Local vector collection |
| Graph | Neo4j | Entity nodes, relationships, GDS |
| Key-value (OSS) | Redis | lab_records-shaped JSON values |
| Search (OSS) | OpenSearch | lab_records index |
| OLAP (OSS) | ClickHouse | lab_records MergeTree table |
| Wide-column (OSS) | Cassandra | lab_records CQL table |
| Vector (OSS) | Qdrant | Local vector collection |

### Frontend

| Area | Technology | Role |
|---|---|---|
| Language | HTML5 + vanilla JS | SPA |
| Data grid | AG Grid Community | Post CRUD |
| CSS | Tailwind CSS (CDN) | UI styling |

---

## Backend architecture

`backend/` is Clean Architecture's four circles (Entities, Use Cases, Interface Adapters, Frameworks & Drivers) mapped onto directories.

```
backend/
├── domain/                     # 1 Entities — innermost circle, imports nothing
│   ├── entities.py             #    frozen dataclasses: LabRecord, LabRecordPatch, Employee, User, Post, VectorMatch …
│   ├── exceptions.py           #    DomainError hierarchy (NotFoundError, ValidationError, ExternalServiceError …)
│   └── ports.py                #    ABC ports: LabRecordRepository, VectorStore, GraphStore, PasswordHasher, TokenProvider …
├── usecases/                   # 2 Use Cases — application rules. Import domain only
│   ├── lab_record_usecase.py   #    one CRUD rule shared by 7 DB routers (reject empty PATCH, 404)
│   ├── vector_usecase.py       #    provider-agnostic vector upsert/query
│   ├── graph_usecase.py        #    graph rules such as no self-loops
│   ├── employee_usecase.py
│   ├── post_usecase.py         #    "only the author may edit/delete" (no HTTPException)
│   └── auth_usecase.py         #    login / authenticate / ensure_user
├── adapters/                   # 3 Interface Adapters — outer shape <-> inner shape
│   ├── gateways/               #    port implementations (driver -> entity)
│   ├── security/               #    bcrypt_hasher.py, jwt_token_provider.py
│   └── api/                    #    HTTP controllers + presenters
├── infrastructure/             # 4 Frameworks & Drivers
│   ├── settings.py             #    pydantic-settings (APP_ prefix)
│   ├── orm.py                  #    SQLAlchemy engine / Session / UserRow / PostRow
│   └── clients.py              #    13 driver clients as lru_cache singletons + ResourceRegistry
└── main.py                     # composition root: lifespan, CORS, routers, error handlers, seed
tests/                          # unit tests that need no database + dependency-direction checks
docs/                           # tech001.md–tech018.md learning notes
```

**Dependency direction (outside may point inward only):**

```
main.py ──▶ adapters ──▶ usecases ──▶ domain
   │            │
   └──▶ infrastructure ◀┘ (gateways reference driver types only; deps.py constructs them)
```

This is enforced by a test (`tests/test_architecture.py`) that scans `import` statements with `ast`, not by documentation alone. See [Intermediate Python and Clean Architecture](#intermediate-python-and-clean-architecture).

---

## Intermediate Python and Clean Architecture

This section records **which file implements** each of the eight study topics and **how it was verified**.
Each source module docstring repeats the same notes under `[Python 중급 적용 사례 — …]` / `[Clean Architecture 적용 사례 — …]`.

### Verification summary

| Check | Command | Result |
|---|---|---|
| Unit and architecture tests | `pytest tests` | 17 passed |
| Static types | `mypy backend` | Success: no issues found in 46 source files |
| Real store round-trip (Redis, MongoDB) | TestClient POST/GET/PATCH/DELETE | 201 / 200 / 200 / 204; empty PATCH → 400; missing id → 404 |
| Failure and config mapping | OpenSearch down, Supabase unset, bad JWT | 502 `ExternalServiceError`, 400 `ConfigurationError`, 401 + `WWW-Authenticate: Bearer` |

---

### 1. Intermediate Python

#### 1-1. Abstract classes and interfaces — `abc.ABC` + `@abstractmethod`

**Where:** `backend/domain/ports.py` (definition) → `backend/adapters/gateways/*.py`, `backend/adapters/security/*.py`, `tests/fakes.py` (implementations)

```python
# backend/domain/ports.py
class LabRecordRepository(ABC):
    source: ClassVar[str] = "unknown"          # implementations must override this class attribute

    @abstractmethod
    def add(self, record: LabRecord) -> LabRecord: ...
    @abstractmethod
    def list(self, limit: int) -> list[LabRecord]: ...
    @abstractmethod
    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord | None: ...
    @abstractmethod
    def delete(self, record_id: str) -> bool: ...
```

| Port (ABC) | Implementations |
|---|---|
| `LabRecordRepository` | Mongo, Postgres, Supabase, Redis, OpenSearch, ClickHouse, Cassandra, and (tests) `InMemoryLabRecordRepository` |
| `VectorStore` | Pinecone, Weaviate, Qdrant |
| `GraphStore` | `Neo4jGraphStore` |
| `EmployeeRepository` | `DynamoDbEmployeeRepository` |
| `UserRepository` / `PostRepository` | SQL repositories and in-memory test doubles |
| `PasswordHasher` / `TokenProvider` | bcrypt / JWT, plus `PlainTextHasher` / `StaticTokenProvider` in tests |

**Enforcement:** `tests/test_domain.py::test_abc_forces_full_implementation` — instantiating a subclass that only implements `add` raises `TypeError`.
There is also one `typing.Protocol` example (`Closeable`: structural subtyping — `close()` is enough, no inheritance required).

#### 1-2. Type hints and mypy

**Where:** every module. Config is `mypy.ini` (`disallow_untyped_defs = True` is strictest on domain and usecases).

| Feature | Example | File |
|---|---|---|
| `from __future__ import annotations` | forward refs, cycles | all modules |
| PEP 695 `type` alias | `type PostSortKey = Literal["created_at:desc", …]` | `domain/entities.py` |
| `Literal` | `GraphAlgorithm`, `VectorProviderName` | `domain/entities.py`, `infrastructure/settings.py` |
| `ClassVar` | `source: ClassVar[str]` | `domain/ports.py`, every gateway |
| `Final` | `COLUMNS`, `_STATUS_BY_EXCEPTION` | `gateways/lab_clickhouse.py`, `api/error_handlers.py` |
| `Mapping` / `Sequence` / `Iterable` | read-only, covariant inputs | `domain/entities.py`, `domain/ports.py`, `api/presenters.py` |
| `Callable[[], T]` | strategy table of repository factories | `api/deps.py` |
| `Annotated[T, Depends(…)]` | `CurrentUser` | `api/deps.py`, routers |
| `Protocol` + `@runtime_checkable` | `Closeable` | `domain/ports.py` |
| `typing.cast` | inaccurate driver stubs | `gateways/lab_postgres.py`, `gateways/lab_redis.py` |
| `Mapped[...]` (SQLAlchemy 2.0) | typed columns | `infrastructure/orm.py` |
| keyword-only `*` | `update(post_id, *, title, content)` | `domain/ports.py`, `usecases/post_usecase.py` |

**Check:** `mypy backend` → `Success: no issues found in 46 source files`.
Two real mypy findings during development (SQLAlchemy `RowMapping` key types, redis-py sync/async stubs) were resolved with `cast`, and the reason is commented on those lines.

#### 1-3. Exceptions — `try/except/else/finally` and a custom hierarchy

**Hierarchy:** `backend/domain/exceptions.py`

```
DomainError (message inherited via the default_detail class attribute)
├── NotFoundError · ValidationError · PermissionDeniedError · AuthenticationError
├── ConfigurationError · UnsupportedProviderError
└── ExternalServiceError(service=…)   ← wraps driver exceptions
```

**All four clauses in one place:** `_load()` in `backend/adapters/gateways/lab_redis.py`

```python
def _load(self, raw: str, *, key: str) -> LabRecord:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExternalServiceError(f"Redis value is not valid JSON: {key}", service=self.source) from exc
    else:
        return LabRecord.from_dict(data)
    finally:
        logger.debug("redis load key=%s bytes=%d", key, len(raw))
```

| Pattern | Where |
|---|---|
| Driver exception → domain exception + `raise … from exc` | every gateway |
| Specific exception before the general one | `gateways/lab_opensearch.py` |
| Ignore only a known case, re-raise the rest | `gateways/graph_neo4j.py` |
| Isolate cleanup failures | `infrastructure/clients.py::ResourceRegistry.close_all` |
| `try/finally` resource guarantee | `infrastructure/orm.py::get_db`, `main.py::lifespan` |
| Context manager commit/rollback | `gateways/lab_postgres.py` (`with engine.begin()`) |
| Rollback then re-raise | `gateways/sql_repositories.py` |
| Exception → HTTP status (MRO walk) | `api/error_handlers.py::status_code_for` |

**Check:** `tests/test_domain.py::test_exception_hierarchy_and_chaining`, plus TestClient checks for 400/401/404/502.

#### 1-4. JSON — `json.dumps()` / `json.loads()`

| Where | What |
|---|---|
| `gateways/lab_redis.py` | store with `ensure_ascii=False`; load with `JSONDecodeError` handling |
| `domain/entities.py` | `to_dict()` / `from_dict()` accept any `Mapping` (pymongo, RowMapping, OpenSearch `_source`) |
| `api/error_handlers.py` | `JSONResponse` body `{"detail", "error", "service"}` |
| `security/jwt_token_provider.py` | defensive `isinstance(subject, str)` after JWT decode |
| pydantic schemas | JSON validation at the HTTP boundary, then `.to_entity()` / `.to_patch()` |

**Check:** `tests/test_domain.py::test_entity_is_immutable_and_json_roundtrips`.

---

### 2. Clean Architecture

#### 2-1. Layering

| Circle | Directory | Contains | Does **not** contain |
|---|---|---|---|
| Entities | `domain/` | dataclasses, exceptions, ABC ports | FastAPI, SQLAlchemy, pydantic, drivers |
| Use Cases | `usecases/` | six use-case classes | HTTP status codes, SQL, serialization |
| Interface Adapters | `adapters/` | 13 gateways, 2 security adapters, controllers, presenters, schemas | business decisions |
| Frameworks & Drivers | `infrastructure/`, `main.py` | settings, ORM tables, client factories, app assembly | domain rules |

| Before (`v2.1`) | After (`v3.0`) |
|---|---|
| ORM models and pydantic schemas mixed in `backend/models/` | ORM in `infrastructure/orm.py`, pydantic in `adapters/api/schemas/`, entities in `domain/entities.py` |
| `services/post_service.py` raised `fastapi.HTTPException` | `usecases/post_usecase.py` raises `PermissionDeniedError`; `error_handlers.py` maps it to 403 |
| ~500-line lab router, the same checks copied across 7 DBs × 4 endpoints | one `LabRecordUseCase`, seven gateways, one `_build_record_router()`. URLs and responses unchanged |
| routers called driver factories directly | routers receive a use case via `Depends(get_lab_usecase("mongo"))` |
| `@app.on_event("startup")` + module-level `atexit` | `lifespan` + `ResourceRegistry.close_all()` |

#### 2-2. Dependency direction (outside → inside)

| Layer | May import |
|---|---|
| `domain` | standard library only |
| `usecases` | `domain` |
| `adapters` | `domain`, `usecases`, `infrastructure` (driver types), `adapters` |
| `infrastructure` | `domain.exceptions` (to translate `ConfigurationError`), `infrastructure` |
| `main.py`, `adapters/api/deps.py` | everything (the only places allowed to know the whole graph) |

**Automated check:** `tests/test_architecture.py`

- `test_layer_imports_point_inward` — parses every `import` with `ast` and fails on a violation.
- `test_domain_has_no_framework_imports` — no fastapi, sqlalchemy, pydantic, pymongo, redis, boto3, or neo4j under `domain/`.
- `test_usecases_do_not_know_http` — no `fastapi` import and no `HTTPException` name in `usecases/` (comments excluded).

Ports are owned by the inner circle (`domain/ports.py`). Implementations live outside (`adapters/gateways/`). Use cases never import a gateway. Gateways receive driver clients as constructor arguments; only `deps.py` calls `clients.mongo_collection()` and friends.

#### 2-3. Use cases

Inputs are primitives or domain values. Outputs are domain entities. Collaborators are ports only.

```python
# backend/usecases/lab_record_usecase.py — one rule shared by 7 databases
class LabRecordUseCase:
    def __init__(self, repo: LabRecordRepository) -> None:
        self._repo = repo

    def update(self, record_id: str, patch: LabRecordPatch) -> LabRecord:
        if patch.is_empty():
            raise ValidationError("No fields to update.")
        updated = self._repo.update(record_id, patch)
        if updated is None:
            raise NotFoundError(f"{self.source} record not found: {record_id}")
        return updated
```

| Use case | Rules |
|---|---|
| `LabRecordUseCase` | limit range, reject empty PATCH, missing id → NotFound |
| `VectorUseCase` | reject empty vectors and out-of-range `top_k`. Does not know the provider |
| `GraphUseCase` | forbid self-loop edges |
| `EmployeeUseCase` | missing employee → NotFound |
| `PostUseCase` | only the author may update or delete; increment view count |
| `AuthUseCase` | login (message does not enumerate accounts), token → user, idempotent seed |

**Independence check:** `tests/test_usecases.py` exercises these rules with in-memory fakes only (no FastAPI, database, or network).

#### 2-4. Interface adapters

| Kind | File | Conversion |
|---|---|---|
| Gateway | `adapters/gateways/lab_*.py` | driver rows/documents → `LabRecord` |
| Gateway | `adapters/gateways/vector_stores.py` | Pinecone / Weaviate / Qdrant hits → `VectorMatch` |
| Gateway | `adapters/gateways/sql_repositories.py` | ORM rows → `User` / `Post` |
| Gateway | `adapters/security/*.py` | passlib / python-jose → hasher / token ports |
| Controller | `adapters/api/*_router.py` | HTTP → `schema.to_entity()` / `to_patch()` → use case |
| Presenter | `adapters/api/presenters.py` | entity → response schema |
| Error translator | `adapters/api/error_handlers.py` | `DomainError` subclass → 400 / 401 / 403 / 404 / 502 |
| Composition root | `adapters/api/deps.py` | `LAB_REPOSITORY_FACTORIES` and `VECTOR_STORE_FACTORIES` |

Controller bodies stay at two or three lines:

```python
@sub.patch("/{record_id}", response_model=LabRecordRead)
def update_record(record_id: str, payload: LabRecordUpdate, uc: LabRecordUseCase = Depends(provider)):
    return presenters.lab_record(uc.update(record_id, payload.to_patch()), source=uc.source)
```

**Adding a database (open/closed):** (1) implement `LabRecordRepository` in `gateways/lab_xxx.py`, (2) add a client factory in `infrastructure/clients.py`, (3) add one line to the strategy table in `deps.py`. Do not edit the use case, router, or schemas.

---

### Tests and static checks

```bash
pip install -r requirements-dev.txt
pytest tests          # use-case, domain, and architecture tests — no database required
mypy backend          # static type check
```

### Technical notes (`docs/techNNN.md`)

Topic notes for the Python techniques used in this repo. They live under `docs/`, not the repository root, and each note cites the real call sites. The UI loads them through `/api/docs/tech`.

| File | Topic |
|---|---|
| [tech001.md](docs/tech001.md) | `__init__.py` and packages |
| [tech002.md](docs/tech002.md) | `from __future__ import annotations` and forward references |
| [tech003.md](docs/tech003.md) | dataclasses — `frozen`, `slots`, `field`, `replace` |
| [tech004.md](docs/tech004.md) | ABC and Protocol |
| [tech005.md](docs/tech005.md) | type hints — `Literal`, `Final`, `ClassVar`, `Annotated`, `cast`, mypy |
| [tech006.md](docs/tech006.md) | exceptions — `try/except/else/finally`, custom hierarchy, chaining |
| [tech007.md](docs/tech007.md) | `json` — `dumps` / `loads`, `ensure_ascii`, `JSONDecodeError` |
| [tech008.md](docs/tech008.md) | `functools` — `lru_cache` singletons, `cached_property` |
| [tech009.md](docs/tech009.md) | context managers — `with`, `contextmanager`, lifespan |
| [tech010.md](docs/tech010.md) | closures, higher-order functions, strategy tables |
| [tech011.md](docs/tech011.md) | generators and iterators — `yield`, `scan_iter`, `itertools` |
| [tech012.md](docs/tech012.md) | `@classmethod`, `@staticmethod`, `@property`, naming |
| [tech013.md](docs/tech013.md) | arguments — keyword-only `*`, unpacking, `zip` |
| [tech014.md](docs/tech014.md) | `logging` — module loggers, levels, `logger.exception` |
| [tech015.md](docs/tech015.md) | `ast` — architecture tests that check import direction |
| [tech016.md](docs/tech016.md) | pydantic and pydantic-settings |
| [tech017.md](docs/tech017.md) | pytest — `raises`, `parametrize`, fixtures, test doubles |
| [tech018.md](docs/tech018.md) | string formatting — f-string escapes, parameter binding, encoding |

---

## Dependencies in detail

### 1. PostgreSQL · SQLAlchemy · psycopg

**Role:** persistent users and posts (main DB), plus the lab_records table.

#### SQLAlchemy 2.0 — ORM and Core side by side

```python
# ORM (users / posts) — backend/infrastructure/orm.py
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
```

```python
# Core (lab_records) — table: backend/infrastructure/clients.py
lab_records_table = Table(
    settings.postgresql_table_name, lab_metadata,
    Column("id", String, primary_key=True),
    Column("tags", JSON, nullable=False),
    ...
)
# usage: backend/adapters/gateways/lab_postgres.py
with self._engine.begin() as conn:                      # commit on success, rollback on error
    conn.execute(insert(self._table).values(**record.to_dict()))
```

ORM is used for the relational User ↔ Post model. Core is used for the simple, dynamic lab table.

#### psycopg 3 (binary)

```
psycopg[binary]==3.2.3
```

`psycopg[binary]` ships a precompiled C extension and is faster than the pure-Python build.
SQLAlchemy DSN prefix: `postgresql+psycopg://`

#### Session management via dependency injection

```python
# backend/infrastructure/orm.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# backend/adapters/api/deps.py — wrap the session as gateway → use case
def get_post_usecase(db: Annotated[Session, Depends(get_db)]) -> PostUseCase:
    return PostUseCase(SqlPostRepository(db))

# backend/adapters/api/post_router.py — the router never sees Session
@router.get("", response_model=PostListResponse)
def list_posts(_: CurrentUser, posts: PostUC, ...) -> PostListResponse:
    return presenters.post_page(posts.list_posts(q, page, size, sort))
```

A session is opened per request and always closed, so connections do not leak.

---

### 2. JWT · passlib · python-jose

**Role:** password hashing and stateless JWT authentication.

#### Password hashing — passlib + bcrypt

```python
# backend/adapters/security/bcrypt_hasher.py — PasswordHasher port
class BcryptPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, raw_password: str) -> str:
        return self._ctx.hash(raw_password)                  # salt generated and stored in the hash

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return self._ctx.verify(raw_password, password_hash) # timing-safe compare
```

bcrypt's work factor slows brute-force attempts.

#### Issuing and verifying JWTs — python-jose

```python
class JwtTokenProvider(TokenProvider):
    def issue(self, subject: str) -> str:
        claims = {"sub": subject, "exp": datetime.now(timezone.utc) + self._expire}
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)        # HS256

    def subject_of(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:            # expiry, bad signature, and malformed tokens
            logger.debug("jwt decode failed: %s", exc)
            return None
        subject = payload.get("sub")
        return subject if isinstance(subject, str) else None
```

`OAuth2PasswordBearer` reads the `Authorization` header. `deps.get_current_user` calls `AuthUseCase.authenticate(token)` and injects a domain `User`. An invalid token becomes `AuthenticationError`, which `error_handlers.py` translates to 401 plus `WWW-Authenticate: Bearer`.

---

### 3. DynamoDB · boto3

**Role:** store and load Employee entities in AWS DynamoDB.

```python
@lru_cache
def dynamodb_table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.dynamodb_table_name)

def get_employee_usecase() -> EmployeeUseCase:
    return EmployeeUseCase(DynamoDbEmployeeRepository(clients.dynamodb_table()))
```

boto3 reads `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` or an IAM role. For local work, use [LocalStack](https://localstack.cloud/) or [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html).

| Item | Detail |
|---|---|
| Primary key | composite: partition key `id` + sort key `name` |
| Access | `get_item` (one), `scan` (all) |
| Schema | schemaless — extra attributes are allowed |
| Transactions | not used (plain put/delete) |

```python
def find(self, employee_id: str, name: str) -> Employee | None:
    try:
        item = self._table.get_item(Key={"id": employee_id, "name": name}).get("Item")
    except (ClientError, BotoCoreError) as exc:
        raise ExternalServiceError("DynamoDB read failed", service="dynamodb") from exc
    return Employee.from_dict(item) if item else None

def list_all(self) -> list[Employee]:
    items = self._table.scan().get("Items", [])  # full scan — paginate in production
    return [Employee.from_dict(item) for item in items]
```

> **Note:** `scan()` reads the whole table. Production code should use `query()` plus a GSI.

```
APP_AWS_REGION=ap-northeast-2
APP_DYNAMODB_TABLE_NAME=Employees
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

---

### 4. MongoDB · pymongo

**Role:** CRUD for lab documents (`LabRecord`).

```python
@lru_cache
def mongo_client() -> MongoClient:
    client: MongoClient = MongoClient(settings.mongodb_uri)
    registry.register("mongo", client.close)        # closed by ResourceRegistry on lifespan shutdown
    return client

class MongoLabRecordRepository(LabRecordRepository):
    source: ClassVar[str] = "mongodb"
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
```

`lru_cache` keeps one `MongoClient` for the process lifetime. `registry.close_all()` drains the pool when the lifespan ends.

```python
collection.insert_one(payload.model_dump())
collection.find_one_and_update({"id": record_id}, {"$set": changes}, return_document=ReturnDocument.AFTER)
collection.find({}, {"_id": 0}).limit(limit)
```

`_id` (ObjectId) is omitted from responses. `$set` updates only the given fields, which matches PATCH semantics.

```
APP_MONGODB_URI=mongodb://localhost:27017
APP_MONGODB_DB_NAME=lab_db
APP_MONGODB_COLLECTION_NAME=documents
```

---

### 5. Supabase · supabase-py

**Role:** CRUD on a Supabase `lab_records` table (PostgreSQL BaaS).

```python
@lru_cache
def _supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(400, "Supabase settings are required.")
    return create_client(settings.supabase_url, settings.supabase_key)
```

`supabase_url` is `https://<project-id>.supabase.co`. `supabase_key` is an `anon` or `service_role` key.

```python
client.table("lab_records").insert(data).execute()
response = client.table("lab_records").select("*").limit(limit).execute()
client.table("lab_records").update(changes).eq("id", record_id).execute()
client.table("lab_records").delete().eq("id", record_id).execute()
```

supabase-py wraps PostgREST, so traffic is HTTP(S). If Row Level Security is on, use a `service_role` key or a matching policy.

```sql
CREATE TABLE lab_records (
  id      TEXT PRIMARY KEY,
  title   TEXT NOT NULL,
  content TEXT NOT NULL,
  tags    JSONB NOT NULL DEFAULT '[]'
);
```

```
APP_SUPABASE_URL=https://<project-id>.supabase.co
APP_SUPABASE_KEY=<anon-or-service-role-key>
APP_SUPABASE_TABLE_NAME=lab_records
```

---

### 6. Pinecone (vector DB)

**Role:** upsert embeddings and run similarity search on a cloud index.

```python
@lru_cache
def _pinecone_index():
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)

index.upsert(vectors=[{
    "id":       payload.id,
    "values":   payload.values,    # list[float] — dimension is fixed when the index is created
    "metadata": payload.metadata,
}])

result = index.query(vector=payload.values, top_k=payload.top_k, include_metadata=True)
matches = result.to_dict().get("matches", [])
```

The default metric is **cosine similarity**. Set `metric="dotproduct"` or `"euclidean"` when creating the index.

```python
pc.create_index(
    name="lab-vectors",
    dimension=1536,          # e.g. OpenAI text-embedding-3-small
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
```

```
APP_VECTOR_PROVIDER=pinecone
APP_PINECONE_API_KEY=<your-api-key>
APP_PINECONE_INDEX_NAME=lab-vectors
```

---

### 7. Weaviate (vector DB)

**Role:** store objects and run similarity search on a local or self-hosted collection.

```python
@lru_cache
def _weaviate_client():
    return weaviate.connect_to_local()   # default: localhost:8080

object_uuid = str(uuid.uuid5(NAMESPACE, payload.id))   # deterministic UUID
collection.data.insert(
    uuid=object_uuid,
    properties={"external_id": payload.id, "metadata": payload.metadata},
    vector=payload.values,
)

result = collection.query.near_vector(
    near_vector=payload.values,
    limit=payload.top_k,
    return_metadata=MetadataQuery(distance=True),
)
```

`uuid5` avoids collisions when the same `id` is inserted again. `distance` closer to 0 means more similar (cosine distance).

```bash
docker run -d \
  -p 8080:8080 -p 50051:50051 \
  -e ENABLE_MODULES='' \
  cr.weaviate.io/semitechnologies/weaviate:1.25.0
```

```python
client.collections.create(
    name="LabVectors",
    vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
)
```

```
APP_VECTOR_PROVIDER=weaviate
APP_WEAVIATE_URL=http://localhost:8080
APP_WEAVIATE_COLLECTION_NAME=LabVectors
```

> Choose `pinecone`, `weaviate`, or `qdrant` with `APP_VECTOR_PROVIDER`. Selection is the `VECTOR_STORE_FACTORIES` strategy table in `adapters/api/deps.py`. The router and `VectorUseCase` do not know the provider.

---

### 8. Neo4j · GDS (graph DB)

**Role:** store Entity nodes and edges, then analyze them with Graph Data Science.

```python
@lru_cache
def _neo4j_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,                              # bolt://localhost:7687
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
```

`MERGE` matches an existing node or creates it (upsert). Edges use the same pattern for `RELATES_TO`. GDS needs the Graph Data Science plugin. Drop any existing projection with `gds.graph.drop` before projecting again.

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26
```

```
APP_NEO4J_URI=bolt://localhost:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=password
APP_NEO4J_DATABASE=neo4j
APP_NEO4J_GRAPH_NAME=lab_graph
```

PageRank and degree centrality are exposed as `POST /lab/graph/analyze` with `pagerank` or `degree`.

---

### 9. Redis (key-value)

**Role:** store lab_records-shaped documents (`id` / `title` / `content` / `tags`) as JSON strings. The most common OSS in-memory store for cache and session use.

```python
@lru_cache
def redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)

def add(self, record: LabRecord) -> LabRecord:
    self._client.set(self._key(record.id), json.dumps(record.to_dict(), ensure_ascii=False))
    return record
```

Listing uses `SCAN MATCH "lab_record:*"` then `MGET`. `KEYS` is avoided because it blocks the server.

```bash
docker run -d -p 6379:6379 redis:7
```

```
APP_REDIS_URL=redis://localhost:6379/0
APP_REDIS_KEY_PREFIX=lab_record:
```

---

### 10. OpenSearch (search / analytics)

**Role:** index lab_records for search. The widely adopted OSS fork after the Elasticsearch license change.

```python
@lru_cache
def _opensearch_client():
    return OpenSearch(hosts=[settings.opensearch_url])

client.index(index=settings.opensearch_index_name, id=data["id"], body=data, refresh=True)
```

Reads use a `match_all` query. Updates use the `update` API `doc` partial update.

```bash
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  opensearchproject/opensearch:2.15.0
```

```
APP_OPENSEARCH_URL=http://localhost:9200
APP_OPENSEARCH_INDEX_NAME=lab_records
```

---

### 11. ClickHouse (OLAP)

**Role:** store lab_records in a columnar table. A fast-growing OSS analytics database.

```python
client = clickhouse_connect.get_client(
    host=settings.clickhouse_host, port=settings.clickhouse_port,
    username=settings.clickhouse_user, password=settings.clickhouse_password,
)
client.command("""
    CREATE TABLE IF NOT EXISTS lab_records
    (id String, title String, content String, tags Array(String))
    ENGINE = MergeTree ORDER BY id
""")
```

Row-level UPDATE/DELETE are asynchronous mutations. The gateway runs `ALTER TABLE ... UPDATE/DELETE ... WHERE id = ...` with `settings={"mutations_sync": 1}` so CRUD responses return immediately.

```bash
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:24
```

```
APP_CLICKHOUSE_HOST=localhost
APP_CLICKHOUSE_PORT=8123
APP_CLICKHOUSE_USER=default
APP_CLICKHOUSE_PASSWORD=
APP_CLICKHOUSE_DATABASE=default
APP_CLICKHOUSE_TABLE_NAME=lab_records
```

---

### 12. Cassandra (wide-column)

**Role:** store lab_records in a CQL table. A fully open-source alternative in the same wide-column category as DynamoDB.

```python
cluster = Cluster(settings.cassandra_hosts.split(","), port=settings.cassandra_port)
session = cluster.connect()
session.execute("""
    CREATE KEYSPACE IF NOT EXISTS lab_keyspace
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")
session.execute("""
    CREATE TABLE IF NOT EXISTS lab_records
    (id text PRIMARY KEY, title text, content text, tags list<text>)
""")
```

CQL `INSERT` / `SELECT` / `UPDATE` / `DELETE` map directly onto CRUD.

```bash
docker run -d -p 9042:9042 cassandra:5
```

```
APP_CASSANDRA_HOSTS=127.0.0.1
APP_CASSANDRA_PORT=9042
APP_CASSANDRA_KEYSPACE=lab_keyspace
APP_CASSANDRA_TABLE_NAME=lab_records
```

---

### 13. Qdrant (vector DB)

**Role:** upsert embeddings and run similarity search on a local or self-hosted collection. The third `APP_VECTOR_PROVIDER` option, sharing `/lab/vector/*` with Pinecone and Weaviate.

```python
@lru_cache
def _qdrant_client():
    return QdrantClient(url=settings.qdrant_url)

point_uuid = str(uuid.uuid5(QDRANT_UUID_NAMESPACE, payload.id))
client.upsert(collection_name=settings.qdrant_collection_name, points=[
    PointStruct(id=point_uuid, vector=payload.values, payload={"external_id": payload.id, **payload.metadata}),
])
result = client.query_points(collection_name=settings.qdrant_collection_name, query=payload.values, limit=payload.top_k)
```

```bash
docker run -d -p 6333:6333 qdrant/qdrant:v1.12.1
```

```
APP_VECTOR_PROVIDER=qdrant
APP_QDRANT_URL=http://localhost:6333
APP_QDRANT_COLLECTION_NAME=lab-vectors
```

---

## Environment variables

Every application setting uses the `APP_` prefix. Copy the example file:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `APP_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `APP_ALGORITHM` | `HS256` | JWT algorithm |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | token lifetime |
| `APP_ALLOWED_ORIGINS` | `http://127.0.0.1:8001,...` | CORS origins |
| `APP_DATABASE_URL` | `postgresql+psycopg://...` | main PostgreSQL |
| `APP_POSTGRESQL_DSN` | `postgresql+psycopg://...` | lab PostgreSQL |
| `APP_POSTGRESQL_TABLE_NAME` | `lab_records` | lab table name |
| `APP_AWS_REGION` | `ap-northeast-2` | DynamoDB region |
| `APP_DYNAMODB_TABLE_NAME` | `Employees` | DynamoDB table |
| `APP_MONGODB_URI` | `mongodb://localhost:27017` | MongoDB URI |
| `APP_MONGODB_DB_NAME` | `lab_db` | MongoDB database |
| `APP_MONGODB_COLLECTION_NAME` | `documents` | MongoDB collection |
| `APP_SUPABASE_URL` | _(required)_ | Supabase project URL |
| `APP_SUPABASE_KEY` | _(required)_ | Supabase API key |
| `APP_SUPABASE_TABLE_NAME` | `lab_records` | Supabase table |
| `APP_VECTOR_PROVIDER` | `pinecone` | `pinecone`, `weaviate`, or `qdrant` |
| `APP_PINECONE_API_KEY` | _(required for Pinecone)_ | Pinecone API key |
| `APP_PINECONE_INDEX_NAME` | `lab-vectors` | Pinecone index |
| `APP_WEAVIATE_URL` | `http://localhost:8080` | Weaviate URL |
| `APP_WEAVIATE_COLLECTION_NAME` | `LabVectors` | Weaviate collection |
| `APP_NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `APP_NEO4J_USER` | `neo4j` | Neo4j user |
| `APP_NEO4J_PASSWORD` | `password` | Neo4j password |
| `APP_NEO4J_DATABASE` | `neo4j` | Neo4j database |
| `APP_NEO4J_GRAPH_NAME` | `lab_graph` | GDS projection name |
| `APP_REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `APP_REDIS_KEY_PREFIX` | `lab_record:` | Redis key prefix |
| `APP_OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch URL |
| `APP_OPENSEARCH_INDEX_NAME` | `lab_records` | OpenSearch index |
| `APP_CLICKHOUSE_HOST` | `localhost` | ClickHouse host |
| `APP_CLICKHOUSE_PORT` | `8123` | ClickHouse HTTP port |
| `APP_CLICKHOUSE_USER` | `default` | ClickHouse user |
| `APP_CLICKHOUSE_PASSWORD` | _(empty)_ | ClickHouse password |
| `APP_CLICKHOUSE_DATABASE` | `default` | ClickHouse database |
| `APP_CLICKHOUSE_TABLE_NAME` | `lab_records` | ClickHouse table |
| `APP_CASSANDRA_HOSTS` | `127.0.0.1` | Cassandra hosts (comma-separated) |
| `APP_CASSANDRA_PORT` | `9042` | Cassandra port |
| `APP_CASSANDRA_KEYSPACE` | `lab_keyspace` | Cassandra keyspace |
| `APP_CASSANDRA_TABLE_NAME` | `lab_records` | Cassandra table |
| `APP_QDRANT_URL` | `http://localhost:6333` | Qdrant URL |
| `APP_QDRANT_COLLECTION_NAME` | `lab-vectors` | Qdrant collection |

---

## Project layout

```
multi-db-lab/
├── backend/
│   ├── main.py                  # composition root (lifespan, CORS, routers, error handlers, seed, frontend mount)
│   ├── domain/                  # 1 Entities
│   ├── usecases/                # 2 Use Cases
│   ├── adapters/                # 3 Interface Adapters (gateways, security, api)
│   └── infrastructure/          # 4 Frameworks & Drivers (settings, orm, clients)
├── tests/                       # fakes, domain, use cases, architecture, docs router
├── frontend/                    # index.html, app.js, engine.js, docs.js, usecases.js
├── docs/                        # tech001.md–tech018.md
├── main.py                      # legacy compatibility entrypoint
├── mypy.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── readme.md                    # this file (English)
├── readme-kr.md                 # Korean guide
├── llms.txt                     # LLM documentation index
└── .env.example
```

---

## How to run

The frontend (`frontend/`) is served by FastAPI as static files (`StaticFiles` in `backend/main.py`). No separate frontend server is required.

### 1) PostgreSQL + API + frontend (Docker Compose, recommended)

```bash
docker compose up --build
```

- App (frontend + API): http://127.0.0.1:8010
- Swagger: http://127.0.0.1:8010/docs

`docker-compose.yml` expects an external Docker network named `shared-net`. Create it once with `docker network create shared-net` if it does not exist.

### 2) Run locally (no Docker)

```bash
uvicorn backend.main:app --reload
```

- App: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### 3) Optional external services

Set the matching variables in `.env` and start only the services you need.

```bash
docker run -d -p 27017:27017 mongo:7
docker run -d -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/weaviate:1.25.0
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26
docker run -d -p 6379:6379 redis:7
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" -e "DISABLE_SECURITY_PLUGIN=true" \
  opensearchproject/opensearch:2.15.0
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:24
docker run -d -p 9042:9042 cassandra:5
docker run -d -p 6333:6333 qdrant/qdrant:v1.12.1
```

Issue credentials for Supabase, Pinecone, and DynamoDB in each cloud console and put them in `.env`.

### Default account

- username: `admin`
- password: `admin1234`

---

## API summary

### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/login` | log in and issue a JWT |
| `GET` | `/api/auth/me` | current user |

### Posts (PostgreSQL ORM)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/posts` | list (`q`, `page`/`size`, `sort`) |
| `GET` | `/api/posts/{id}` | detail (`inc_view=true` increments views) |
| `POST` | `/api/posts` | create |
| `PUT` | `/api/posts/{id}` | update (author only) |
| `DELETE` | `/api/posts/{id}` | delete (author only) |

### Employees (DynamoDB)

| Method | Path | Description |
|---|---|---|
| `POST` | `/employees` | create (`put_item`) |
| `GET` | `/employees` | list (`scan`) |
| `GET` | `/employees/{id}/{name}` | get one |
| `DELETE` | `/employees/{id}/{name}` | delete |

### Lab records

The same four routes exist for each record-shaped store. Replace `{db}` with `mongo`, `postgres`, `supabase`, `redis`, `opensearch`, `clickhouse`, or `cassandra`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/lab/{db}/records` | create |
| `GET` | `/lab/{db}/records` | list |
| `PATCH` | `/lab/{db}/records/{id}` | partial update |
| `DELETE` | `/lab/{db}/records/{id}` | delete |

### Lab — vector DB (Pinecone / Weaviate / Qdrant)

| Method | Path | Description |
|---|---|---|
| `POST` | `/lab/vector/upsert` | store a vector (`APP_VECTOR_PROVIDER`) |
| `POST` | `/lab/vector/query` | similarity search |

### Lab — Neo4j graph

| Method | Path | Description |
|---|---|---|
| `POST` | `/lab/graph/nodes` | create an Entity node (`MERGE`) |
| `POST` | `/lab/graph/edges` | create a `RELATES_TO` edge |
| `POST` | `/lab/graph/analyze` | GDS analysis (`pagerank` or `degree`) |

### Technical notes

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/docs/tech` | list `docs/techNNN.md` |
| `GET` | `/api/docs/tech/{id}` | markdown body (`tech001` … `tech018`) |

Full interactive docs: http://127.0.0.1:8000/docs (Swagger UI).

---

## Multi-DB engine (canvas)

After login, the **Multi-DB Engine** tab connects several databases at once and merges their rows into one AG Grid.

- **Palette:** PostgreSQL, MongoDB, Supabase, Redis, OpenSearch, ClickHouse, Cassandra, DynamoDB, Pinecone, Weaviate, Neo4j, and Qdrant (12 icons).
- **Compatible** (solid border): PostgreSQL, MongoDB, Supabase, Redis, OpenSearch, ClickHouse, Cassandra. They share the `id` / `title` / `content` / `tags` shape (`/lab/<db>/records`), so connecting them to the Grid node fetches rows and merges them.
- **Incompatible** (dashed border): DynamoDB (Employee), Pinecone / Weaviate / Qdrant (vector), Neo4j (graph). They appear on the palette, but connecting them to the Grid node only shows that the record shape does not match.
- **How to use:** click a palette icon to add a node, drag its handle to the Grid node, and the app loads that database's records (seeding three samples if empty) with a `source` column. Several connections accumulate in one grid. Deleting a node or edge removes only that source. Node positions and connections are stored in `localStorage` and survive a refresh.
