from __future__ import annotations

"""集中管理應用程式設定，所有敏感資訊皆由環境變數提供。"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 載入 .env；若不存在則安靜略過
load_dotenv()


class Settings(BaseSettings):
    """專案設定模型，透過環境變數注入。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 應用程式
    APP_HOST: str = Field(default="127.0.0.1", description="應用程式監聽位址")
    APP_PORT: int = Field(default=18080, description="應用程式監聽埠號")
    SECRET_KEY: str = Field(default="dev-secret-key-change-me", description="Session 加密密鑰")

    # 公司資訊
    COMPANY_ID: str = Field(default="KH", description="公司代碼，用於樹狀節點 key")
    COMPANY_NAME: str = Field(default="康軒文教", description="公司名稱，樹狀根節點顯示文字")

    # Azure AD / Microsoft Graph
    AZURE_CLIENT_ID: str = Field(default="", description="Azure AD 應用程式 Client ID")
    AZURE_CLIENT_SECRET: str = Field(default="", description="Azure AD 應用程式 Client Secret")
    AZURE_TENANT_ID: str = Field(default="", description="Azure AD 租戶 ID")
    AZURE_AUTHORITY: str = Field(default="", description="自訂 Azure OAuth Authority，預設依租戶組合")

    # SQL Server 設定（目前主資料來源為 Graph，可視需要保留）
    DB_SERVER: str = Field(default="", description="SQL Server 主機名稱")
    DB_NAME: str = Field(default="", description="資料庫名稱")
    DB_USERNAME: str = Field(default="", description="資料庫使用者名稱")
    DB_PASSWORD: str = Field(default="", description="資料庫使用者密碼")
    DB_ACTIVE_STATUS: str = Field(default="在職", description="過濾在職員工的狀態值")

    @property
    def resolved_azure_authority(self) -> str:
        """取得實際使用的 Azure Authority。"""

        if self.AZURE_AUTHORITY:
            return self.AZURE_AUTHORITY.rstrip("/")
        if self.AZURE_TENANT_ID:
            return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}"
        return "https://login.microsoftonline.com/common"


@lru_cache()
def get_settings() -> Settings:
    """取得全域共用的設定實例。"""

    return Settings()
