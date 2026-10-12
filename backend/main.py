"""
FastAPI 애플리케이션 조립 지점 (Frameworks & Drivers 계층의 진입점).

[Clean Architecture 적용 사례 — 의존성 방향]
  main.py 는 모든 계층을 import 할 수 있는 "가장 바깥" 입니다. 반대 방향 import 는 없습니다:
      main → adapters.api(라우터·에러핸들러·deps) → usecases → domain
      main → infrastructure(orm·clients·settings)
  시드 데이터 생성도 ORM 을 직접 만지지 않고 유스케이스(AuthUseCase.ensure_user) 와 게이트웨이를 통해 수행합니다.

[Python 중급 적용 사례 — 예외 처리 · 컨텍스트 매니저]
  * `@asynccontextmanager` lifespan : yield 앞은 startup, 뒤는 shutdown.
    try/finally 로 감싸 startup 중 예외가 나도 `registry.close_all()` 이 실행되게 합니다.
  * 과거의 `@app.on_event("startup")` + 모듈 수준 `atexit` 은 FastAPI 0.93+ 에서 deprecated 입니다.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.adapters.api.auth_router import router as auth_router
from backend.adapters.api.deps import build_auth_usecase
from backend.adapters.api.employee_router import router as employee_router
from backend.adapters.api.error_handlers import register_error_handlers
from backend.adapters.api.lab_router import router as lab_router
from backend.adapters.api.post_router import router as post_router
from backend.adapters.gateways.sql_repositories import SqlPostRepository
from backend.infrastructure.clients import registry
from backend.infrastructure.orm import Base, SessionLocal, engine
from backend.infrastructure.settings import settings
from backend.usecases import PostUseCase

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
SEED_ADMIN = ("admin", "admin1234")


def seed_data() -> None:
    """관리자 계정과 샘플 게시글 15 건을 멱등하게 생성합니다 (유스케이스 경유)."""
    with SessionLocal() as db:
        admin = build_auth_usecase(db).ensure_user(*SEED_ADMIN)
        posts = PostUseCase(SqlPostRepository(db))
        if posts.list_posts("", page=1, size=1, sort="id:asc").total == 0:
            for idx in range(1, 16):
                posts.create_post(f"샘플 게시글 {idx}", f"PostgreSQL 연동 샘플 본문입니다. (#{idx})", owner=admin)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        Base.metadata.create_all(bind=engine)
        seed_data()
        yield
    finally:
        registry.close_all()
        engine.dispose()


def create_app() -> FastAPI:
    """앱 팩토리. 테스트에서 설정을 바꿔 여러 인스턴스를 만들 수 있도록 함수로 둡니다."""
    app = FastAPI(title="FastAPI Multi-DB Lab (Clean Architecture)", version="3.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(auth_router)
    app.include_router(post_router)
    app.include_router(employee_router)
    app.include_router(lab_router)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
