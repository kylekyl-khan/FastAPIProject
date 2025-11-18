from __future__ import annotations

"""核心資料模型與樹狀結構工具。"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from config import get_settings


class EmployeePublic(BaseModel):
    """對外公開的員工聯絡資訊。"""

    company_id: str = Field(description="公司代碼")
    employee_id: str = Field(description="員工編號")
    name: str = Field(description="員工姓名")
    ename: Optional[str] = Field(default=None, description="英文姓名")
    email: Optional[str] = Field(default=None, description="電子郵件")
    campus: Optional[str] = Field(default=None, description="校區名稱")
    dept_id: Optional[str] = Field(default=None, description="部門代碼")
    dept_name: Optional[str] = Field(default=None, description="部門名稱")
    title: Optional[str] = Field(default=None, description="職稱")
    job: Optional[str] = Field(default=None, description="職務說明")
    phone_no: Optional[str] = Field(default=None, description="公司電話")
    mobile_phone: Optional[str] = Field(default=None, description="手機號碼")
    ext: Optional[str] = Field(default=None, description="分機")
    status: Optional[str] = Field(default=None, description="狀態")


class TreeNode(BaseModel):
    """通訊錄樹狀節點。"""

    key: str = Field(description="節點唯一識別值")
    label: str = Field(description="節點顯示文字")
    node_type: Literal["company", "campus", "dept", "employee"]
    children: list["TreeNode"] = Field(default_factory=list, description="子節點清單")
    data: Optional[EmployeePublic] = Field(default=None, description="員工資料，僅員工節點使用")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


TreeNode.model_rebuild()


def build_tree_from_employees(employees: list[EmployeePublic]) -> list[TreeNode]:
    """組成公司 → 校區 → 部門 → 人員的樹狀結構。"""

    settings = get_settings()
    company_label = settings.COMPANY_NAME or "公司"
    company_key = f"company:{settings.COMPANY_ID or 'company'}"
    company_node = TreeNode(
        key=company_key,
        label=company_label,
        node_type="company",
        children=[],
    )

    campus_nodes: dict[str, TreeNode] = {}
    dept_nodes: dict[tuple[str, str], TreeNode] = {}

    for employee in employees:
        campus_value = (employee.campus or "Unknown").strip() or "Unknown"
        campus_key = f"campus:{campus_value}"
        if campus_key not in campus_nodes:
            campus_nodes[campus_key] = TreeNode(
                key=campus_key,
                label=campus_value,
                node_type="campus",
                children=[],
            )
            company_node.children.append(campus_nodes[campus_key])

        dept_value = employee.dept_id or employee.dept_name or "Unknown"
        dept_key = (campus_key, dept_value)
        if dept_key not in dept_nodes:
            dept_label = employee.dept_name or dept_value
            dept_nodes[dept_key] = TreeNode(
                key=f"dept:{campus_value}:{dept_value}",
                label=dept_label,
                node_type="dept",
                children=[],
            )
            campus_nodes[campus_key].children.append(dept_nodes[dept_key])

        employee_node = TreeNode(
            key=f"emp:{employee.employee_id}",
            label=employee.name or employee.email or employee.employee_id,
            node_type="employee",
            children=[],
            data=employee,
        )
        dept_nodes[dept_key].children.append(employee_node)

    return [company_node]


def find_node_by_key(nodes: list[TreeNode], key: str) -> TreeNode | None:
    """遞迴搜尋整棵樹並回傳指定 key 的節點。"""

    for node in nodes:
        if node.key == key:
            return node
        found = find_node_by_key(node.children, key)
        if found:
            return found
    return None
