# main.py
import logging
import urllib.parse
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from auth_routes import router as auth_router
from config import get_settings

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

# 資料庫連線配置
DB_CONFIG = {
    "server": "qs db01-test",  # 或實際實例名稱，例如 'qs db01-test\\SQLEXPRESS'
    "database": "address",
    "username": "KCISweb_user",
    "password": "0xeYzpQJF9",
}


# 建立資料庫 URL
def get_database_url():
    password_encoded = urllib.parse.quote_plus(DB_CONFIG["password"])
    return (
        f"mssql+pymssql://{DB_CONFIG['username']}:{password_encoded}"
        f"@{DB_CONFIG['server']}/{DB_CONFIG['database']}"
    )


# 建立引擎與 Session
engine = create_engine(get_database_url(), echo=False, connect_args={"charset": "utf8"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Contact(BaseModel):
    name: str
    parent: Optional[str] = None
    mail: str


class TreeNode(BaseModel):
    name: str
    mail: str
    children: List["TreeNode"] = Field(default_factory=list)


TreeNode.update_forward_refs()


def build_tree(contacts: List[Contact], root_name: str = None) -> List[TreeNode]:
    # 建立節點字典
    node_dict = {}
    for contact in contacts:
        node_dict[contact.name] = TreeNode(
            name=contact.name,
            mail=contact.mail,
            children=[],
        )

    # 建立樹狀結構
    roots = []
    for contact in contacts:
        if contact.parent is None or contact.parent == "":
            roots.append(node_dict[contact.name])
        else:
            if contact.parent in node_dict:
                node_dict[contact.parent].children.append(node_dict[contact.name])

    return roots if not root_name else [node_dict[root_name]] if root_name in node_dict else []


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
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()
        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]
        tree = build_tree(contacts)
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
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()
        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]
        subtree = build_tree(contacts, root_name)
        return subtree[0] if subtree else {}
    except Exception as e:
        logger.error(f"get_contacts_subtree failed for {root_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load contacts subtree")
    finally:
        db.close()


@app.get("/contacts/employee")
async def get_employee(mail: str = Query(..., description="員工 Email")):
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT name, parent, mail FROM addresslist WHERE mail = :mail"),
            {"mail": mail},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Employee not found")

        logger.info(f"get_employee: {mail} -> {row[0]}")
        return {
            "name": row[0],
            "parent": row[1],
            "mail": row[2],
        }
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
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()
        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]
        tree = build_tree(contacts)
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
