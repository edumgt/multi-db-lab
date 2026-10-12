"""
api — HTTP Interface Adapter (컨트롤러 + 프리젠터).

  schemas/           pydantic 요청·응답 모델 (HTTP 경계의 "모양")
  presenters.py      도메인 엔티티 → 응답 스키마 변환
  error_handlers.py  도메인 예외 → HTTP 상태코드 변환
  deps.py            조립(Composition): 드라이버 클라이언트 → 게이트웨이 → 유스케이스
  *_router.py        엔드포인트. 요청을 파싱해 유스케이스를 호출하고 결과를 presenter 로 돌려주는 일만 합니다.
"""
