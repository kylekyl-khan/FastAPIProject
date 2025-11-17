import os
from functools import lru_cache
import urllib.parse

from dotenv import load_dotenv

# 載入 .env（若不存在也不會出錯）
load_dotenv()


class Settings:
    """
    集中管理專案設定（含 Azure AD / Entra 相關）。
    未來要擴充其他設定可直接加在這裡。
    """

    # FastAPI / session
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Azure AD / Entra
    AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
    AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
    AZURE_REDIRECT_URI: str = os.getenv(
        "AZURE_REDIRECT_URI", "https://127.0.0.1:8443/auth/callback"
    )

    # 若未指定 AZURE_AUTHORITY，預設用 TENANT_ID 組出 endpoint
    AZURE_AUTHORITY: str = os.getenv(
        "AZURE_AUTHORITY",
        ""
        if not os.getenv("AZURE_TENANT_ID")
        else f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}",
    )

    # OAuth2 scope（基本登入 + User.Read）
    AZURE_SCOPES: list[str] = [
        "openid",
        "profile",
        "email",
        "offline_access",
        "User.Read",
    ]

    # Database
    DB_SERVER: str = os.getenv("DB_SERVER", "db01_test")
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
    return Settings()


def get_database_url(settings: Settings | None = None) -> str:
    """對外提供取得資料庫 URL 的 helper，方便重用。"""

    settings = settings or get_settings()
    return settings.database_url
