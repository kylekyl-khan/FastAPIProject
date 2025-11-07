# FastAPI 通訊錄服務本地部署教程

本教程將帶你一步步在本機啟動專案，包含環境準備、資料庫建置、啟動後端與前端頁面。照著每個步驟操作即可完成部署。

---

## 1. 準備開發環境

1. 安裝 **Python 3.10 以上版本**（可到 [python.org](https://www.python.org/downloads/) 下載）。
2. 安裝 **Git**（可到 [git-scm.com](https://git-scm.com/downloads) 下載）。
3. 若想用 Docker 快速啟動 SQL Server，請先安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

> 如果你的電腦已經有可用的 Microsoft SQL Server，可跳過 Docker 安裝，但後續仍需在該實例建立 `address` 資料庫與 `addresslist` 資料表。

---

## 2. 取得程式碼並安裝相依套件

1. 下載專案程式碼並切換到專案資料夾：
   ```bash
   git clone <[repository-url](https://github.com/kylekyl-khan/FastAPIProject)>
   cd FastAPIProject
   ```

2. 建立並啟用虛擬環境：
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 安裝 Python 套件：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. 啟動並初始化 SQL Server

### 3.1 使用 Docker 快速啟動（推薦）

```bash
docker run -e "ACCEPT_EULA=Y" \
  -e "SA_PASSWORD=YourStrong!Passw0rd" \
  -p 1433:1433 --name fastapi-sqlserver \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

等待容器狀態為 `healthy` 後，使用下列指令進入容器並打開 `sqlcmd`：

```bash
docker exec -it fastapi-sqlserver /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U sa -P YourStrong!Passw0rd
```

### 3.2（可選）使用現有 SQL Server

若你已經有 SQL Server，使用喜歡的管理工具（Azure Data Studio、SSMS、sqlcmd）連線即可，後續步驟相同。

---

## 4. 建立資料庫與範例資料

在 `sqlcmd` 或圖形化管理工具中執行以下 SQL 腳本：

```sql
CREATE DATABASE address;
GO
USE address;
GO
CREATE TABLE addresslist (
    name NVARCHAR(255) NOT NULL,
    parent NVARCHAR(255) NULL,
    mail NVARCHAR(255) NOT NULL
);
INSERT INTO addresslist (name, parent, mail) VALUES
('Company', NULL, 'info@example.com'),
('Management', 'Company', 'management@example.com'),
('Engineering', 'Company', 'engineering@example.com'),
('Alice Chen', 'Engineering', 'alice.chen@example.com'),
('Bob Wu', 'Engineering', 'bob.wu@example.com');
```

> 建立好資料後即可離開 `sqlcmd`（輸入 `QUIT`）。

---

## 5. 設定後端資料庫連線

開啟專案根目錄的 `main.py`，找到 `DB_CONFIG` 區塊，確認內容與你實際的 SQL Server 設定相符：

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "address",
    "username": "sa",
    "password": "YourStrong!Passw0rd",
}
```

- 若不是在本機執行 SQL Server，請改成實際的主機名稱或 IP。
- 若使用 Docker 指令中的密碼，記得與此處保持一致。

---

## 6. 啟動 FastAPI 服務

1. 確認虛擬環境仍在啟用狀態。
2. 在專案根目錄執行：
   ```bash
   uvicorn main:app --reload
   ```
3. 終端機出現 `Application startup complete.` 代表啟動成功，服務位於 `http://127.0.0.1:8000`。

---

## 7. 驗證服務是否正常

1. 開啟瀏覽器訪問 `http://127.0.0.1:8000/contacts`，應該看到通訊錄樹狀列表。
2. 若想檢視 API 文件，訪問 `http://127.0.0.1:8000/docs`。
3. 也可以使用 `curl` 驗證：
   ```bash
   curl http://127.0.0.1:8000/contacts/tree | jq
   ```

若看不到資料，請確認資料庫設定與 SQL Server 是否正在執行。

---

## 8.（可選）啟用 HTTPS 以配合 Outlook 外掛

Outlook 外掛要求 HTTPS。專案提供腳本快速建立自簽憑證。

1. 產生憑證：
   ```bash
   python generate_cert.py
   ```
2. 將 `ssl/ca.pem` 匯入作業系統信任憑證（Windows 使用者可執行 `install_cert.ps1`）。
3. 啟動 HTTPS 伺服器：
   ```bash
   python https_server.py
   ```
4. 在 Outlook 外掛設定中使用 `https://127.0.0.1:8443/optimized-manifest.xml` 作為 Manifest URL。

---

## 9. 常見問題排查

| 問題 | 排查方式 |
| ---- | -------- |
| 無法連線至資料庫 | 檢查 SQL Server 是否啟動、帳密是否與 `DB_CONFIG` 相符、Docker 容器是否暴露 1433 連接埠。 |
| 啟動時顯示 `ModuleNotFoundError` | 確認虛擬環境已啟用並重新執行 `pip install -r requirements.txt`。 |
| 前端無法操作 Outlook 功能 | 只有在 Outlook 中開啟才會啟用新增收件人按鈕；在一般瀏覽器中屬於預期行為。 |

---

## 10. 進階補充

- 如需自訂資料結構，可調整 `main.py` 中的 `build_tree` 函式。
- 專案包含 `create_icon.py` 可產生測試用圖示，以及 `test_main.http` 方便透過 VS Code REST Client 插件測試 API。

完成上述步驟後，即可在本地完整體驗 FastAPI 通訊錄應用！
