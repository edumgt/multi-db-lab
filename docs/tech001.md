> **쉽게 이해하기**
>
> - **한 줄 요약** — 폴더를 '파이썬 패키지' 로 만들어 주는 표시 파일입니다. 비어 있어도 됩니다.
> - **비유하면** — 건물의 '안내 데스크(인포메이션 센터)'. 내부 연구실이 복잡해도 1층 안내 데스크에서 필요한 것을 바로 찾을 수 있습니다.
> - **이 프로젝트에서는** — `backend/usecases/__init__.py` 가 여러 유스케이스를 모아 `from backend.usecases import PostUseCase` 한 줄로 쓰게 해 줍니다.
> - **기억할 것** — 밖에서 자주 쓰는 클래스나 함수만 깔끔하게 꺼내두고, 무거운 초기화 코드는 넣지 않습니다.

파이썬에서 `__init__.py` 파일은 단순한 폴더를 **언제든 불러다 쓸 수 있는 부품 상자(파이썬 패키지)** 로 만들어 주는 핵심 파일입니다.

왜 이 파일이 필요하고 어떻게 유용하게 쓰이는지 핵심 4가지를 알기 쉽게 정리합니다.

---

### 1. "이 폴더는 파이썬 패키지입니다" 선언하기

* **폴더를 패키지로 인식**: 파이썬에게 이 폴더가 일반 파일 보관함이 아니라, 파이썬 모듈들이 들어 있는 **패키지(Package)** 임을 명시적으로 알려줍니다.
* **비어 있어도 OK**: 파일 안에 아무 내용이 없어도(`0 byte`), 파일이 존재하기만 하면 파이썬이 패키지로 인식합니다.
* *참고*: 파이썬 3.3부터는 이 파일이 없어도 폴더를 인식하지만(네임스페이스 패키지), 패키지 경계를 명확히 하고 의도치 않은 임포트 실수를 막기 위해 **작성하는 것이 표준 모범 사례**입니다.

---

### 2. 패키지를 불러올 때 딱 한 번 실행되는 초기화 코드

* 누군가 이 패키지를 `import`하는 순간, `__init__.py` 안의 코드가 **단 한 번만 자동으로 실행**됩니다.
* **주요 용도**: 패키지 전체에서 공통으로 쓸 로거(Logger) 설정, 전역 설정값 준비, DB 연결 초기화 등을 넣어둘 수 있습니다.
* ⚠️ **주의**: 너무 무거운 작업이나 시간이 오래 걸리는 코드를 넣으면, 패키지를 임포트할 때마다 프로그램 시작이 느려지므로 가벼운 설정만 넣는 것이 좋습니다.

---

### 3. 복잡한 내부를 감추는 단일 창구 — 퍼사드(Facade) 패턴

#### 💡 퍼사드(Facade) 패턴이란?
건물의 '정면(외관)'을 뜻하는 말로, **내부가 아무리 복잡하게 얽혀 있어도 외부 사용자에게는 단순하고 통일된 안내 창구 하나만 제공하는 디자인 패턴**입니다.

* **복잡성 숨기기**: 사용하는 사람(클라이언트)은 내부의 수많은 클래스나 파일 경로를 일일이 알 필요가 없습니다.
* **결합도 낮추기 (영향 최소화)**: 내부 코드가 바뀌거나 파일 위치가 옮겨져도, 안내 창구(`__init__.py`)만 그대로 유지되면 외부 코드는 고칠 필요가 없습니다.
* **사용 편의성**: 자주 쓰는 복잡한 흐름을 메소드 하나 또는 깔끔한 임포트 한 줄로 끝낼 수 있습니다.

#### 🛒 쉬운 예시: 쇼핑몰 주문 처리 시스템
쇼핑몰에서 주문 하나를 처리하려면 재고 확인, 결제, 배송이라는 복잡한 3가지 하위 시스템이 필요합니다.

```python
# --- 복잡한 내부 부품 시스템들 ---
class InventorySystem:
    def check_stock(self, item_id: str) -> bool:
        print(f"[{item_id}] 1. 재고를 확인합니다.")
        return True

class PaymentSystem:
    def process_payment(self, amount: int) -> bool:
        print(f"{amount}원 2. 결제를 진행합니다.")
        return True

class ShippingSystem:
    def arrange_shipping(self, item_id: str) -> None:
        print(f"[{item_id}] 3. 배송을 접수합니다.")


# --- 안내 데스크 역할을 하는 퍼사드(Facade) 클래스 ---
class OrderFacade:
    def __init__(self):
        self.inventory = InventorySystem()
        self.payment = PaymentSystem()
        self.shipping = ShippingSystem()

    def complete_order(self, item_id: str, amount: int) -> None:
        """손님은 내부 3단계를 몰라도 이 메서드 하나로 주문을 끝냅니다."""
        print("--- 주문 프로세스 시작 ---")
        if self.inventory.check_stock(item_id):
            if self.payment.process_payment(amount):
                self.shipping.arrange_shipping(item_id)
        print("--- 주문 프로세스 완료 ---\n")


# --- 실제 사용하는 클라이언트 코드 ---
if __name__ == "__main__":
    # 손님이 복잡한 3개 시스템을 직접 다룰 필요가 전혀 없습니다!
    order = OrderFacade()
    order.complete_order("item_12345", 50000)
```

#### 📂 `__init__.py`가 바로 퍼사드 패턴인 이유
파이썬 패키지에서 `__init__.py`가 위 `OrderFacade`와 똑같은 역할을 수행합니다.

- ❌ **적용 전 (불편함)**: 내부 폴더와 파일 구조를 일일이 알아야 함
  ```python
  from my_package.models.user_model import User
  from my_package.services.user_service import UserService
  ```
- ⭕ **`my_package/__init__.py`에 모아둔 후 (퍼사드 적용)**:
  ```python
  # my_package/__init__.py 에서 미리 꺼내놓음
  from .models.user_model import User
  from .services.user_service import UserService
  ```
  외부에서는 단 한 줄로 깔끔하게 가져옵니다:
  ```python
  from my_package import User, UserService
  ```

> **이 프로젝트의 실제 적용 사례**  
> `backend/usecases/__init__.py`에서 `PostUseCase`, `AuthUseCase` 등을 미리 임포트해 두었기 때문에, 라우터(API)에서는 내부 폴더 깊이를 몰라도 `from backend.usecases import PostUseCase`로 바로 가져다 쓸 수 있습니다.

---

### 4. `__all__` — 공개할 것과 숨길 것 정하기

* `__init__.py` 안에 `__all__` 리스트를 정의하면, `from package import *` (모두 가져오기)를 했을 때 **어떤 클래스나 함수만 외부에 공개할지**를 명확하게 제한할 수 있습니다.
* 외부에서 함부로 건드리면 안 되는 내부용 함수나 변수를 숨겨두는 안전한 자물쇠 역할을 합니다.

```python
# my_package/__init__.py
__all__ = ["User", "UserService"]  # 이 2가지만 외부에 안전하게 공개!
```

---

### 💡 한눈에 정리하기

1. **폴더 인식**: 단순한 폴더를 파이썬 패키지로 만들어 줍니다.
2. **단일 창구 (퍼사드)**: 내부가 아무리 복잡해도 밖에서는 `from 패키지 import 클래스` 한 줄로 편하게 쓰게 해 줍니다.
3. **클린 아키텍처 연결**: 도메인(Domain), 유스케이스(UseCase) 등 각 계층의 입구를 깔끔하게 정돈하여 계층 간의 의존성을 줄여줍니다.