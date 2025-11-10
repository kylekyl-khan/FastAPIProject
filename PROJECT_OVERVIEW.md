# PROJECT_OVERVIEW.md

## 🧩 公司通訊錄系統（FastAPI × Outlook Web Add-in）

### 一、專案願景與目標

**目標**：建置一個「公司通訊錄」Web 應用，並整合至 **Outlook Web Add-in**。  
使用者可依組織層級（集團 → 校區 → 處室 → 分組）**瀏覽樹狀結構**、查詢人員資料，並可直接將人員加入 Outlook 的收件人欄位（TO / CC / BCC）。

**用途**：  
- 內部通訊錄與組織架構可視化  
- 提供 Outlook Web Add-in 即時插入收件人功能  
- 支援 Demo / PoC 階段可直接展示互動與前後端整合能力  

---

### 二、系統架構總覽

| 層級 | 技術 / 工具 | 功能說明 |
|------|--------------|----------|
| **前端** | HTML + CSS + JavaScript + Office.js | Outlook Web Add-in UI，樹狀通訊錄操作介面 |
| **後端** | FastAPI | 提供通訊錄 API 與靜態頁面 |
| **資料庫** | Microsoft SQL Server (Docker) | 儲存通訊錄資料 |
| **ORM** | SQLAlchemy | 從資料表讀取平面結構、轉換為樹狀 JSON |
| **部署** | Uvicorn + HTTPS (自簽憑證) | 運行於 Windows 本機虛擬開發環境（venv） |
| **開發工具** | VSCode + GitHub + Minikube（未來 K8s 部署） | 版本管理、雲端開發、虛擬環境隔離 |

---

### 三、後端設計

#### 🔹 框架與環境

- **FastAPI**
- **Uvicorn**（本機開發使用 127.0.0.1:9000）
- **虛擬環境 (venv)** 管理依賴
- **Docker SQL Server**（mcr.microsoft.com/mssql/server:2022-latest）

#### 🔹 資料庫設定

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "address",
    "username": "sa",
    "password": "itpower1!"
}
```

**表結構：addresslist**

| 欄位 | 類型 | 說明 |
|------|------|------|
| name | nvarchar | 單位或人員名稱 |
| parent | nvarchar | 上層節點名稱 |
| mail | nvarchar | 電子郵件地址（人員節點才有值） |

#### 🔹 資料模型

```python
class Contact(BaseModel):
    name: str
    parent: Optional[str] = None
    mail: str
```

#### 🔹 API 路由

| 路徑 | 方法 | 說明 |
|------|------|------|
| `/contacts/tree` | GET | 取得頂層節點（例如康軒文教、各校區） |
| `/contacts/tree/{root_or_node}` | GET | 取得指定節點的樹狀結構，支援 lazy loading |
| `/contacts/group/{group_id}/members` | GET | 取得分組成員（可合併於 `/contacts/tree/{id}` 回傳） |
| `/contacts` | GET | 前端主頁（contacts.html） |

#### 🔹 回傳 JSON 結構（示意）

```json
{
  "name": "康軒文教",
  "type": "root",
  "has_children": true,
  "children": [
    {
      "name": "青山校區",
      "type": "branch",
      "has_children": true
    },
    {
      "name": "總務處",
      "type": "department",
      "has_children": false,
      "members": [
        { "name": "王小明", "title": "組長", "mail": "ming@kanghsuan.com" }
      ]
    }
  ]
}
```

---

### 四、前端 / Outlook Add-in 架構

#### 🔹 技術與檔案結構

- `/static/contacts.html`  
- `/static/script.js`  
- `/static/style.css`

#### 🔹 架構概念（單頁應用 SPA）

| 模組 | 職責 |
|------|------|
| **ContactManager** | 中樞控制：載入 root、切換組織樹、管理搜尋與狀態 |
| **ApiClient** | 封裝 `/contacts/tree` 與 `/contacts/tree/{id}` 呼叫 |
| **TreeView** | 負責樹狀 DOM 建立與 lazy loading |
| **MemberList** | 顯示成員清單與 +TO / +CC / +BCC 按鈕 |
| **OutlookIntegration** | 與 Office.js 互動，管理 Outlook 收件人新增 |
| **ToastManager** | 顯示成功/錯誤通知 |
| **Modal / Overlay** | 預留掛點顯示詳細資料或警告視窗 |

---

### 五、主要使用情境（UI 流程）

#### 🏠 首頁 Root View

- 顯示頂層單位卡片（康軒文教、青山校區、秀岡校區、新竹校區、高雄校區、林口校區）。
- 點擊卡片 → 呼叫 `/contacts/tree/{root}` → 切換至組織樹畫面。
- 搜尋列預留（未來串接 API / 前端 filter）。

#### 🌳 組織視圖 Org View

- 左側：TreeView，展開節點時呼叫 `/contacts/tree/{node}`。
- 右側：節點資訊 + 成員列表。
- 成員節點顯示表格（姓名、職稱、Email、電話）。
- 每個成員提供 `+TO / +CC / +BCC` 按鈕。
- Outlook 狀態：
  - 若存在 `Office.context.mailbox.item` → 啟用按鈕。
  - 若無 → 顯示「非 Outlook 環境」警告 Toast。

---

### 六、開發與執行環境

| 項目 | 說明 |
|------|------|
| 系統 | Windows 11 |
| Python | 3.11+（虛擬環境） |
| Docker | SQL Server 容器 |
| 前端 | 靜態檔案 + Office.js |
| 執行 | `python -m uvicorn main:app --host 127.0.0.1 --port 9000` |

---

### 七、目前開發進度

✅ 已完成：
- 後端 FastAPI 結構與 DB 模型  
- `/contacts/tree` 與 `/contacts/tree/{root}` API  
- 本機虛擬環境（venv + Docker SQL Server）  
- 前端 SPA 架構與 Outlook.js 整合雛型  

🚧 進行中：
- 調整 `build_tree()` 回傳格式以對應前端 TreeView  
- 加入 `/contacts/group/{group_id}/members` API  
- 完善成員屬性（職稱、電話、Email）  

🧭 下一步：
1. 設計統一的 JSON schema（含 type / has_children / members）
2. 串接搜尋功能 `/contacts/search`
3. 建立 health-check 與部署文件 (`DEPLOY_K8S.md`)
4. 將前端整合為 Outlook Web Add-in manifest

---

### 八、部署與遷移規劃

| 環境 | 技術 | 備註 |
|------|------|------|
| 開發環境 | venv + Docker SQL | 本機 Windows |
| 測試環境 | Minikube (K8s) | 模擬多服務部署 |
| 正式環境 | Kubernetes + HTTPS 憑證 | 實體或雲端伺服器部署 |
| CI/CD | GitHub Actions | 自動打包與部署 |

---

© 2025 FastAPI Outlook Add-in Project Overview.
