# FastAPI Project - Windows 虛擬開發環境安裝與最新 Demo 指南

本指南協助你在 Windows 11 本機虛擬環境完成安裝，並依照最新流程演示通訊錄服務。資料來源已切換為 **DB_Mis_Admin.dbo.Interinfo_Member**，不再建立舊的 `address` / `addresslist` 範例表。

---

## 🧩 一、環境安裝 (INSTALL)

### 1. Python 與 Git 準備

1. 安裝 **Python 3.11+**（勾選 Add Python to PATH）。
2. 安裝 **Git for Windows**。

確認版本：
```powershell
python --version
git --version
```

### 2. 建立專案目錄並 Clone Repo

```powershell
cd $env:USERPROFILE\Desktop
mkdir KC
cd KC
git clone https://github.com/kylekyl-khan/FastAPIProject.git
cd FastAPIProject
```

### 3. 建立與啟用虛擬環境

```powershell
python -m venv venv
.\venv\Scripts\activate
```

看到 `(venv)` 代表啟用成功。

### 4. 安裝套件依賴

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. 設定資料庫與環境變數

建立 `.env` 檔（可複製 `.env.example`）並填入實際 SQL Server 帳密：

```env
DB_SERVER=db01_test      # 依實際主機調整
DB_NAME=DB_Mis_Admin
DB_USERNAME=your-db-user
DB_PASSWORD=your-strong-password

SECRET_KEY=some-random-string-for-session
# 若需要 Entra SSO，加入 AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET / AZURE_REDIRECT_URI 等
```

> 專案會直接連線到 `DB_Mis_Admin.dbo.Interinfo_Member`，請確認帳號具備讀取權限。若要在本機搭建測試 SQL Server，可自行以 Docker 啟動，但不需要建立舊的 addresslist 範例資料。

---

## ⚙️ 二、最新 Demo 流程 (DEMO)

### Demo Level 1：純後端 + 瀏覽器

1. 啟動 API Server：
   ```powershell
   python -m uvicorn main:app --reload
   ```
2. 驗證服務：
   - http://127.0.0.1:8000/contacts  →  觀看通訊錄 UI（資料來自 Interinfo_Member）
   - http://127.0.0.1:8000/docs      →  查看 API 說明，特別是 `/contacts/tree`

### Demo Level 2：HTTPS + Outlook Add-in + Entra SSO

1. 產生並安裝自簽憑證：
   ```powershell
   python generate_cert.py
   # 需要安裝根憑證時，可執行 install_cert.ps1
   ```
2. 啟動 HTTPS 服務：
   ```powershell
   python https_server.py
   ```
3. 建立 Microsoft Entra App registration：
   - Redirect URI：`https://127.0.0.1:8443/auth/callback`
   - 將 AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET / AZURE_REDIRECT_URI 寫入 `.env`
4. 在 Outlook Web (OWA) 以 `https://127.0.0.1:8443/optimized-manifest.xml` sideload Add-in。
5. 示範流程：
   - 開啟郵件 → 啟用 Add-in → 載入 `contacts.html`
   - 未登入時點「登入」走 Entra 流程
   - 成功登入後顯示來自 `DB_Mis_Admin.dbo.Interinfo_Member` 的組織樹與員工聯絡資訊

---

## 🧱 三、後續部署建議

- 正式環境請改用公司內部 SQL Server 主機與正式帳號，環境變數或 Secret 管理密碼。
- 服務綁定 0.0.0.0 並搭配反向代理 / 防火牆設定。
- 依需求啟用 HTTPS、CORS 與監控日誌。

---

## 📚 四、常用指令摘要

| 操作 | 指令 |
|------|------|
| 啟用虛擬環境 | `.\venv\Scripts\activate` |
| 安裝套件 | `python -m pip install -r requirements.txt` |
| 啟動 API（HTTP） | `python -m uvicorn main:app --reload` |
| 啟動 API（HTTPS） | `python https_server.py` |
| 停止 API | `Ctrl + C` |

© 2025 FastAPIProject Setup Guide. For internal use only.
