"""Microsoft Entra / Azure AD OAuth2 登入流程相關路由。"""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

# 載入設定
settings = get_settings()

CLIENT_ID = settings.AZURE_CLIENT_ID
TENANT_ID = settings.AZURE_TENANT_ID
CLIENT_SECRET = settings.AZURE_CLIENT_SECRET
REDIRECT_URI = settings.AZURE_REDIRECT_URI

# 嘗試從設定中取得 Authority，沒有就用 tenant 組出預設值
_raw_authority: Optional[str] = getattr(settings, "resolved_azure_authority", None) or getattr(
    settings, "AZURE_AUTHORITY", None
)
if _raw_authority:
    AUTHORITY = _raw_authority.rstrip("/")
else:
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Scopes：若設定中有 AZURE_SCOPES 就用設定，否則用預設值
SCOPES = getattr(
    settings,
    "AZURE_SCOPES",
    ["openid", "profile", "email", "offline_access", "User.Read"],
)

AUTH_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"


@router.get("/login")
async def login(request: Request):
    """導向到 Microsoft 登入畫面。"""

    # 產生隨機 state，用於避免 CSRF
    state = secrets.token_urlsafe(16)
    request.session["auth_state"] = state

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    url = f"{AUTH_ENDPOINT}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Microsoft 登入完成後的回呼端點。
    - 成功：把 token 存進 session，然後 redirect 回 /contacts
    - 失敗：回傳 JSON 錯誤訊息
    """

    # 1. 若有 error 參數，直接回傳錯誤
    if error:
        return JSONResponse(
            {"error": error},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 2. 驗證 state，避免 CSRF
    expected_state = request.session.get("auth_state")
    if not expected_state or not state or state != expected_state:
        return JSONResponse(
            {"error": "invalid_state"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not code:
        return JSONResponse(
            {"error": "missing_code"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. 用 authorization code 換取 token
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        resp = await client.post(TOKEN_ENDPOINT, data=data)

    if resp.status_code != 200:
        return JSONResponse(
            {
                "error": "token_request_failed",
                "status_code": resp.status_code,
                "detail": resp.text,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token_data = resp.json()

    # 4. 把 token 存進 session，之後後端可以用來呼叫 Graph
    request.session["auth"] = {
        "token": token_data,
    }
    # 登入完成就不需要 state 了
    request.session.pop("auth_state", None)

    # 5. 重新導回通訊錄頁面（前端會依 session 狀態決定 UI）
    return RedirectResponse(url="/contacts")
