from __future__ import annotations

"""Microsoft Graph 取用戶服務。

這個模組負責：
1. 透過 Client Credentials Flow 向 Entra 取得 access token
2. 呼叫 Microsoft Graph `/v1.0/users` 取得組織中的使用者清單
3. 回傳原始的使用者資料 list[dict]，由 main.py 進一步轉成 EmployeePublic
"""

from typing import Any, Dict, List

import httpx
import logging

from config import get_settings

logger = logging.getLogger("graph_service")


def get_graph_access_token() -> str:
    """向 Entra / Azure AD 取得呼叫 Microsoft Graph 所需的 access token。"""
    settings = get_settings()

    authority = getattr(settings, "AZURE_AUTHORITY", None) or (
        f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"
    )
    token_url = f"{authority}/oauth2/v2.0/token"

    # 使用 Client Credentials Flow，scope 採用 .default
    data = {
        "client_id": settings.AZURE_CLIENT_ID,
        "client_secret": settings.AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    logger.info("Requesting Graph access token from %s", token_url)

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(token_url, data=data)
        resp.raise_for_status()
        payload = resp.json()

    access_token = payload.get("access_token")
    if not access_token:
        logger.error("Graph token response has no access_token: %s", payload)
        raise RuntimeError("Failed to obtain Graph access token")

    return access_token


def fetch_employees_from_graph() -> List[Dict[str, Any]]:
    """
    從 Microsoft Graph 取得使用者清單。

    - 呼叫 /v1.0/users
    - 使用 $select 只取我們需要的欄位
    - 支援分頁：追蹤 @odata.nextLink，把所有頁面資料串起來
    - 只保留 accountEnabled != False 的使用者
    """
    access_token = get_graph_access_token()

    base_url = "https://graph.microsoft.com/v1.0/users"
    # 選取我們需要的欄位，之後在 main.py 會做欄位映射
    params = {
        "$select": (
            "id,displayName,mail,userPrincipalName,"
            "department,jobTitle,officeLocation,"
            "mobilePhone,businessPhones,accountEnabled"
        ),
        "$top": "999",
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    all_users: List[Dict[str, Any]] = []
    next_url: str | None = base_url

    logger.info("Fetching users from Microsoft Graph...")

    with httpx.Client(timeout=15.0) as client:
        while next_url:
            resp = client.get(next_url, headers=headers, params=params if next_url == base_url else None)
            resp.raise_for_status()
            data = resp.json()

            page_users = data.get("value", [])
            if not isinstance(page_users, list):
                logger.error("Unexpected Graph users payload format: %s", data)
                raise RuntimeError("Graph users response format invalid")

            # 過濾掉明確停用的帳號
            for user in page_users:
                if user.get("accountEnabled") is False:
                    continue
                all_users.append(user)

            # 檢查是否有下一頁
            next_url = data.get("@odata.nextLink")

    logger.info("fetch_employees_from_graph: got %d users from Graph", len(all_users))
    return all_users


__all__ = ["get_graph_access_token", "fetch_employees_from_graph"]
