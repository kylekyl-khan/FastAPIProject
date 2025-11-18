from __future__ import annotations

"""FastAPI 入口點，提供通訊錄樹狀 API 與健康檢查。"""

import logging
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config import get_settings
from graph_service import check_graph_health, fetch_employees_from_graph
from models import EmployeePublic, TreeNode, build_tree_from_employees, find_node_by_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
LOGGER = logging.getLogger("contacts")

SETTINGS = get_settings()
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SETTINGS.SECRET_KEY)


async def fetch_active_employees() -> list[EmployeePublic]:
    """以 Microsoft Graph 為主資料來源取得在職員工。"""

    raw_users = await fetch_employees_from_graph()
    employees: list[EmployeePublic] = []
    for user in raw_users:
        company_id = SETTINGS.COMPANY_ID or "KH"
        employee_id = user.get("id") or user.get("userPrincipalName") or ""
        email = user.get("mail") or user.get("userPrincipalName")
        campus = user.get("companyName") or user.get("officeLocation")
        dept_value = user.get("department")
        job_title = user.get("jobTitle")
        business_phones = user.get("businessPhones") or []

        employees.append(
            EmployeePublic(
                company_id=company_id,
                employee_id=employee_id,
                name=user.get("displayName") or email or employee_id,
                email=email,
                campus=campus,
                dept_id=dept_value,
                dept_name=dept_value,
                title=job_title,
                job=job_title,
                phone_no=business_phones[0] if business_phones else None,
                mobile_phone=user.get("mobilePhone"),
                status="在職",
            )
        )
    return employees


@app.get("/")
async def root() -> dict[str, str]:
    """基本檢查入口。"""

    return {"message": "Hello World"}


@app.get("/health")
async def health() -> dict[str, str]:
    """健康檢查，聚焦 Graph 連線狀態。"""

    graph_status = await check_graph_health()
    status_value = "ok" if graph_status.get("graph") == "ok" else "degraded"
    return {"status": status_value, **graph_status}


@app.get("/contacts/tree")
async def get_contacts_tree() -> list[TreeNode]:
    """回傳完整的公司通訊錄樹狀結構。"""

    try:
        employees = await fetch_active_employees()
        tree = build_tree_from_employees(employees)
        return tree
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - 以日誌協助偵錯
        LOGGER.error("get_contacts_tree failed: %s", exc)
        LOGGER.debug("Traceback: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="載入通訊錄資料時發生錯誤") from exc


@app.get("/contacts/tree/{root_key}")
async def get_contacts_subtree(root_key: str) -> TreeNode | dict:
    """取得指定節點子樹，找不到時回傳空物件。"""

    try:
        employees = await fetch_active_employees()
        tree = build_tree_from_employees(employees)
        subtree = find_node_by_key(tree, root_key)
        return subtree or {}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        LOGGER.error("get_contacts_subtree failed for %s: %s", root_key, exc)
        LOGGER.debug("Traceback: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="載入通訊錄子樹時發生錯誤") from exc


@app.get("/contacts")
async def contacts_page() -> FileResponse:
    """回傳通訊錄前端頁面。"""

    return FileResponse("./static/contacts.html")


@app.get("/optimized-manifest.xml")
async def optimized_manifest() -> FileResponse:
    """回傳 Outlook Add-in manifest 檔案。"""

    return FileResponse("./static/optimized-manifest.xml")


app.mount("/static", StaticFiles(directory="static"), name="static")
