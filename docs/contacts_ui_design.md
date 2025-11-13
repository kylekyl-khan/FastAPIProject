# 通訊錄 Outlook 外掛前端介面原型設計

## 1. 使用者流程概述

1. 進入首頁（`/contacts`）時載入公司最高層級組織資料，顯示成卡片格狀或清單。
2. 點擊任一組織單位卡片，逐層展開 TreeView，必要時呼叫 `/contacts/tree/{root_name}` API。
3. 在 TreeView 中逐層點擊部門 → 分組節點，延遲載入下層節點。
4. 點選分組的最後一層節點時，於右側顯示人員清單與操作按鈕。
5. 透過按鈕將選定人員加入 Outlook 收件者/副本欄位；若不在 Outlook 環境則顯示警告 Toast。

## 2. 頁面結構與元件配置

### 2.1 全域佈局

```text
+---------------------------------------------------------------+
|  Header: 應用標題、重新整理、Outlook 狀態指示               |
+---------------------+-----------------------------------------+
|  Left Pane          |  Right Pane                             |
|  （組織樹狀區）     |  （人員資訊區）                        |
|                     |                                         |
|  [搜尋輸入框]       |  [分組標題與行動按鈕列]                |
|  [TreeView 容器]    |  [人員卡片清單]                        |
|                     |     - 名稱、職稱、Email、電話          |
|                     |     - 行動按鈕：收件者/副本/密件      |
+---------------------+-----------------------------------------+
|  Toast 容器 (固定於底部)                                     |
+---------------------------------------------------------------+
```

### 2.2 首頁（`/contacts`）內容
- **Header**：顯示應用名稱、目前 Outlook 整合狀態（`Connected` / `Not Connected`），提供重新整理按鈕。
- **搜尋輸入框**：支援關鍵字過濾 TreeView 節點（即時篩選）。
- **組織卡片區**：初次載入顯示最高層級單位，每張卡片含單位名稱、單位描述、`展開` 按鈕。
- **TreeView 容器**：點擊卡片後顯示懸浮面板或直接進入左側 TreeView，節點可展開/收合。
- **人員資訊區**：尚未選擇分組時顯示空狀態提示（含圖示與說明文字）。
- **Toast 容器**：用於顯示成功、警告或錯誤訊息。

### 2.3 TreeView 行為
- 利用 `<ul>` / `<li>` 或 `<details>` / `<summary>` 結構搭配自訂樣式實作階層。
- 每個節點顯示：名稱、節點類型（部門/分組）、載入狀態指示。
- 懸浮 `action` 區提供：`展開/收合`、`載入中` 旋轉圖示。
- 支援懶載入：展開節點時若尚未載入子節點則呼叫 API。

### 2.4 人員資訊區
- 顯示所選分組名稱與路徑（Breadcrumb）。
- 人員清單以卡片或表格形式呈現，每列包含：
  - 大頭貼縮圖（可用字母佔位）
  - 姓名、職稱
  - Email（可點擊複製）
  - 電話（顯示 tel 連結）
  - 加入 Outlook 行動按鈕列：`收件者`、`副本`、`密件`。
- 提供全選/批次加入 Outlook 的選項。

### 2.5 Toast 與 Modal
- **Toast**：自訂 HTML 容器，使用 `aria-live="polite"` 增強可及性；支援不同狀態樣式（success/warning/error）。
- **Modal**（選用）：顯示進階資訊或大量人員清單時使用。

## 3. API 呼叫設計

| 時機 | API | Request | Response 主要欄位 |
| --- | --- | --- | --- |
| 進入首頁 | `GET /contacts/tree` | 無 | `{"name": "root", "children": [...]}` |
| 點擊特定組織 | `GET /contacts/tree/{root_name}` | `root_name`: 單位名稱 | 依節點回傳 `{"name": "青山校區", "children": [...]}` |
| 懶載入子節點 | 同上 | 搭配節點唯一識別 `id` | 子節點陣列（含 `type`, `children` 或 `hasChildren`） |

### 3.1 資料結構建議

```json
{
  "id": "campus-001",
  "name": "青山校區",
  "type": "campus",            // campus | department | group | person
  "hasChildren": true,
  "children": [
    {
      "id": "dept-101",
      "name": "教務處",
      "type": "department",
      "hasChildren": true
    }
  ]
}
```

- 最末層（`type: "group"`）的 `children` 為人員陣列，格式如下：

```json
{
  "id": "person-203",
  "name": "林小明",
  "title": "專員",
  "email": "user@example.com",
  "phone": "02-1234-5678"
}
```

## 4. DOM 元件與 CSS 建議

| 功能 | 元件 | 描述 |
| --- | --- | --- |
| TreeView | `<nav>` + `<ul class="tree">` | 採 `aria-tree` 角色，子節點 `role="treeitem"`。|
| 人員清單 | `<section>` + `<article class="contact-card">` | 使用 CSS Grid 排版，支援響應式。|
| Toast | `<div id="toast-container">` | 以 `position: fixed; bottom: 1rem; right: 1rem;` 展示。|
| Breadcrumb | `<nav aria-label="Breadcrumb">` | 顯示目前選取路徑。|
| 搜尋欄 | `<input type="search">` | 搭配去抖動事件處理。|
| Loading Indicator | `<span class="spinner">` | CSS 動畫顯示。|

## 5. JavaScript 模組化建議

```
/ static/
  ├── script.js
  ├── api/
  │     └── contactsApi.js
  ├── modules/
  │     ├── treeView.js
  │     ├── contactList.js
  │     ├── toast.js
  │     └── outlookIntegration.js
```

### 5.1 `contactsApi.js`
- 封裝 `fetchTree(rootName)` 與 `fetchRoot()` 函式，回傳 Promise。
- 處理 HTTPS 憑證錯誤與逾時，提供錯誤訊息。

### 5.2 `treeView.js`
- 管理 TreeView DOM，提供 `renderRoot(nodes)`、`expandNode(nodeId)`、`collapseNode(nodeId)`。
- 支援懶載入：節點第一次展開時呼叫 API。
- 發出自訂事件 `tree:nodeSelected`，攜帶節點資料。

### 5.3 `contactList.js`
- 處理右側人員清單渲染與 Outlook 按鈕。
- 暴露 `renderContacts(group)`、`clear()`。
- 與 `outlookIntegration.js` 合作，避免重複加入收件人。

### 5.4 `toast.js`
- 提供 `show(message, type)` 函式，類型包含 `success`、`warning`、`error`。
- 自動於設定秒數後隱藏，並支援多個佇列。

### 5.5 `outlookIntegration.js`
- 檢查 `Office.context.mailbox` 是否存在，暴露 `isOutlook()`。
- 提供 `addRecipients(recipients, targetField)`，targetField 可為 `to`, `cc`, `bcc`。
- 內部使用 `Office.context.mailbox.item[to|cc|bcc].getAsync` 與 `setAsync` 更新欄位，避免重複。
- 若非 Outlook 環境，呼叫 `toast.show("Outlook 環境不可用", "warning")`。

### 5.6 `script.js`
- 為入口檔案，負責初始化：
  1. 檢查 Outlook 環境；若無則顯示 Toast。
  2. 呼叫 `contactsApi.fetchRoot()` 取得最高層級節點，交給 `treeView.renderRoot`。
  3. 註冊事件：
     - `tree:nodeSelected` → 若 `node.type === 'group'` 則渲染人員清單。
     - Outlook 按鈕 `click` → 呼叫 `outlookIntegration.addRecipients`。
     - 搜尋輸入去抖動 → 呼叫 `treeView.filter(keyword)`。
  4. 監聽 `window.resize` 調整排版（行動版折疊左側樹狀區）。

## 6. Outlook 外掛整合建議

1. 在 `Office.initialize` 中啟動腳本，確保 Office.js 已載入。
2. 使用 `Office.context.mailbox.item` 操作收件者：
   ```javascript
   Office.context.mailbox.item.to.addAsync([{ displayName, emailAddress }], callback);
   ```
3. 加入前先透過 `getAsync` 取得現有收件者，使用 email 地址比對避免重複。
4. 若欲支援批次加入，先彙整所有選取人員的 email，再一次呼叫 `addAsync`。
5. 使用 `Office.context.mailbox.item.notificationMessages.replaceAsync` 顯示 Outlook 原生提示或改用自訂 Toast。
6. 若偵測不到 Outlook 環境，提供替代動作：
   - 顯示 `toast.show('請在 Outlook 外掛中使用，以啟用寄件功能', 'warning');`
   - 禁用加入收件者按鈕或改為複製 Email。

## 7. 互動細節與使用者體驗

- **Lazy Loading**：節點第一次展開時顯示 spinner，避免空白。載入完成後自動移除。
- **Breadcrumb**：在右側顯示從根節點到目前分組的路徑，增進定位感。
- **Keyboard Accessibility**：TreeView 支援方向鍵操作、`Enter` 展開節點。
- **空狀態提示**：當尚未選取分組或某分組無人員時顯示對應插畫與說明，提供重新整理按鈕。
- **錯誤處理**：API 失敗時透過 Toast + 錯誤圖示提醒，並在節點上顯示重試按鈕。
- **響應式設計**：行動版將 TreeView 折疊至抽屜式選單，點擊後滑出；人員清單改為單欄卡片。
- **主題一致性**：採用 Outlook Add-in 指南建議的中性色調與 4px 圓角，按鈕配色參考 Microsoft Fluent Design。

## 8. 文字化介面流程示意

```
[Header]
  通訊錄 | Outlook 狀態：Connected ● | 重新整理 ↻

[左側]
  搜尋： [__________________]

  TreeView：
  - 文教系統
    - 青山校區 ▶ (點擊展開)
      - 教務處 ▶
      - 總務處 ▶
  - 科技系統

[右側]
  空狀態：請從左側選擇部門

-- 點擊「青山校區」後 --

TreeView：
  - 文教系統
    - 青山校區 ▼
      - 教務處 ▶
      - 總務處 ▶

右側顯示：
  標題：青山校區
  說明：請選擇分組以查看成員

-- 展開「教務處」 → 點選「招生組」 --

Breadcrumb：文教系統 / 青山校區 / 教務處 / 招生組
[批次加入 Outlook 按鈕]

人員卡片：
┌─────────────────────────────┐
| 林小明  | 招生專員          |
| Email: user@example.com       |
| Phone: 02-1234-5678           |
| [加到收件者] [加到副本] [加到密件] |
└─────────────────────────────┘
```

## 9. 進一步優化方向

- 加入快取機制：對已載入的節點結果緩存，減少重複 API 呼叫。
- 支援匯出：提供將分組成員匯出 CSV 或複製到剪貼簿的功能。
- 使用 Service Worker：實現基本離線瀏覽與靜態資源快取。
- 以 `aria-live` 提升 Toast 無障礙程度，並確保所有互動可由鍵盤完成。

