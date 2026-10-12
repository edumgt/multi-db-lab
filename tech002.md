> **쉽게 이해하기**
>
> - **한 줄 요약** — 타입 힌트를 '지금 계산' 하지 않고 '글자로 보관' 하게 하는 스위치입니다.
> - **비유하면** — 아직 짓지 않은 건물의 주소를 메모해 두는 것. 실제로 필요할 때만 찾아갑니다.
> - **이 프로젝트에서는** — 자기 자신을 반환하는 메서드(`-> Post`) 나 서로 import 하는 타입을 따옴표 없이 쓸 수 있습니다.
> - **기억할 것** — FastAPI 가 함수 안에서 만든 `Annotated` 별칭을 못 읽는 경우가 있습니다(`lab_router.py` 주석 참고).

파이썬에서 `from __future__ import annotations`는 **타입 애너테이션을 즉시 평가하지 않고 문자열로 보관**하도록 바꾸는 선언입니다. 이 프로젝트의 거의 모든 모듈 첫 줄에 들어 있습니다.

---

### 1. 무엇이 달라지는가

* 기본 동작: 함수/클래스 정의 시점에 애너테이션의 표현식이 **실제로 실행**됩니다. 아직 정의되지 않은 이름을 쓰면 `NameError`가 납니다.
* 선언 후: 애너테이션은 문자열로만 저장되고(`__annotations__`에 `'User'` 처럼), 필요할 때 `typing.get_type_hints()`로 평가합니다.

> **예시 코드 — 전방 참조(Forward Reference)**
> ```python
> # backend/infrastructure/orm.py
> from __future__ import annotations
>
> class UserRow(Base):
>     posts: Mapped[list[PostRow]] = relationship(...)   # PostRow 는 아래에서 정의됨
>
> class PostRow(Base):
>     owner: Mapped[UserRow] = relationship(...)
> ```
> 선언이 없으면 `UserRow` 정의 중 `PostRow`가 존재하지 않아 오류가 납니다.

### 2. 클래스 자신을 반환하는 메서드

* `@classmethod def from_dict(cls, raw) -> LabRecord:` 처럼 **클래스 몸체 안에서 그 클래스 이름을 반환 타입**으로 쓸 수 있습니다.
* 선언이 없다면 `-> "LabRecord"` 로 따옴표를 쳐야 합니다. (`backend/domain/entities.py`)

### 3. 성능상의 이점

* 애너테이션 평가가 사라지므로 import 시간이 약간 줄어듭니다. 복잡한 제네릭(`dict[str, Callable[[], LabRecordRepository]]`)이 많을수록 차이가 커집니다.

### 4. 주의할 점 — 런타임에 애너테이션을 읽는 라이브러리

* FastAPI · pydantic 은 애너테이션을 **런타임에 평가**해 의존성 주입과 검증을 수행합니다. 평가는 "그 함수가 정의된 모듈의 전역 네임스페이스" 기준으로 이뤄집니다.
* 따라서 **함수 안에서 만든 지역 별칭**은 해석되지 않습니다. 이 프로젝트에서 실제로 겪은 버그입니다.

> ```python
> # backend/adapters/api/lab_router.py — 실패한 시도
> def _build_record_router(source: str) -> APIRouter:
>     UseCase = Annotated[LabRecordUseCase, Depends(get_lab_usecase(source))]   # 지역 변수
>
>     @sub.post("")
>     def create_record(payload: LabRecordCreate, uc: UseCase): ...   # 문자열 'UseCase' → 전역에서 못 찾음
>                                                                      # → FastAPI 가 쿼리 파라미터로 오인 (422)
> ```
> **해결:** 모듈 전역 타입만 애너테이션에 쓰고, 주입은 기본값 방식으로 표현했습니다.
> ```python
>     provider = get_lab_usecase(source)
>     def create_record(payload: LabRecordCreate, uc: LabRecordUseCase = Depends(provider)): ...
> ```

### 5. 파이썬 3.14 이후

* PEP 649/749 로 "지연 평가 애너테이션"이 기본이 됩니다. 그때까지는 이 선언을 모든 모듈 첫 줄에 두는 것이 안전한 관례입니다.

---

이 프로젝트에서는 `domain/entities.py`의 상호 참조, `ports.py`의 엔티티 참조, ORM 의 양방향 relationship 이 모두 이 선언 덕분에 따옴표 없이 깔끔하게 작성되었습니다. 단, 라우터처럼 **런타임이 애너테이션을 읽는 곳**에서는 지역 별칭을 피해야 한다는 점을 기억하세요.
