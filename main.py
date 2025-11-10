# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

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


class DemoPerson(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    email: str
    organization_id: int


class DemoOrgNode(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List['DemoOrgNode'] = Field(default_factory=list)
    people: List[DemoPerson] = Field(default_factory=list)


DemoOrgNode.update_forward_refs()


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


DEMO_DB_URL = "sqlite:///./demo_org.db"
demo_engine = create_engine(
    DEMO_DB_URL, echo=False, connect_args={"check_same_thread": False}
)
DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)


def init_demo_db() -> None:
    with demo_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    FOREIGN KEY(parent_id) REFERENCES organizations(id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    title TEXT,
                    email TEXT NOT NULL,
                    organization_id INTEGER NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(id)
                )
                """
            )
        )

        existing_orgs = conn.execute(
            text("SELECT COUNT(*) FROM organizations")
        ).scalar()

        if not existing_orgs:
            conn.execute(
                text(
                    "INSERT INTO organizations (id, name, parent_id) VALUES (:id, :name, :parent_id)"
                ),
                [
                    {"id": 1, "name": "總公司", "parent_id": None},
                    {"id": 2, "name": "北區事業部", "parent_id": 1},
                    {"id": 3, "name": "南區事業部", "parent_id": 1},
                    {"id": 4, "name": "企業方案處", "parent_id": 2},
                    {"id": 5, "name": "客戶成功處", "parent_id": 2},
                    {"id": 6, "name": "雲端研發中心", "parent_id": 3},
                    {"id": 7, "name": "營運支援處", "parent_id": 3},
                ],
            )
            conn.execute(
                text(
                    "INSERT INTO people (id, name, title, email, organization_id) VALUES (:id, :name, :title, :email, :organization_id)"
                ),
                [
                    {
                        "id": 1,
                        "name": "林雅婷",
                        "title": "總經理",
                        "email": "lin.yating@example.com",
                        "organization_id": 1,
                    },
                    {
                        "id": 2,
                        "name": "陳建宏",
                        "title": "北區事業部副總",
                        "email": "chen.jianhong@example.com",
                        "organization_id": 2,
                    },
                    {
                        "id": 3,
                        "name": "黃淑芬",
                        "title": "企業方案處處長",
                        "email": "huang.shufen@example.com",
                        "organization_id": 4,
                    },
                    {
                        "id": 4,
                        "name": "張少強",
                        "title": "企業方案顧問",
                        "email": "zhang.shaoqiang@example.com",
                        "organization_id": 4,
                    },
                    {
                        "id": 5,
                        "name": "王怡文",
                        "title": "客戶成功經理",
                        "email": "wang.yiwen@example.com",
                        "organization_id": 5,
                    },
                    {
                        "id": 6,
                        "name": "周家豪",
                        "title": "客戶成功專員",
                        "email": "zhou.jiahao@example.com",
                        "organization_id": 5,
                    },
                    {
                        "id": 7,
                        "name": "吳惠敏",
                        "title": "南區事業部副總",
                        "email": "wu.huimin@example.com",
                        "organization_id": 3,
                    },
                    {
                        "id": 8,
                        "name": "鄭翔宇",
                        "title": "雲端研發中心經理",
                        "email": "zheng.xiangyu@example.com",
                        "organization_id": 6,
                    },
                    {
                        "id": 9,
                        "name": "蔡欣怡",
                        "title": "資深工程師",
                        "email": "cai.xinyi@example.com",
                        "organization_id": 6,
                    },
                    {
                        "id": 10,
                        "name": "高子豪",
                        "title": "營運支援處處長",
                        "email": "gao.zihao@example.com",
                        "organization_id": 7,
                    },
                    {
                        "id": 11,
                        "name": "賴怡潔",
                        "title": "營運分析師",
                        "email": "lai.yijie@example.com",
                        "organization_id": 7,
                    },
                ],
            )


def build_demo_tree() -> List[DemoOrgNode]:
    session = DemoSessionLocal()
    try:
        org_rows = session.execute(
            text("SELECT id, name, parent_id FROM organizations")
        ).mappings().all()
        people_rows = session.execute(
            text(
                "SELECT id, name, title, email, organization_id FROM people"
            )
        ).mappings().all()

        org_nodes: Dict[int, DemoOrgNode] = {}
        for row in org_rows:
            org_nodes[row["id"]] = DemoOrgNode(
                id=row["id"],
                name=row["name"],
                parent_id=row["parent_id"],
                children=[],
                people=[],
            )

        for person in people_rows:
            org_id = person["organization_id"]
            if org_id in org_nodes:
                org_nodes[org_id].people.append(
                    DemoPerson(
                        id=person["id"],
                        name=person["name"],
                        title=person["title"],
                        email=person["email"],
                        organization_id=org_id,
                    )
                )

        roots: List[DemoOrgNode] = []
        for node in org_nodes.values():
            if node.parent_id and node.parent_id in org_nodes:
                org_nodes[node.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots
    finally:
        session.close()


@app.on_event("startup")
async def on_startup() -> None:
    init_demo_db()


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


@app.get("/demo")
async def demo_page():
    return FileResponse('./static/demo.html')


@app.get("/demo/organizations/tree", response_model=List[DemoOrgNode])
async def demo_organization_tree():
    return build_demo_tree()


@app.get("/demo/organizations/{org_id}", response_model=DemoOrgNode)
async def demo_organization(org_id: int):
    tree = build_demo_tree()
    node_map: Dict[int, DemoOrgNode] = {}

    def traverse(node: DemoOrgNode) -> None:
        node_map[node.id] = node
        for child in node.children:
            traverse(child)

    for root_node in tree:
        traverse(root_node)

    if org_id not in node_map:
        raise HTTPException(status_code=404, detail="Organization not found")

    return node_map[org_id]


@app.get("/optimized-manifest.xml")
async def optimized_manifest():
    return FileResponse('./static/optimized-manifest.xml')



# 挂载静态文件目录（放在所有路由定义之后）
app.mount("/static", StaticFiles(directory="static"), name="static")
