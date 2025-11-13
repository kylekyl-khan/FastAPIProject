# main.py
import logging
import urllib.parse
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("contacts")


app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接配置
DB_CONFIG = {
    'server': 'localhost',
    'database': 'address',
    'username': 'sa',
    'password': 'itpower1!'
}


# 创建数据库连接URL
def get_database_url():
    password_encoded = urllib.parse.quote_plus(DB_CONFIG['password'])
    # 对于默认实例，不需要指定实例名
    return f"mssql+pymssql://{DB_CONFIG['username']}:{password_encoded}@{DB_CONFIG['server']}/{DB_CONFIG['database']}"


# 创建引擎和会话
engine = create_engine(get_database_url(), echo=False, connect_args={"charset": "utf8"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Contact(BaseModel):
    name: str
    parent: Optional[str] = None
    mail: str


class TreeNode(BaseModel):
    name: str
    mail: str
    children: List['TreeNode'] = Field(default_factory=list)


TreeNode.update_forward_refs()


def build_tree(contacts: List[Contact], root_name: str = None) -> List[TreeNode]:
    # 创建节点字典
    node_dict = {}
    for contact in contacts:
        node_dict[contact.name] = TreeNode(
            name=contact.name,
            mail=contact.mail,
            children=[]
        )

    # 构建树结构
    roots = []
    for contact in contacts:
        if contact.parent is None or contact.parent == "":
            roots.append(node_dict[contact.name])
        else:
            if contact.parent in node_dict:
                node_dict[contact.parent].children.append(node_dict[contact.name])

    return roots if not root_name else [node_dict[root_name]] if root_name in node_dict else []


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
        # 查询所有联系人
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()

        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]

        # 构建树状结构
        tree = build_tree(contacts)

        # 直接返回，让FastAPI处理序列化
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
        # 查询所有联系人
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()

        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]

        # 构建子树
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


@app.get("/contacts")
async def contacts_page():
    return FileResponse('./static/contacts.html')


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    return FileResponse('./static/optimized-manifest.xml')



# 挂载静态文件目录（放在所有路由定义之后）
app.mount("/static", StaticFiles(directory="static"), name="static")
