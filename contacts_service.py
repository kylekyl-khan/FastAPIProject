"""
此檔案負責通訊錄資料的存取與樹狀結構建構邏輯。
包含從資料庫讀取員工資料、組合公司層級樹狀節點、以及節點查找工具。
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from config import get_settings
from schemas import EmployeePublic, TreeNode

SETTINGS = get_settings()

# 使用模型重建前向參照
TreeNode.model_rebuild()


def fetch_active_employees(db_session: Session) -> list[EmployeePublic]:
    """
    從 Interinfo_Member 資料表讀取在職員工資料並轉換為 EmployeePublic 清單。
    """

    query = text(
        """
        SELECT
            CompanyID AS company_id,
            EmployeeID AS employee_id,
            Name AS name,
            EName AS ename,
            Email AS email,
            Campus AS campus,
            DeptID AS dept_id,
            DeptName AS dept_name,
            Title AS title,
            Job AS job,
            PHONE_NO AS phone_no,
            MOBILE_PHONE AS mobile_phone,
            EXT AS ext,
            Status AS status
        FROM dbo.Interinfo_Member
        WHERE Status = :status
        """
    )

    result = db_session.execute(query, {"status": SETTINGS.DB_ACTIVE_STATUS})
    employees: list[EmployeePublic] = [EmployeePublic(**row._mapping) for row in result]
    return employees


def fetch_employee_by_email(db_session: Session, email: str) -> EmployeePublic | None:
    """
    依據電子郵件查詢單一員工資料，若無符合則回傳 None。
    """

    query = text(
        """
        SELECT
            CompanyID AS company_id,
            EmployeeID AS employee_id,
            Name AS name,
            EName AS ename,
            Email AS email,
            Campus AS campus,
            DeptID AS dept_id,
            DeptName AS dept_name,
            Title AS title,
            Job AS job,
            PHONE_NO AS phone_no,
            MOBILE_PHONE AS mobile_phone,
            EXT AS ext,
            Status AS status
        FROM dbo.Interinfo_Member
        WHERE Email = :email AND Status = :status
        """
    )

    result = db_session.execute(query, {"email": email, "status": SETTINGS.DB_ACTIVE_STATUS})
    row = result.first()
    if not row:
        return None
    return EmployeePublic(**row._mapping)


def build_tree_from_employees(employees: list[EmployeePublic]) -> list[TreeNode]:
    """
    依照公司 → 校區 → 部門 → 員工階層組合樹狀資料，供前端顯示。
    """

    company_node = TreeNode(key="company:KH", label="Company", node_type="company", children=[])
    campus_nodes: dict[str, TreeNode] = {}
    dept_nodes: dict[tuple[str, str], TreeNode] = {}

    for employee in employees:
        campus_value = employee.campus or "Unknown"
        campus_key = f"campus:{campus_value}"
        if campus_key not in campus_nodes:
            campus_nodes[campus_key] = TreeNode(
                key=campus_key,
                label=campus_value,
                node_type="campus",
                children=[],
            )
            company_node.children.append(campus_nodes[campus_key])

        dept_id_value = employee.dept_id or "Unknown"
        dept_key = (campus_value, dept_id_value)
        if dept_key not in dept_nodes:
            dept_label = employee.dept_name or dept_id_value
            dept_nodes[dept_key] = TreeNode(
                key=f"dept:{campus_value}:{dept_id_value}",
                label=dept_label,
                node_type="dept",
                children=[],
            )
            campus_nodes[campus_key].children.append(dept_nodes[dept_key])

        employee_node = TreeNode(
            key=f"emp:{employee.employee_id}",
            label=employee.name,
            node_type="employee",
            children=[],
            data=employee,
        )
        dept_nodes[dept_key].children.append(employee_node)

    return [company_node]


def find_node_by_key(nodes: list[TreeNode], key: str) -> TreeNode | None:
    """
    在樹狀節點清單中遞迴搜尋指定 key，若找不到則回傳 None。
    """

    for node in nodes:
        if node.key == key:
            return node
        found = find_node_by_key(node.children, key)
        if found:
            return found
    return None
