# FastAPI 通訊錄服務本地部署與 Demo 教程

本文件說明如何在本機快速啟動並展示專案。後端會直接連線到公司的 **DB_Mis_Admin.dbo.Interinfo_Member** 表，無需再建立舊的 `address` / `addresslist` 範例資料庫。

---

## 1. 準備開發環境

1. 安裝 **Python 3.10 以上** 與 **Git**。
2. 若需在本機啟動 SQL Server 供測試，可使用 Docker Desktop，但正式 Demo 會直接連到既有的 `DB_Mis_Admin`。

---

## 2. 取得程式碼並安裝相依套件

```bash
git clone https://github.com/kylekyl-khan/FastAPIProject
cd FastAPIProject
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 設定資料庫與環境變數

專案使用環境變數描述 SQL Server 連線資訊。請在專案根目錄建立 `.env`（可參考 `.env.example`）：

```env
DB_SERVER=db01_test          # 實際 SQL Server 主機，預設示例值
DB_NAME=DB_Mis_Admin         # 目標資料庫名稱
DB_USERNAME=your-db-user
DB_PASSWORD=your-strong-password

SECRET_KEY=some-random-string-for-session
# 若要啟用 Entra SSO，請加入 AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET 等設定
```

> 本機 Demo 可連到測試環境（如 `db01_test`），正式環境請改成公司內部 SQL Server，並確保帳號具備讀取 `dbo.Interinfo_Member` 權限。

---

## 4. Demo 流程

### Demo Level 1：純後端 + 瀏覽器

1. 啟動 FastAPI（確保虛擬環境已啟用）：
   ```bash
   uvicorn main:app --reload
   ```
2. 瀏覽器驗證：
   - http://127.0.0.1:8000/contacts  →  檢視通訊錄 UI（資料來源：`Interinfo_Member`）
   - http://127.0.0.1:8000/docs      →  查看 API 文件（`/contacts/tree` 等）

### Demo Level 2：HTTPS + Outlook Add-in + Entra SSO

1. 建立自簽憑證並安裝：
   ```bash
   python generate_cert.py
   # Windows 可執行 install_cert.ps1 安裝根憑證
   ```
2. 啟動 HTTPS 伺服器：
   ```bash
   python https_server.py
   ```
3. 在 Microsoft Entra 建立 App registration，Redirect URI 設定為 `https://127.0.0.1:8443/auth/callback`，並將下列值寫入 `.env`：
   - AZURE_CLIENT_ID
   - AZURE_TENANT_ID
   - AZURE_CLIENT_SECRET
   - AZURE_REDIRECT_URI（預設即可）
4. 在 Outlook Web (OWA) 以 URL `https://127.0.0.1:8443/optimized-manifest.xml` sideload Add-in。
5. Demo 步驟：
   - 在 OWA 開啟郵件 → 啟用 Add-in → 載入 `contacts.html`
   - 若未登入，點「登入」並完成 Entra 流程
   - 登入後即可看到實際從 `DB_Mis_Admin.dbo.Interinfo_Member` 取得的組織樹與員工聯絡資訊

---

## 5. 常見檢查點

- 確認 `.env` 中的 DB 參數正確且能連線到 `DB_Mis_Admin`。
- `uvicorn` 啟動時若出現資料庫錯誤，請檢查帳密與網路連線。
- Outlook Add-in 若無法載入，請確認憑證已安裝且使用 HTTPS 位址。

完成以上設定，即可使用最新的資料來源與 Demo 流程展示通訊錄服務。
