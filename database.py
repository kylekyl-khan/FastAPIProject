"""
此檔案負責建立資料庫連線引擎並提供 SQLAlchemy Session 工具函式。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_database_url

# 建立 SQLAlchemy 引擎與 SessionFactory
engine = create_engine(get_database_url(), echo=False, connect_args={"charset": "utf8"})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Generator[Session, None, None]:
    """
    產生一個資料庫 Session，並在完成後自動釋放連線。
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
