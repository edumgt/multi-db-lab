> **쉽게 이해하기**
>
> - **한 줄 요약** — 복잡한 검증 메서드 없이 평범한 `assert`만으로 테스트를 작성하는 파이썬 표준 테스트 도구입니다.
> - **비유하면** — 답안(코드)을 넣으면 어디가 어떻게 틀렸는지 빨간펜으로 친절하게 이유까지 짚어주는 스마트 자동 채점기.
> - **이 프로젝트에서는** — 무거운 13개 DB를 띄우지 않고 가짜 저장소(`tests/fakes.py`)로 핵심 비즈니스 로직을 2초 만에 초고속 검사합니다.
> - **기억할 것** — 파일 이름은 `test_*.py`, 함수 이름은 `test_*`로 지어야 pytest가 자동으로 찾아서 실행합니다.

**pytest**는 파이썬에서 가장 널리 쓰이는 표준 테스트 프레임워크입니다.

자바의 JUnit이나 파이썬 기본 `unittest`처럼 장황한 문법을 쓸 필요 없이, 파이썬 기본 문법인 `assert` 하나만으로 직관적이고 강력한 테스트를 작성할 수 있습니다.

---

### 1. 기본 규칙 — 파일과 함수 이름 짓기

pytest는 명령어를 실행하면 프로젝트 안을 샅샅이 뒤져 테스트 대상을 자동으로 찾아냅니다:
* **파일명**: `test_*.py` 또는 `*_test.py`
* **함수명**: `test_*` 로 시작하는 함수
* **클래스명**: `Test*` 로 시작하는 클래스 (선택 사항)

```bash
# 터미널에서 실행하기
pytest tests -q
```

---

### 2. Pytest의 핵심 마법 — Assertion Rewriting (어설션 재작성)

pytest가 전 세계 파이썬 개발자들에게 사랑받는 가장 큰 이유는 바로 **Assertion Rewriting(어설션 재작성)** 메커니즘 덕분입니다.

#### 💡 왜 특별할까요?
* **표준 `assert` 사용**: `self.assertEqual()`, `self.assertTrue()` 같은 복잡한 전용 메서드를 외울 필요 없이, 누구나 아는 평범한 `assert x == y` 구문을 그대로 씁니다.
* **지능적인 실패 분석 (AST Rewriting)**: 파이썬 기본 `assert`는 실패하면 아무 정보 없이 `AssertionError`만 던집니다. 하지만 pytest는 바이트코드를 지능적으로 재작성하여 **좌변과 우변의 실제 값, 그리고 어디가 다른지(Diff)** 를 터미널에 상세하게 출력해 줍니다.
* **가독성 극대화**: 복잡한 딕셔너리, 리스트, 또는 엔티티 객체를 비교할 때 어떤 항목이 왜 다른지 한눈에 직관적으로 파악할 수 있습니다.

---

#### ⚖️ 코드 비교: 기존 unittest vs pytest

##### ❌ 기존 방식 (`unittest` 스타일 — 장황하고 번거로움)
```python
import unittest

class TestMath(unittest.TestCase):
    def test_addition(self):
        result = 2 + 3
        # 클래스를 꼭 상속해야 하고, 검증 메서드를 외워서 써야 함
        self.assertEqual(result, 6)
```

##### ⭕ Pytest 방식 (간결하고 자연스러움)
```python
def test_addition():
    result = 2 + 3
    # 클래스 상속도 필요 없고, 평범한 assert만 쓰면 끝!
    assert result == 6
```

---

#### 🔍 실패 시 pytest의 친절한 출력 화면

만약 위 테스트가 실패하면, pytest는 좌변 계산 과정과 실제 값을 친절하게 풀어서 보여줍니다:

```text
>       assert result == 6
E       assert 5 == 6
E +  where 5 = 2 + 3
```
리스트나 딕셔너리가 다를 때도 어느 키와 값이 다른지 `+ / -` 기호로 한눈에 비교해 줍니다.

---

#### 🏛️ 클린 아키텍처와 단위 테스트의 관계

클린 아키텍처에서는 비즈니스 로직(Domain, Use Case)이 외부 DB나 웹 프레임워크에 의존하지 않도록 순수하게 설계합니다. 따라서 **테스트 코드 역시 프레임워크에 얽매이지 않고 순수하고 가볍게 작성**하는 것이 핵심입니다.

`pytest`와 평범한 `assert` 조합을 사용하면 테스트 코드 자체의 가독성이 극대화되어, 유스케이스가 기대하는 비즈니스 규칙과 결과값을 군더더기 없이 명확하게 검증할 수 있습니다.

---

### 3. `pytest.raises` — "이 에러가 터져야 성공!" (예외 검증)

잘못된 요청이 들어왔을 때 우리가 만든 커스텀 예외(`NotFoundError`, `ValidationError` 등)가 정상적으로 발생하는지 검사할 때 씁니다:

```python
# tests/test_usecases.py
import pytest
from backend.domain.exceptions import NotFoundError, ValidationError

def test_missing_record_raises_404():
    uc = LabRecordUseCase(InMemoryLabRecordRepository())
    
    # "이 안에서 NotFoundError가 터지면 테스트 합격!"
    with pytest.raises(NotFoundError):
        uc.delete("존재하지_않는_ID")
```

---

### 4. `@pytest.mark.parametrize` — "하나의 함수로 여러 데이터 시험하기"

같은 검증 로직에 여러 개의 입력값과 기댓값을 넣고 돌릴 때 씁니다:

```python
# tests/test_docs_router.py
@pytest.mark.parametrize("bad_id", ["tech999", "../Readme", "Readme"])
def test_read_rejects_invalid_path(bad_id: str):
    # bad_id 값 3개에 대해 3번의 독립된 테스트가 각각 실행됩니다!
    with pytest.raises(NotFoundError):
        read_tech_doc(bad_id)
```

---

### 5. 픽스처(`@pytest.fixture`) — "테스트 준비물 세팅 & 뒷정리"

테스트를 시작하기 전에 필요한 데이터나 공통 객체를 만들어 주는 '준비물' 기능입니다:

```python
@pytest.fixture
def auth_service() -> AuthUseCase:
    # 테스트에 쓸 유스케이스 준비물을 반환
    return AuthUseCase(InMemoryUserRepository(), PlainTextHasher(), StaticTokenProvider())

def test_login(auth_service: AuthUseCase):
    # 픽스처 이름을 인자로 적기만 하면 pytest가 알아서 주입해 줍니다!
    auth_service.ensure_user("admin", "pw")
    assert auth_service.authenticate(...).username == "admin"
```

---

### 6. 가짜 저장소(Fakes) — DB 없이 2초 만에 테스트 끝내기

진짜 PostgreSQL, MongoDB, Redis를 켜지 않고도, 메모리 딕셔너리로 동작하는 가짜 리포지토리(`tests/fakes.py`)를 만들어 유스케이스에 꽂아 넣습니다.

* **효과**: 13개 DB 컨테이너가 없어도 17개의 비즈니스 로직 테스트 전체가 **단 2초** 만에 완료됩니다.

---

### 7. 자주 쓰는 pytest 터미널 명령어

```bash
pytest tests -q                 # 간결하게 성공/실패만 출력
pytest -x                       # 하나라도 실패하면 즉시 중단
pytest -k "login"               # 이름에 'login'이 들어간 테스트만 실행
pytest --lf                     # 마지막에 실패했던 테스트만 골라서 재실행
pytest -vv                      # 실패 시 assert 비교 내용을 가장 상세하게 출력
```

---

### 💡 한눈에 정리하기

1. **Assertion Rewriting**: `self.assertEqual` 없이 평범한 `assert`만으로 어디가 틀렸는지 스마트하게 분석
2. **순수한 테스트**: 클린 아키텍처의 도메인과 유스케이스를 무거운 DB 없이 가볍고 명확하게 검증
3. **핵심 기능**: `@pytest.mark.parametrize`(데이터 반복), `pytest.raises`(예외 검증), `@pytest.fixture`(준비물 주입)
