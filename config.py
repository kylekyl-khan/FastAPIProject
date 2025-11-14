import os
from functools import lru_cache

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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
