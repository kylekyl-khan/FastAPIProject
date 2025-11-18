"""
此檔案負責集中管理應用程式設定，並提供資料庫連線字串等共用方法。
所有設定皆由環境變數讀取，避免在程式碼中硬編碼敏感資訊。
"""
import os
import urllib.parse
from functools import lru_cache
import urllib.parse

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 載入 .env 設定；若檔案不存在則忽略
load_dotenv()


class Settings(BaseSettings):
    """
    此類別用於讀取並管理專案設定，包含資料庫與 Azure 身分驗證相關參數。
    透過 BaseSettings 可自動從環境變數載入設定，必要時可在 .env 提供預設值。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # FastAPI / session
    SECRET_KEY: str = Field(default="dev-secret-key-change-me", description="Session 加密用密鑰")

    # Azure AD / Entra
    AZURE_CLIENT_ID: str = ""
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_REDIRECT_URI: str = Field(
        default="https://127.0.0.1:8443/auth/callback",
        description="Azure 登入完成後的回呼位址",
    )
    AZURE_AUTHORITY: str = Field(default="", description="自訂 Azure OAuth Authority")
    AZURE_SCOPES: list[str] = Field(
        default=["openid", "profile", "email", "offline_access", "User.Read"],
        description="Azure OAuth 要求的權限範圍",
    )

    # Database
    DB_SERVER: str = Field(default="db01_test", description="SQL Server 主機名稱")
    DB_NAME: str = Field(default="DB_Mis_Admin", description="資料庫名稱")
    DB_USERNAME: str = Field(default="", description="資料庫使用者名稱")
    DB_PASSWORD: str = Field(default="", description="資料庫使用者密碼")
    DB_ACTIVE_STATUS: str = Field(default="在職", description="過濾在職員工的狀態值")

    @property
    def database_url(self) -> str:
        """
        組合 SQLAlchemy 連線字串；會將密碼進行 URL 編碼以避免特殊字元導致解析錯誤。
        """

        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mssql+pymssql://{self.DB_USERNAME}:{encoded_password}@{self.DB_SERVER}/{self.DB_NAME}"

    @property
    def resolved_azure_authority(self) -> str:
        """
        取得實際使用的 Azure Authority；若未明確指定則依租戶編號組合預設值。
        """

        if self.AZURE_AUTHORITY:
            return self.AZURE_AUTHORITY.rstrip("/")
        if self.AZURE_TENANT_ID:
            return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}"
        return ""

    # Database
    DB_SERVER: str = os.getenv("DB_SERVER", "QS-DBO1-TEST")
    DB_NAME: str = os.getenv("DB_NAME", "DB_Mis_Admin")
    DB_USERNAME: str = os.getenv("DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @property
    def database_url(self) -> str:
        """組出資料庫連線字串，使用環境變數提供的帳號密碼與伺服器資訊。"""

        password_encoded = urllib.parse.quote_plus(self.DB_PASSWORD)
        return (
            f"mssql+pymssql://{self.DB_USERNAME}:{password_encoded}"
            f"@{self.DB_SERVER}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    透過 lru_cache 確保設定物件全域共用，避免重複讀取環境變數。
    """

    return Settings()


def get_database_url(settings: Settings | None = None) -> str:
    """
    對外提供的資料庫連線字串取得方法，方便其他模組重用並在測試時覆寫設定。
    """

    config = settings or get_settings()
    return config.database_url
