# FastAPI Project - Windows 虛擬開發環境安裝與示範指南

本文件整合安裝與示範操作說明，協助開發者在 **Windows 11 本機虛擬開發環境**（Local Dev Environment）中建立、啟動與演示專案。

---

## 🧩 一、環境安裝 (INSTALL)

### 1. Python 與 Git 準備

1. 安裝 **Python 3.11+**
   - 官方下載頁面：https://www.python.org/downloads/
   - 安裝時務必勾選 **Add Python to PATH**
   - 安裝完成後確認：
     ```powershell
     python --version
     ```

2. 安裝 **Git for Windows**
   - 官方下載：https://git-scm.com/download/win
   - 安裝後確認：
     ```powershell
     git --version
     ```

---

### 2. 建立專案目錄並 Clone Repo

```powershell
cd $env:USERPROFILE\Desktop
mkdir KC
cd KC
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>
```

---

### 3. 建立與啟用虛擬環境

```powershell
python -m venv venv
.env\Scriptsctivate
```

確認出現 `(venv)` 字樣即代表啟用成功。

---

### 4. 安裝套件依賴

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# 或
python -m pip install fastapi uvicorn sqlalchemy pymssql pydantic
```

---

### 5. 啟動 Docker SQL Server（開發用）

1. 安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，啟用 WSL2 引擎。
2. 啟動 SQL Server 容器：

```powershell
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=itpower1!" -p 1433:1433 --name sqlserver -d mcr.microsoft.com/mssql/server:2022-latest
docker ps
```

確認 `sqlserver` 狀態為 `Up`。

---

### 6. 建立測試資料庫

使用 `sqlcmd` 或其他管理工具建立：

```sql
CREATE DATABASE address;
GO
USE address;
GO
CREATE TABLE addresslist (
    name NVARCHAR(50),
    parent NVARCHAR(50),
    mail NVARCHAR(100)
);
GO
INSERT INTO addresslist (name, parent, mail) VALUES
('總經理', NULL, 'boss@example.com'),
('人資部', '總經理', 'hr@example.com'),
('資訊部', '總經理', 'it@example.com'),
('研發組', '資訊部', 'dev@example.com'),
('網管組', '資訊部', 'net@example.com');
GO
```

---

### 7. DB 設定確認

確保 `main.py` 內設定如下：

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "address",
    "username": "sa",
    "password": "itpower1!"
}
```

---

## ⚙️ 二、開發與示範操作 (DEMO)

### 1. 啟動虛擬環境

```powershell
cd C:\Users\<你的帳號>\Desktop\KC\<your-repo>
.env\Scriptsctivate
```

---

### 2. 啟動 API Server

建議使用以下指令（避免權限問題）：

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 9000
```

成功訊息：

```
INFO:     Uvicorn running on http://127.0.0.1:9000 (Press CTRL+C to quit)
```

---

### 3. 測試與演示

- **健康檢查：**  
  [http://127.0.0.1:9000/](http://127.0.0.1:9000/) → 應顯示 `{"message": "Hello World"}`

- **Swagger UI 文件：**  
  [http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs)

- **通訊錄樹狀查詢：**  
  [http://127.0.0.1:9000/contacts/tree](http://127.0.0.1:9000/contacts/tree)  
  [http://127.0.0.1:9000/contacts/tree/資訊部](http://127.0.0.1:9000/contacts/tree/資訊部)

---

## 🧱 三、後續遷移與正式部署建議

> ⚠️ 本環境屬於 **虛擬開發環境 (Local Virtual Dev Environment)**，僅供本機開發、測試、展示之用。  
> 未來遷移到正式伺服器 (Production Environment) 時請注意：

1. **DB 連線設定**
   - 改用正式資料庫主機、應用程式帳號
   - 密碼改由環境變數或 Secret 管理

2. **服務綁定**
   - host 改為 0.0.0.0 或指定內網 IP
   - port 納入防火牆 / reverse proxy 設定

3. **部署方式**
   - 可使用 Docker Compose、Kubernetes、systemd 服務等

4. **安全性**
   - 不使用開發用憑證與密碼
   - 啟用 HTTPS、CORS、安全驗證
   - 設定監控與日誌系統

---

## 📚 四、快速指令摘要

| 操作 | 指令 |
|------|------|
| 啟動虛擬環境 | `.\venv\Scripts\activate` |
| 安裝套件 | `python -m pip install -r requirements.txt` |
| 啟動 API | `python -m uvicorn main:app --host 127.0.0.1 --port 9000` |
| 停止 API | `Ctrl + C` |
| 停用虛擬環境 | `deactivate` |
| 檢查 Docker 容器 | `docker ps` |

---

© 2025 FastAPIProject Setup Guide. For internal use only.
