# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json

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
    children: List['TreeNode'] = []


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


@app.get("/contacts/tree")
async def get_contacts_tree():
    try:
        db = SessionLocal()

        # 查询所有联系人
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()

        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]

        # 构建树状结构
        tree = build_tree(contacts)

        db.close()
        # 直接返回，让FastAPI处理序列化
        return tree
    except Exception as e:
        return {"error": str(e)}


@app.get("/contacts/tree/{root_name}")
async def get_contacts_subtree(root_name: str):
    try:
        db = SessionLocal()

        # 查询所有联系人
        result = db.execute(text("SELECT name, parent, mail FROM addresslist"))
        rows = result.fetchall()

        contacts = [Contact(name=row[0], parent=row[1], mail=row[2]) for row in rows]

        # 构建子树
        subtree = build_tree(contacts, root_name)

        db.close()
        return subtree[0] if subtree else {}
    except Exception as e:
        return {"error": str(e)}


@app.get("/contacts")
async def contacts_page():
    return FileResponse('./static/contacts.html')


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    return FileResponse('./static/optimized-manifest.xml')



# 挂载静态文件目录（放在所有路由定义之后）
app.mount("/static", StaticFiles(directory="static"), name="static")