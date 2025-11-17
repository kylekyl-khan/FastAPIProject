"""與 Microsoft Graph 整合的服務層。"""

import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request, status

from models import EmployeePublic

LOGGER = logging.getLogger(__name__)
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SELECT_FIELDS = (
    "id,displayName,mail,userPrincipalName,jobTitle,department,officeLocation,"
    "companyName,mobilePhone,businessPhones,accountEnabled"
)


def get_access_token_from_session(request: Request) -> str:
    """從 session 中取得目前登入使用者的 Graph access token。"""

    auth_data = request.session.get("auth") or {}
    token_data = auth_data.get("token") if isinstance(auth_data.get("token"), dict) else auth_data
    access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return access_token


async def _get_graph_page(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.get(url, headers=headers)
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        LOGGER.warning("Graph returned 401 Unauthorized when calling %s", url)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is invalid or expired")
    if response.status_code in {status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS}:
        LOGGER.warning("Graph call blocked (%s) for %s", response.status_code, url)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph API temporarily unavailable")
    if response.status_code >= 500:
        LOGGER.warning("Graph server error (%s) for %s", response.status_code, url)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Graph API error")
    response.raise_for_status()
    return response.json()


async def fetch_graph_users(access_token: str) -> list[dict[str, Any]]:
    """使用給定的 access token 呼叫 Microsoft Graph /users。"""

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "$select": SELECT_FIELDS,
        "$top": 999,
        "$filter": "accountEnabled eq true",
    }
    url = f"{GRAPH_BASE_URL}/users?{urlencode(params)}"
    users: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        next_url: str | None = url
        while next_url:
            data = await _get_graph_page(client, next_url, headers)
            items = data.get("value") or []
            users.extend(items)
            next_url = data.get("@odata.nextLink")

    return users


def map_graph_user_to_employee(user: dict[str, Any]) -> EmployeePublic:
    """將 Graph user 物件轉換為 EmployeePublic。"""

    company_name = user.get("companyName") or "KangHsu"
    email = user.get("mail") or user.get("userPrincipalName")
    business_phones = user.get("businessPhones") or []
    account_enabled = user.get("accountEnabled")

    return EmployeePublic(
        company_id=company_name,
        employee_id=user.get("id", ""),
        name=user.get("displayName") or email or "Unknown",
        email=email,
        campus=user.get("officeLocation"),
        dept_id=user.get("department"),
        dept_name=user.get("department"),
        title=user.get("jobTitle"),
        job=user.get("jobTitle"),
        phone_no=business_phones[0] if business_phones else None,
        mobile_phone=user.get("mobilePhone"),
        status="enabled" if account_enabled is not False else "disabled",
    )


async def ping_graph(access_token: Optional[str] = None) -> bool:
    """簡易 Graph 健康檢查。"""

    if not access_token:
        # 若無 token，暫時視為略過檢查，回傳 True
        return True

    url = f"{GRAPH_BASE_URL}/me"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == status.HTTP_401_UNAUTHORIZED:
                LOGGER.warning("Graph ping unauthorized")
                return False
            resp.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - 健康檢查失敗時僅記錄
        LOGGER.warning("Graph ping failed: %s", exc)
        return False
