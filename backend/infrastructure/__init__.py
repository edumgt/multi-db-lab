"""
infrastructure 패키지 — Frameworks & Drivers (Clean Architecture 의 가장 바깥 원).

여기에는 "기술 그 자체" 만 있습니다.
  settings.py — pydantic-settings 로 환경변수를 읽는 설정 객체
  orm.py      — SQLAlchemy engine / Session / ORM 테이블 정의
  clients.py  — 각 DB 드라이버 클라이언트 팩토리(lru_cache 싱글턴) + 종료 시 정리(atexit)

[Clean Architecture 적용 사례 — 의존성 방향]
  이 패키지는 domain · usecases 를 import 하지 않습니다 (예외: ConfigurationError 변환용 domain.exceptions).
  반대로 adapters 의 게이트웨이는 이 패키지가 만든 클라이언트를 *생성자 인자로 받기만* 하고
  직접 팩토리를 호출하지 않습니다. 팩토리 호출은 조립 지점(adapters/api/deps.py, main.py) 에서만 합니다.
"""
