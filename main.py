from __future__ import annotations

"""主應用程式進入點（Graph 為主的公司通訊錄 API）。"""

import logging
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from auth_routes import router as auth_router
from config import get_database_url, get_settings

# 嘗試載入 Graph 服務；如果沒有，後面會自動降級
try:
    from graph_service import fetch_employees_from_graph  # type: ignore[import]
except Exception:  # noqa: BLE001
    fetch_employees_from_graph = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging 設定
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("contacts")

# ---------------------------------------------------------------------------
# FastAPI 應用程式與中介層
# ---------------------------------------------------------------------------

app = FastAPI()

# CORS：目前允許全部來源，之後若要上正式環境可再收緊
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware：用於 OAuth/登入狀態（auth_routes 會使用）
settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# ---------------------------------------------------------------------------
# 資料庫引擎（目前主要用在 /health，或未來需要 DB 時使用）
# ---------------------------------------------------------------------------

engine = create_engine(
    get_database_url(settings),
    echo=False,
    connect_args={"charset": "utf8"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Pydantic 資料模型
# ---------------------------------------------------------------------------


class EmployeePublic(BaseModel):
    """對前端公開的員工基本資料結構。"""

    company_id: str
    employee_id: str
    name: str
    ename: Optional[str] = None
    email: Optional[str] = None
    campus: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    title: Optional[str] = None
    job: Optional[str] = None
    phone_no: Optional[str] = None
    mobile_phone: Optional[str] = None
    ext: Optional[str] = None
    status: Optional[str] = None


class TreeNode(BaseModel):
    """公司 → 校區 → 部門 → 員工 的樹狀節點。"""

    key: str
    label: str
    node_type: Literal["company", "campus", "dept", "employee"]
    children: List["TreeNode"] = Field(default_factory=list)
    data: Optional[EmployeePublic] = None


# Pydantic v2 需要呼叫 model_rebuild 處理自我參照
TreeNode.model_rebuild()

# ---------------------------------------------------------------------------
# Tree 組裝邏輯
# ---------------------------------------------------------------------------


def build_tree_from_employees(employees: List[EmployeePublic]) -> List[TreeNode]:
    """依照公司 → 校區 → 部門 → 員工 組成樹狀結構。"""

    company_node = TreeNode(
        key="company:KH",  # 之後若要多公司，可改成從設定讀取
        label="Company",
        node_type="company",
        children=[],
    )

    campus_map: dict[str, TreeNode] = {}
    dept_map: dict[tuple[str, str], TreeNode] = {}

    for employee in employees:
        # 校區
        campus_value = employee.campus or "Unknown"
        campus_key = f"campus:{campus_value}"
        if campus_key not in campus_map:
            campus_node = TreeNode(
                key=campus_key,
                label=campus_value,
                node_type="campus",
                children=[],
            )
            campus_map[campus_key] = campus_node
            company_node.children.append(campus_node)

        campus_node = campus_map[campus_key]

        # 部門（以 campus + dept_id 當 key）
        dept_id_value = employee.dept_id or "Unknown"
        dept_key = (campus_value, dept_id_value)
        if dept_key not in dept_map:
            dept_label = employee.dept_name or dept_id_value
            dept_node = TreeNode(
                key=f"dept:{campus_value}:{dept_id_value}",
                label=dept_label,
                node_type="dept",
                children=[],
            )
            dept_map[dept_key] = dept_node
            campus_node.children.append(dept_node)

        dept_node = dept_map[dept_key]

        # 員工節點
        employee_node = TreeNode(
            key=f"emp:{employee.employee_id}",
            label=employee.name,
            node_type="employee",
            children=[],
            data=employee,
        )
        dept_node.children.append(employee_node)

    return [company_node]


def find_node_by_key(nodes: List[TreeNode], key: str) -> Optional[TreeNode]:
    """在整棵樹中遞迴尋找指定 key 的節點。"""
    for node in nodes:
        if node.key == key:
            return node
        found = find_node_by_key(node.children, key)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# 員工資料來源：以 Graph 為主，必要時降級到 DB
# ---------------------------------------------------------------------------


def fetch_employees_from_db() -> List[EmployeePublic]:
    """從資料庫 Interinfo_Member 讀取在職員工（舊路線，當作備援）。"""
    db = SessionLocal()
    try:
        query = text(
            """
            SELECT
                CompanyID,
                EmployeeID,
                Name,
                EName,
                Email,
                Campus,
                DeptID,
                DeptName,
                Title,
                Job,
                PHONE_NO,
                MOBILE_PHONE,
                EXT,
                Status
            FROM dbo.Interinfo_Member
            WHERE Status = :status
            """
        )
        result = db.execute(query, {"status": "在職"})
        rows = result.fetchall()

        employees = [
            EmployeePublic(
                company_id=row[0],
                employee_id=row[1],
                name=row[2],
                ename=row[3],
                email=row[4],
                campus=row[5],
                dept_id=row[6],
                dept_name=row[7],
                title=row[8],
                job=row[9],
                phone_no=row[10],
                mobile_phone=row[11],
                ext=row[12],
                status=row[13],
            )
            for row in rows
        ]
        return employees
    finally:
        db.close()


def fetch_active_employees() -> List[EmployeePublic]:
    """
    取得目前要給通訊錄用的員工清單。

    現在版本：
    - 僅使用 Microsoft Graph
    - 若 Graph 失敗，直接丟錯，不再退回 DB
    """

    if fetch_employees_from_graph is None:  # type: ignore[truthy-function]
        # 表示根本沒有成功 import graph_service
        raise RuntimeError(
            "Graph integration not available. "
            "請確認 graph_service.py 存在，且裡面有 fetch_employees_from_graph()。"
        )

    try:
        logger.info("Fetching employees from Microsoft Graph (graph-only)...")
        raw_users = fetch_employees_from_graph()  # type: ignore[call-arg]

        employees: list[EmployeePublic] = []

        for u in raw_users:
            business_phones = u.get("businessPhones") or []
            phone = business_phones[0] if business_phones else None

            employees.append(
                EmployeePublic(
                    company_id="KH",  # 之後可以改成從設定讀
                    employee_id=u.get("id") or u.get("userPrincipalName") or "",
                    name=u.get("displayName") or "",
                    ename=None,
                    email=u.get("mail") or u.get("userPrincipalName"),
                    campus=u.get("officeLocation"),
                    dept_id=u.get("department"),
                    dept_name=u.get("department"),
                    title=u.get("jobTitle"),
                    job=u.get("jobTitle"),
                    phone_no=phone,
                    mobile_phone=u.get("mobilePhone"),
                    ext=None,
                    status="在職",
                )
            )

        logger.info("Graph returned %d employees", len(employees))
        if not employees:
            raise RuntimeError("Graph returned empty employees list")

        return employees

    except Exception as exc:  # noqa: BLE001
        # 這裡什麼錯都先直接炸出去，讓上層看到
        logger.exception("fetch_active_employees (Graph) failed")
        raise


# ---------------------------------------------------------------------------
# 登入檢查 dependency（只給 demo 用的 protected endpoint 用）
# ---------------------------------------------------------------------------


def get_current_user(request: Request):
    """
    從 session 中取得目前登入使用者資訊。

    若未登入：拋出 401（正式環境可改成 redirect 到 /auth/login）。
    """
    auth_data = request.session.get("auth")
    if not auth_data or not auth_data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return auth_data.get("user")


# ---------------------------------------------------------------------------
# 基本路由
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.get("/health")
async def health():
    """
    系統健康檢查：
    - DB：簡單執行 SELECT 1
    - Graph：如果有載入 graph_service，就嘗試呼叫一次
    """
    issues: list[str] = []

    # DB 檢查
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Health check DB failed: %s", exc)
        issues.append("db")
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass

    # Graph 檢查（若有）
    if fetch_employees_from_graph is not None:  # type: ignore[truthy-function]
        try:
            raw = fetch_employees_from_graph()  # type: ignore[call-arg]
            if not isinstance(raw, list):
                issues.append("graph-format")
        except Exception as exc:  # noqa: BLE001
            logger.error("Health check Graph failed: %s", exc)
            issues.append("graph")

    status_text = "ok" if not issues else "degraded"
    return {"status": status_text, "issues": issues}


# ---------------------------------------------------------------------------
# 通訊錄 API
# ---------------------------------------------------------------------------


@app.get("/contacts/tree")
async def get_contacts_tree():
    """
    公司通訊錄樹狀資料（公開）：
    - 目前只使用 Graph 當資料來源
    - 為了除錯，會把實際錯誤訊息透過 detail 回傳
    """
    import traceback

    try:
        employees = fetch_active_employees()
        tree = build_tree_from_employees(employees)
        return tree
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        logger.error("get_contacts_tree failed:\n%s", tb)
        # 直接把錯誤類型 + 訊息帶回去，方便你在瀏覽器看到真正原因
        raise HTTPException(
            status_code=500,
            detail=f"get_contacts_tree error: {exc.__class__.__name__}: {exc}",
        ) from exc
    
@app.get("/contacts/tree/{root_key}")
async def get_contacts_subtree(root_key: str):
    """
    從整棵樹中取出某個節點底下的子樹。
    """
    try:
        employees = fetch_active_employees()
        tree = build_tree_from_employees(employees)
        subtree = find_node_by_key(tree, root_key)
        return subtree or {}
    except Exception as exc:  # noqa: BLE001
        logger.error("get_contacts_subtree failed for %s: %s", root_key, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to load contacts subtree",
        ) from exc


@app.get("/contacts/employee")
async def get_employee(mail: str = Query(..., description="員工 Email")):
    """
    以 Email 查詢單一員工資訊。

    目前實作：
    - 先用 Graph 版本抓全部後在記憶體中比對（人數不多時可接受）
    - 若 Graph 失敗則用 DB 查詢。
    """
    # 先試 Graph
    if fetch_employees_from_graph is not None:  # type: ignore[truthy-function]
        try:
            employees = fetch_active_employees()
            for emp in employees:
                if emp.email and emp.email.lower() == mail.lower():
                    logger.info("get_employee (graph) %s -> %s", mail, emp.name)
                    return emp
        except Exception as exc:  # noqa: BLE001
            logger.error("get_employee via Graph failed: %s", exc)

    # 備援：DB 直接查
    db = SessionLocal()
    try:
        query = text(
            """
            SELECT
                CompanyID,
                EmployeeID,
                Name,
                EName,
                Email,
                Campus,
                DeptID,
                DeptName,
                Title,
                Job,
                PHONE_NO,
                MOBILE_PHONE,
                EXT,
                Status
            FROM dbo.Interinfo_Member
            WHERE Email = :email AND Status = :status
            """
        )
        row = db.execute(query, {"email": mail, "status": "在職"}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Employee not found")

        employee = EmployeePublic(
            company_id=row[0],
            employee_id=row[1],
            name=row[2],
            ename=row[3],
            email=row[4],
            campus=row[5],
            dept_id=row[6],
            dept_name=row[7],
            title=row[8],
            job=row[9],
            phone_no=row[10],
            mobile_phone=row[11],
            ext=row[12],
            status=row[13],
        )

        logger.info("get_employee (db) %s -> %s", mail, employee.name)
        return employee
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("get_employee failed for %s: %s", mail, exc)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from exc
    finally:
        db.close()


@app.get("/contacts/tree/protected-example")
async def get_protected_contacts_tree(current_user=Depends(get_current_user)):
    """
    示範用「需登入」的受保護 API：
    - 呼叫前需先完成 /auth/login 流程（SessionMiddleware 會存放 user）。
    """
    try:
        employees = fetch_active_employees()
        tree = build_tree_from_employees(employees)
        return {"current_user": current_user, "tree": tree}
    except Exception as exc:  # noqa: BLE001
        logger.error("get_protected_contacts_tree failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to load contacts tree",
        ) from exc


# ---------------------------------------------------------------------------
# 靜態頁面與 manifest
# ---------------------------------------------------------------------------


@app.get("/contacts")
async def contacts_page():
    """Outlook 通訊錄 Task Pane 入口頁面。"""
    return FileResponse("static/contacts.html")


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    """Outlook Add-in manifest（提供給 OWA / Desktop sideload 用）。"""
    return FileResponse("static/optimized-manifest.xml")


# 掛載靜態檔案目錄（CSS / JS / 圖示）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 掛載 OAuth / 登入相關路由（/auth/login, /auth/callback, ...）
app.include_router(auth_router)
