"""
adapters 패키지 — Interface Adapters (Clean Architecture 의 세 번째 원).

[Clean Architecture 적용 사례 — Interface Adapter]
  "바깥 세계의 모양" 과 "유스케이스가 이해하는 모양" 을 서로 변환하는 계층입니다.
    gateways/  — DB 드라이버 결과(dict · Row · 드라이버 객체) ↔ 도메인 엔티티   (포트 구현체)
    security/  — bcrypt · JWT 라이브러리 ↔ PasswordHasher · TokenProvider 포트
    api/       — HTTP 요청(pydantic) → 유스케이스 입력, 엔티티 → HTTP 응답(pydantic)  (컨트롤러 + 프리젠터)

[의존성 방향]
  adapters → usecases → domain  (안쪽으로만)
  adapters → infrastructure 는 "타입 참조" 수준(드라이버 클라이언트 타입)만 허용하고,
  클라이언트 *생성* 은 api/deps.py 조립 지점에서만 합니다.
"""
