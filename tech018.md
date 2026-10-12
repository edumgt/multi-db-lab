파이썬 **문자열 포매팅** 은 f-string(3.6+) 이 표준이지만, 로깅의 `%s` 스타일과 DB 드라이버의 **파라미터 바인딩 플레이스홀더** 를 구분해 쓰는 것이 중요합니다. 이 프로젝트의 ClickHouse · Cassandra · Redis 게이트웨이에서 세 가지가 함께 등장합니다.

---

### 1. f-string 기본

```python
f"{self._prefix}{record_id}"                       # 연결
f"{len(raw)} bytes"                                # 표현식
f"{score:.3f}"  f"{count:>5}"  f"{ratio:.1%}"      # 포맷 스펙
f"{value!r}"                                       # repr
f"{key=}"                                          # 디버깅: key='abc' (3.8+)
```

### 2. 중괄호 이스케이프 — `{{` `}}`

```python
# backend/adapters/gateways/lab_clickhouse.py
f"SELECT ... FROM {self._table} WHERE id = {{id:String}}"
#                  ^ 파이썬이 치환        ^ 결과 문자열에 '{id:String}' 그대로 남음 → ClickHouse 가 바인딩
```

* f-string 안에서 **리터럴 중괄호** 가 필요하면 두 번 씁니다.
* ClickHouse 의 `{name:Type}` 플레이스홀더와 f-string 문법이 겹치는 대표적인 예입니다.

```python
# 더 복잡한 예 — 키 이름을 플레이스홀더 이름으로도 사용
f"{key} = {{{key}:Array(String)}}"      # key="tags" → "tags = {tags:Array(String)}"
```

### 3. SQL/CQL 에 값을 넣는 **올바른** 방법 — 파라미터 바인딩

```python
# Cassandra — %s 는 str % 연산이 아니라 드라이버의 플레이스홀더
session.execute(f"INSERT INTO {self._table} (id, title, content, tags) VALUES (%s, %s, %s, %s)",
                (record.id, record.title, record.content, record.tags))

# ClickHouse — {name:Type}
client.query("SELECT ... WHERE id = {id:String}", parameters={"id": record_id})

# Neo4j — $name
session.run("MERGE (n:Entity {id: $id}) SET n.label = $label", id=node.id, label=node.label)

# SQLAlchemy Core — 표현식 API 가 자동 바인딩
select(table).where(table.c.id == record_id)
```

* **값** 은 절대 f-string 으로 끼워 넣지 않습니다(SQL 인젝션). 드라이버가 이스케이프와 타입 변환을 담당합니다.
* **식별자**(테이블명 · 컬럼명) 는 바인딩이 안 되므로 f-string 을 쓰되, **설정값이나 화이트리스트** 에서만 가져옵니다.
  ```python
  COLUMNS: Final = ("id", "title", "content", "tags")
  set_clause = ", ".join(f"{key} = %s" for key in changes if key in COLUMNS)
  ```

### 4. 로깅은 `%s` 지연 포매팅

```python
logger.debug("redis load key=%s bytes=%d", key, len(raw))       # 레벨이 꺼져 있으면 포매팅 안 함
```

* tech014 참고. f-string 을 로깅에 쓰면 성능과 구조화 로깅 양쪽에서 손해입니다.

### 5. `str.join` — 리스트를 문자열로

```python
", ".join(COLUMNS)                                   # "id, title, content, tags"
", ".join(f"{key} = %s" for key in changes)          # 제너레이터 표현식 바로 전달
```

* 루프 안에서 `s += ...` 로 이어 붙이는 것보다 빠르고 읽기 좋습니다.

### 6. 여러 줄 문자열과 `textwrap.dedent`

```python
session.execute(
    f"""
    CREATE TABLE IF NOT EXISTS {settings.cassandra_table_name} (
        id text PRIMARY KEY,
        ...
    )
    """
)
```

* 삼중 따옴표 안의 들여쓰기는 문자열에 포함됩니다. SQL 은 공백에 무관해 그대로 두었지만, 사람에게 보여줄 텍스트는 `textwrap.dedent()` 로 정리합니다.

### 7. 바이트와 문자열 — 인코딩 명시

```python
Path(...).read_text(encoding="utf-8")
json.dumps(obj, ensure_ascii=False)          # 한글 원문 유지
redis.from_url(url, decode_responses=True)   # bytes → str 자동 디코딩
```

* 파일 · 네트워크 경계에서는 **항상 `encoding="utf-8"`** 을 명시합니다. 플랫폼 기본값(Windows cp949) 에 의존하면 한글이 깨집니다.

### 8. 자주 쓰는 문자열 메서드

| 메서드 | 예 |
|---|---|
| `strip()` | `o.strip() for o in origins.split(",")` — 설정값 공백 제거 |
| `split(",")` | 쉼표 구분 환경변수 → 리스트 |
| `lower()` | `settings.vector_provider.lower()` — 대소문자 정규화 |
| `startswith(prefix)` | `token.startswith("token-for-")` |
| `removeprefix` / `removesuffix` (3.9+) | `name.removeprefix("backend.")` — 슬라이싱보다 안전 |

---

문자열을 다룰 때 가장 먼저 물어야 할 질문은 **"이 문자열이 코드로 해석되는가?"** 입니다. SQL · CQL · Cypher 로 해석되는 문자열에는 값을 f-string 으로 넣지 말고 드라이버의 바인딩을 쓰세요. 이 프로젝트의 모든 게이트웨이가 그 규칙을 따르며, 식별자는 설정값 · `Final` 화이트리스트에서만 옵니다.
