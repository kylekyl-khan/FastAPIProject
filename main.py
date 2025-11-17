"""主應用程式進入點。"""

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("contacts")

app = FastAPI()

# CORS 中間件（保留原本設定）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware：用於存放登入相關資訊
settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# 建立引擎與 Session
engine = create_engine(
    get_database_url(settings), echo=False, connect_args={"charset": "utf8"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class EmployeePublic(BaseModel):
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
    key: str
    label: str
    node_type: Literal["company", "campus", "dept", "employee"]
    children: List["TreeNode"] = Field(default_factory=list)
    data: Optional[EmployeePublic] = None


TreeNode.update_forward_refs(EmployeePublic=EmployeePublic, TreeNode="TreeNode")


def build_tree_from_employees(employees: List[EmployeePublic]) -> List[TreeNode]:
    """依照公司→校區→部門→員工的階層組成樹狀資料。"""

    company_node = TreeNode(
        key="company:KH",
        label="Company",
        node_type="company",
        children=[],
    )

    campus_map: dict[str, TreeNode] = {}
    dept_map: dict[tuple[str, str], TreeNode] = {}

    for employee in employees:
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
    for node in nodes:
        if node.key == key:
            return node
        found = find_node_by_key(node.children, key)
        if found:
            return found
    return None


def fetch_active_employees(db) -> List[EmployeePublic]:
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


# -----------------------
# 登入檢查 dependency
# -----------------------
def get_current_user(request: Request):
    """
    從 session 中取得目前登入使用者資訊。
    - 若未登入：拋出 401（也可以改成 redirect 到 /auth/login）
    """
    auth_data = request.session.get("auth")
    if not auth_data or not auth_data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return auth_data.get("user")


# 根路由
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.get("/health")
async def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="DB connection failed")
    finally:
        db.close()


@app.get("/contacts/tree")
async def get_contacts_tree():
    db = SessionLocal()
    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        return tree
    except Exception as e:
        logger.error(f"get_contacts_tree failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load contacts tree")
    finally:
        db.close()


@app.get("/contacts/tree/{root_name}")
async def get_contacts_subtree(root_name: str):
    db = SessionLocal()
    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        subtree = find_node_by_key(tree, root_name)
        return subtree or {}
    except Exception as e:
        logger.error(f"get_contacts_subtree failed for {root_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load contacts subtree")
    finally:
        db.close()


@app.get("/contacts/employee")
async def get_employee(mail: str = Query(..., description="員工 Email")):
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

        logger.info(f"get_employee: {mail} -> {employee.name}")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_employee failed for {mail}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


# 示範：受保護的樹狀查詢 API（需要登入）
@app.get("/contacts/tree/protected-example")
async def get_protected_contacts_tree(current_user=Depends(get_current_user)):
    """
    示範用受保護 API：
    - 呼叫前需先完成 /auth/login 流程。
    - current_user 為 session 內的 user info。
    """
    db = SessionLocal()
    try:
        employees = fetch_active_employees(db)
        tree = build_tree_from_employees(employees)
        return {
            "current_user": current_user,
            "tree": tree,
        }
    except Exception as e:
        logger.error(f"get_protected_contacts_tree failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load contacts tree")
    finally:
        db.close()


@app.get("/contacts")
async def contacts_page():
    return FileResponse("./static/contacts.html")


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    return FileResponse("./static/optimized-manifest.xml")


# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="static"), name="static")

# 掛載 auth router
app.include_router(auth_router)
