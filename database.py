"""
建立可選的資料庫連線工具，主要作為健康檢查或未來備援使用。
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_database_url, get_settings

settings = get_settings()
database_url = get_database_url(settings)

engine = create_engine(database_url) if database_url else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


@contextmanager
def get_db_session() -> Generator:
    """
    提供一個 context manager 取得 DB Session。
    若未配置 DB（database_url 為 None），會拋出 RuntimeError。
    """

    if SessionLocal is None:
        raise RuntimeError("Database is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
