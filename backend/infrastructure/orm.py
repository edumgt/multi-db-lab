"""
SQLAlchemy ORM 정의 — users / posts 테이블과 세션 관리.

[Clean Architecture 적용 사례 — 엔티티와 ORM 모델의 분리]
  * 여기의 `UserRow` / `PostRow` 는 "테이블 행" 입니다. 도메인 엔티티(domain/entities.py 의 User/Post)
    와는 다른 객체이며, 변환은 adapters/gateways/sql_repositories.py 가 담당합니다.
  * 과거에는 ORM 객체가 라우터·서비스까지 그대로 흘러다녀, 세션이 닫힌 뒤 lazy-load 가 터지는 등의
    문제가 생길 수 있었습니다. 이제 세션 밖으로는 불변 dataclass 만 나갑니다.

[Python 중급 적용 사례 — 타입 힌트]
  * SQLAlchemy 2.0 의 `Mapped[...]` / `mapped_column` 은 타입 힌트 기반 선언입니다.
    `Mapped[str | None]` 처럼 Optional 을 쓰면 nullable 컬럼이 됩니다.

[Python 중급 적용 사례 — 예외 처리]
  * `get_db()` 의 try/finally 는 예외가 나도 세션을 반드시 닫습니다(커넥션 누수 방지).
"""

from __future__ import annotations

from datetime import datetime
from typing import Generator

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from backend.infrastructure.settings import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posts: Mapped[list[PostRow]] = relationship(back_populates="owner", cascade="all, delete")


class PostRow(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    owner: Mapped[UserRow] = relationship(back_populates="posts")


def get_db() -> Generator[Session, None, None]:
    """요청 단위 세션. FastAPI `Depends(get_db)` 로 주입되며 응답 후 finally 에서 닫힙니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
