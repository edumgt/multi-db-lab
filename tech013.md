> **쉽게 이해하기**
>
> - **한 줄 요약** — 위치 · 키워드 · 가변(`*args`, `**kwargs`) · 키워드 전용(`*`) · 위치 전용(`/`) 을 구분하면 호출 실수가 줄어듭니다.
> - **비유하면** — 주문서 칸. '수량 2, 옵션 매운맛' 처럼 이름을 적게 하면(키워드 전용) 순서를 헷갈릴 일이 없습니다.
> - **이 프로젝트에서는** — `ports.py` 의 `list(limit, *, offset=0)` 처럼 뒤쪽 옵션은 키워드 전용입니다. `**record.to_dict()` 로 dict 를 펼쳐서 넘깁니다.
> - **기억할 것** — 가변 기본값(`def f(x=[])`) 은 쓰지 않습니다.

파이썬 함수의 **인자 전달 방식** — 위치 인자, 키워드 인자, `*args` / `**kwargs`, 키워드 전용(`*`) · 위치 전용(`/`) 구분, 언패킹 — 은 API 의 안전성과 가독성을 결정합니다. 이 프로젝트의 포트 시그니처와 게이트웨이 구현에서 어떻게 쓰였는지 봅니다.

---

### 1. 키워드 전용 인자 — `*` 뒤

```python
# backend/domain/ports.py
@abstractmethod
def update(self, post_id: int, *, title: str | None, content: str | None) -> Post: ...

# 호출
repo.update(post_id, title=payload.title, content=payload.content)     # OK
repo.update(post_id, "제목", "본문")                                    # TypeError
```

* `title` 과 `content` 는 모두 `str | None` 이라 **순서를 바꿔도 타입 검사가 통과** 합니다. 키워드 전용으로 강제해야 실수를 막을 수 있습니다.
* bool 플래그도 키워드 전용이 좋습니다: `get_post(post_id, *, inc_view=False)` → 호출부에 `inc_view=True` 가 드러납니다.

### 2. 위치 전용 인자 — `/` 앞 (3.8+)

```python
def hash(self, raw_password: str, /) -> str: ...
```

* 호출 시 `hash(raw_password="x")` 를 금지합니다. 인자 이름을 나중에 바꿔도 호출 코드가 깨지지 않습니다. 표준 라이브러리(`len(obj, /)`) 에 많습니다.

### 3. `**kwargs` 언패킹 — dict 를 키워드 인자로

```python
# backend/domain/entities.py
return replace(self, **patch.changes())        # {"title": "n"} → replace(self, title="n")

# backend/adapters/gateways/lab_postgres.py
conn.execute(insert(self._table).values(**record.to_dict()))
```

* dict 의 키가 함수의 매개변수 이름과 맞아야 합니다. `LabRecordPatch.changes()` 가 **엔티티 필드명과 같은 키** 만 돌려주도록 설계된 이유입니다.

### 4. `*args` 언패킹 — 시퀀스를 위치 인자로

```python
# backend/main.py
SEED_ADMIN = ("admin", "admin1234")
build_auth_usecase(db).ensure_user(*SEED_ADMIN)            # ensure_user("admin", "admin1234")

# backend/adapters/gateways/lab_cassandra.py
session.execute(f"UPDATE ... SET {set_clause} WHERE id = %s", (*changes.values(), record_id))
```

* 튜플 리터럴 안에서 `*` 로 펼치면 "앞에 여러 값 + 뒤에 하나" 를 깔끔하게 만듭니다.

### 5. dict 합치기 — `{**a, **b}`

```python
# backend/adapters/gateways/vector_stores.py
payload={"external_id": vector_id, **dict(metadata)}
# backend/adapters/gateways/lab_clickhouse.py
parameters={**changes, "id": record_id}
```

* 뒤에 오는 키가 앞의 키를 덮어씁니다. 3.9+ 에서는 `a | b` 도 가능합니다.

### 6. 가변 기본값 함정

```python
def add_tag(record, tags=[]):        # 금지: 모든 호출이 같은 리스트를 공유
    tags.append("x")

def add_tag(record, tags=None):      # 관용구
    tags = [] if tags is None else tags
```

* dataclass 는 이 실수를 `ValueError` 로 막습니다 → `field(default_factory=list)`(tech003).

### 7. 언패킹 할당

```python
name, closer = self._closers.pop()                 # 튜플 언패킹
first, *rest = result.result_rows                  # 확장 언패킹
for key, raw in zip(keys, values): ...             # 루프에서 동시 언패킹
```

### 8. `zip` 으로 컬럼명과 행 묶기

```python
# backend/adapters/gateways/lab_clickhouse.py
dict(zip(result.column_names, row))                # ("id","title",...) + ("1","t",...) → {"id": "1", ...}
```

* 길이가 다르면 짧은 쪽에서 멈춥니다. 3.10+ 의 `zip(a, b, strict=True)` 는 길이 불일치를 오류로 냅니다.

### 9. 인자 설계 가이드

| 상황 | 권장 |
|---|---|
| 같은 타입의 인자가 2 개 이상 | 키워드 전용 `*` |
| bool 플래그 | 키워드 전용 |
| 인자 이름이 바뀔 수 있는 저수준 함수 | 위치 전용 `/` |
| 선택 인자가 많음 | 값 객체(dataclass) 로 묶기 — `LabRecordPatch` |
| 가변 기본값 | `None` + 본문에서 생성, 또는 `default_factory` |

---

`PostRepository.update(post_id, *, title, content)` 처럼 **시그니처 자체가 잘못된 호출을 거부** 하도록 설계하면, 테스트가 아니라 인터프리터가 버그를 잡아 줍니다. 포트(추상 인터페이스) 를 정의할 때 가장 신경 써야 할 부분이 바로 이 인자 설계입니다.
