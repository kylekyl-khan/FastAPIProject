"""
此檔案定義 Pydantic 模型，負責描述通訊錄公開資訊與樹狀節點結構。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class EmployeePublic(BaseModel):
    """
    封裝對外公開的員工聯絡資訊，避免曝露敏感欄位。
    """

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
    """
    定義通訊錄樹狀節點結構，可代表公司、校區、部門或員工。
    """

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
