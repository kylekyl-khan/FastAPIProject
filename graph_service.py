from __future__ import annotations

"""與 Microsoft Graph 互動的服務模組。"""

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from config import get_settings

LOGGER = logging.getLogger(__name__)
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SELECT_FIELDS = ",".join(
    [
        "id",
        "displayName",
        "mail",
        "userPrincipalName",
        "department",
        "jobTitle",
        "officeLocation",
        "companyName",
        "accountEnabled",
        "mobilePhone",
        "businessPhones",
    ]
)


async def get_graph_access_token() -> str:
    """使用 Client Credentials Flow 取得 Graph Access Token。"""

    settings = get_settings()
    if not (settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET and settings.AZURE_TENANT_ID):
        LOGGER.error("Graph settings missing, please configure AZURE_* environment variables")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Graph settings not configured")
    token_url = f"{settings.resolved_azure_authority}/oauth2/v2.0/token"
    payload = {
        "client_id": settings.AZURE_CLIENT_ID,
        "client_secret": settings.AZURE_CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(token_url, data=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - 主要依賴日誌除錯
            LOGGER.error("Graph token API failed: %s - %s", exc.response.status_code, exc.response.text)
            detail = "Graph authentication failed"
            if exc.response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
                detail = "Unauthorized to access Microsoft Graph"
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail) from exc
        except httpx.HTTPError as exc:  # pragma: no cover
            LOGGER.error("Graph token request error: %s", exc)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph token request error") from exc

    token = response.json().get("access_token")
    if not token:
        LOGGER.error("Graph token response missing access_token")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph token not available")

    return token


async def _get_graph_page(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> dict[str, Any]:
    """呼叫 Graph API 取得單頁結果，並處理常見錯誤。"""

    try:
        response = await client.get(url, headers=headers)
        if response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            LOGGER.warning("Graph access denied (%s) when calling %s", response.status_code, url)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph authentication rejected")
        if response.status_code >= 500:
            LOGGER.error("Graph service error (%s) for %s", response.status_code, url)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Graph upstream error")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:  # pragma: no cover
        LOGGER.error("Graph request error for %s: %s", url, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph request failed") from exc


async def fetch_employees_from_graph() -> list[dict[str, Any]]:
    """呼叫 Microsoft Graph 取得使用者清單，並移除停用帳號。"""

    access_token = await get_graph_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    params = {"$select": SELECT_FIELDS, "$top": 999}
    url = f"{GRAPH_BASE_URL}/users?{urlencode(params)}"
    users: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        next_url: str | None = url
        while next_url:
            data = await _get_graph_page(client, next_url, headers)
            items = data.get("value") or []
            users.extend(items)
            next_url = data.get("@odata.nextLink")

    filtered_users = [item for item in users if item.get("accountEnabled", True)]
    return filtered_users


async def check_graph_health() -> dict[str, str]:
    """簡易呼叫 Graph 以驗證服務可用性。"""

    try:
        token = await get_graph_access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        test_url = f"{GRAPH_BASE_URL}/organization?$top=1"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await _get_graph_page(client, test_url, headers)
        return {"graph": "ok"}
    except HTTPException as exc:
        LOGGER.error("Graph health failed: %s", exc)
        return {"graph": f"failed: {exc.detail}"}
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Graph health unexpected error: %s", exc)
        return {"graph": "failed: unexpected error"}
