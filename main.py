"""
此檔案為 FastAPI 應用程式進入點，負責路由定義與中介層設定。
保留既有 API 行為，同時整理程式架構與風格。
"""

import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from auth_routes import router as auth_router
from config import get_settings
from contacts_service import (
    build_tree_from_employees,
    fetch_active_employees,
    fetch_employee_by_email,
    find_node_by_key,
)
from database import get_db_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
LOGGER = logging.getLogger("contacts")

SETTINGS = get_settings()
app = FastAPI()

# 設定 CORS，維持與原始行為一致
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 啟用 SessionMiddleware 以保存登入資訊
app.add_middleware(SessionMiddleware, secret_key=SETTINGS.SECRET_KEY)


# ---------------------------------------------------------------------------
# 依賴注入與共用函式
# ---------------------------------------------------------------------------


def get_current_user(request: Request):
    """
    從 Session 取得目前登入使用者資訊，若未登入則拋出 401。
    """

    auth_data = request.session.get("auth")
    if not auth_data or not auth_data.get("access_token"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth_data.get("user")


# ---------------------------------------------------------------------------
# 基本測試與健康檢查路由
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """
    回傳簡易訊息以確認服務運行。
    """

    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    """
    以動態名稱回應問候訊息。
    """

    return {"message": f"Hello {name}"}


@app.get("/health")
async def health(db: Session = Depends(get_db_session)):
    """
    執行簡單查詢以檢查資料庫連線狀態。
    """

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - 以日誌協助偵錯
        LOGGER.error("Health check failed: %s", exc)
        raise HTTPException(status_code=500, detail="DB connection failed") from exc


# ---------------------------------------------------------------------------
# 通訊錄相關 API
# ---------------------------------------------------------------------------


@app.get("/contacts/tree")
async def get_contacts_tree(db: Session = Depends(get_db_session)):
    """
    讀取所有在職員工並組成公司層級樹狀結構。
    """

    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        return tree
    except Exception as exc:  # pragma: no cover - 以日誌協助偵錯
        LOGGER.error("get_contacts_tree failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load contacts tree") from exc


@app.get("/contacts/tree/{root_name}")
async def get_contacts_subtree(root_name: str, db: Session = Depends(get_db_session)):
    """
    取得指定節點的子樹，若找不到則回傳空物件。
    """

    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        subtree = find_node_by_key(tree, root_name)
        return subtree or {}
    except Exception as exc:  # pragma: no cover
        LOGGER.error("get_contacts_subtree failed for %s: %s", root_name, exc)
        raise HTTPException(status_code=500, detail="Failed to load contacts subtree") from exc


@app.get("/contacts/employee")
async def get_employee(mail: str = Query(..., description="Employee email"), db: Session = Depends(get_db_session)):
    """
    依電子郵件查詢單一員工的公開聯絡資訊。
    """

    try:
        employee = fetch_employee_by_email(db, mail)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        LOGGER.info("get_employee: %s -> %s", mail, employee.name)
        return employee
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        LOGGER.error("get_employee failed for %s: %s", mail, exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/contacts/tree/protected-example")
async def get_protected_contacts_tree(current_user=Depends(get_current_user), db: Session = Depends(get_db_session)):
    """
    示範受保護的樹狀查詢，需要先完成登入流程才能存取。
    """

    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        return {"current_user": current_user, "tree": tree}
    except Exception as exc:  # pragma: no cover
        LOGGER.error("get_protected_contacts_tree failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load contacts tree") from exc


@app.get("/contacts")
async def contacts_page():
    """
    回傳通訊錄前端頁面。
    """

    return FileResponse("./static/contacts.html")


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    """
    回傳 Outlook Add-in manifest 檔案。
    """

    return FileResponse("./static/optimized-manifest.xml")


# ---------------------------------------------------------------------------
# 中介層與路由掛載
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
