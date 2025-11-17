"""
集中管理應用程式設定，並提供資料庫連線字串的共用方法。
"""

from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # FastAPI / session
    SECRET_KEY: str = Field(default="dev-secret-key-change-me", description="Session 加密用密鑰")

    # Azure AD / Entra
    AZURE_CLIENT_ID: str
    AZURE_TENANT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_REDIRECT_URI: str
    AZURE_AUTHORITY: Optional[str] = None
    AZURE_SCOPES: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email", "offline_access", "User.Read"],
        description="Azure OAuth 要求的權限範圍",
    )

    # Database (optional)
    DB_SERVER: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_USERNAME: Optional[str] = None
    DB_PASSWORD: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url(settings: Optional[Settings] = None) -> Optional[str]:
    config = settings or get_settings()
    if not all([config.DB_SERVER, config.DB_NAME, config.DB_USERNAME, config.DB_PASSWORD]):
        return None

    odbc_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={config.DB_SERVER};"
        f"DATABASE={config.DB_NAME};"
        f"UID={config.DB_USERNAME};"
        f"PWD={config.DB_PASSWORD};"
        "TrustServerCertificate=yes;"
    )
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"
