"""
此檔案負責與 Microsoft Entra (Azure AD) 相關的登入、回呼與登出路由。
保留原本的 OAuth 流程，並提供登入狀態查詢 API。
"""

import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# OAuth 工具函式
# ---------------------------------------------------------------------------


def _get_oauth_endpoints() -> Dict[str, str]:
    """
    根據設定組出 Azure AD v2.0 的 authorize 與 token endpoint。
    """

    settings = get_settings()
    authority = settings.resolved_azure_authority.rstrip("/")
    authorize_url = f"{authority}/oauth2/v2.0/authorize"
    token_url = f"{authority}/oauth2/v2.0/token"
    return {"authorize": authorize_url, "token": token_url}


# ---------------------------------------------------------------------------
# 路由實作
# ---------------------------------------------------------------------------


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """
    產生 Microsoft Entra (Azure AD) 的授權網址並進行 302 重新導向。
    會於 Session 中存入 state 以抵禦 CSRF 攻擊。
    """

    settings = get_settings()
    endpoints = _get_oauth_endpoints()

    if not settings.AZURE_CLIENT_ID or not settings.AZURE_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure AD settings are not configured properly.",
        )

    state = secrets.token_urlsafe(32)
    request.session["auth_state"] = state

    params = {
        "client_id": settings.AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.AZURE_REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(settings.AZURE_SCOPES),
        "state": state,
    }

    authorize_url = f"{endpoints['authorize']}?{urlencode(params)}"
    return RedirectResponse(authorize_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> RedirectResponse | JSONResponse:
    """
    處理 Azure AD 回呼：驗證 state、交換授權碼取得 token，並將資訊存入 Session。
    登入成功後會導回通訊錄頁面。
    """

    settings = get_settings()
    endpoints = _get_oauth_endpoints()

    if error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": error, "error_description": error_description},
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'code' or 'state' in callback.",
        )

    stored_state = request.session.get("auth_state")
    request.session.pop("auth_state", None)
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter.")

    data = {
        "client_id": settings.AZURE_CLIENT_ID,
        "client_secret": settings.AZURE_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.AZURE_REDIRECT_URI,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(endpoints["token"], data=data)
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to obtain token from Azure AD: {token_resp.text}",
            )

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        id_token = token_data.get("id_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No access_token returned from Azure AD.")

        user_info: Dict[str, Any] | None = None
        try:
            graph_me_url = "https://graph.microsoft.com/v1.0/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            me_resp = await client.get(graph_me_url, headers=headers)
            if me_resp.status_code == 200:
                user_info = me_resp.json()
        except Exception:
            user_info = None

    request.session["auth"] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": id_token,
        "user": user_info,
    }

    return RedirectResponse(url="/contacts", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """
    清除 Session 中的登入資訊並導回主畫面。
    如需 SSO 登出，可另行串接 Azure 登出端點。
    """

    request.session.pop("auth", None)
    return RedirectResponse(url="/contacts", status_code=status.HTTP_302_FOUND)


@router.get("/me")
async def me(request: Request) -> JSONResponse:
    """
    回傳目前登入狀態，供前端判斷是否顯示登入按鈕。
    已登入會附帶 user 資訊，未登入則回傳 authenticated=False。
    """

    auth_data: Optional[Dict[str, Any]] = request.session.get("auth")
    if not auth_data or not auth_data.get("access_token"):
        return JSONResponse({"authenticated": False})

    return JSONResponse({"authenticated": True, "user": auth_data.get("user")})
