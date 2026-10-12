"""
gateways — domain/ports.py 의 추상 인터페이스를 각 DB 드라이버로 구현한 어댑터 모음.

공통 규칙 (모든 게이트웨이가 지킵니다):
  1. 포트(ABC)를 명시적으로 상속하고 모든 @abstractmethod 를 구현한다.
  2. 생성자에서 드라이버 클라이언트를 *주입받는다* (직접 생성하지 않는다).
  3. 드라이버 고유 예외는 `ExternalServiceError` 로 변환하고 `from exc` 로 원인을 체이닝한다.
  4. 포트 밖으로는 도메인 엔티티만 내보낸다 (dict / Row / ORM 객체 금지).
"""
