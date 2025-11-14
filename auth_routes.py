import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_oauth_endpoints() -> Dict[str, str]:
    """
    根據設定組出 Azure AD v2.0 的 authorize / token endpoint。
    """
    settings = get_settings()
    authority = settings.AZURE_AUTHORITY.rstrip("/")
    authorize_url = f"{authority}/oauth2/v2.0/authorize"
    token_url = f"{authority}/oauth2/v2.0/token"
    return {"authorize": authorize_url, "token": token_url}


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """
    產生 Microsoft Entra (Azure AD) 的 authorize URL 並 302 redirect。
    - 會在 session 中存入 state，用於後續 /auth/callback 驗證。
    """
    settings = get_settings()
    endpoints = _get_oauth_endpoints()

    if not settings.AZURE_CLIENT_ID or not settings.AZURE_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure AD settings are not configured properly.",
        )

    # CSRF 防護用 state
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
    處理 Azure AD redirect 回來的結果：
    - 檢查 error / state
    - 用 code 換取 token
    - 將 access_token 與簡單 user info 存到 session
    - 最後 redirect 回主畫面（預設 /contacts.html）
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

    # 驗證 state
    stored_state = request.session.get("auth_state")
    request.session.pop("auth_state", None)
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter.",
        )

    # code -> token
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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No access_token returned from Azure AD.",
            )

        # 可選：呼叫 Graph /me 取得使用者資訊
        user_info: Dict[str, Any] | None = None
        try:
            graph_me_url = "https://graph.microsoft.com/v1.0/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            me_resp = await client.get(graph_me_url, headers=headers)
            if me_resp.status_code == 200:
                user_info = me_resp.json()
        except Exception:
            user_info = None

    # 存入 session
    request.session["auth"] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": id_token,
        "user": user_info,
    }

    # 登入後導回通訊錄頁面
    return RedirectResponse(url="/contacts.html", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """
    登出：清除 session 中的 auth 資訊並導回主畫面。
    如需 SSO 登出，可再串 Azure 登出端點。
    """
    request.session.pop("auth", None)
    return RedirectResponse(url="/contacts.html", status_code=status.HTTP_302_FOUND)


@router.get("/me")
async def me(request: Request) -> JSONResponse:
    """
    回傳目前登入使用者資訊，給前端檢查登入狀態用。
    - 已登入：{"authenticated": true, "user": {...}}
    - 未登入：{"authenticated": false}
    """
    auth_data: Optional[Dict[str, Any]] = request.session.get("auth")
    if not auth_data or not auth_data.get("access_token"):
        return JSONResponse({"authenticated": False})

    return JSONResponse(
        {
            "authenticated": True,
            "user": auth_data.get("user"),
        }
    )
