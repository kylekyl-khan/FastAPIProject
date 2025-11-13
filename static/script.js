class ContactManager {
  constructor() {}
}

ContactManager.prototype.buildTreeHtml = function (node) {
  // 假設 node 結構大概像 { name, mail, children: [...] }
  let html = "<li>";

  html += `<span data-name="${node.name || ""}" data-mail="${node.mail || ""}">
              ${node.name || "(未命名)"}
           </span>`;

  if (node.children && node.children.length > 0) {
    html += "<ul style='display:none'>";
    for (const child of node.children) {
      html += this.buildTreeHtml(child);
    }
    html += "</ul>";
  }

  html += "</li>";
  return html;
};

ContactManager.prototype.bindTreeEvents = function () {
  const treeRoot = document.getElementById("contacts-tree");
  const detailsBox = document.getElementById("details-box");
  if (!treeRoot || !detailsBox) return;

  treeRoot.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.tagName.toLowerCase() !== "span") return;

    const li = target.closest("li");
    if (!li) return;

    // 展開 / 收合：如果有子 ul
    const childUl = li.querySelector(":scope > ul");
    if (childUl) {
      const isHidden = childUl.style.display === "none";
      childUl.style.display = isHidden ? "block" : "none";
    }

    // 高亮選取節點
    treeRoot.querySelectorAll("span.selected").forEach((s) => {
      s.classList.remove("selected");
    });
    target.classList.add("selected");

    // 更新詳細資訊
    const name = target.dataset.name || "(未命名)";
    const mail = target.dataset.mail || "";

    detailsBox.innerHTML = `
      <h2>${name}</h2>
      <p>Email：${mail || "（無資料）"}</p>
      ${
        mail
          ? `<button id="btn-add-to-to">加入收件人 (To)</button>`
          : ""
      }
    `;

    if (mail) {
      const btn = document.getElementById("btn-add-to-to");
      if (btn) {
        btn.addEventListener("click", () => {
          if (
            window.Office &&
            window.Office.context &&
            window.Office.context.mailbox
          ) {
            window.Office.context.mailbox.item.to.addAsync(
              [{ displayName: name, emailAddress: mail }],
              (asyncResult) => {
                if (
                  asyncResult.status ===
                  window.Office.AsyncResultStatus.Failed
                ) {
                  console.error("Add to TO failed:", asyncResult.error);
                }
              }
            );
          } else {
            alert(`(Dev) 模式：會將 ${mail} 加到 To（Outlook 中才有效）`);
          }
        });
      }
    }
  });
};

ContactManager.prototype.init = function () {
  const treeContainer = document.querySelector("#contacts-tree ul");
  if (!treeContainer) {
    console.error("contacts-tree UL not found");
    return;
  }

  fetch("/contacts/tree")
    .then((resp) => {
      if (!resp.ok) throw new Error("Failed to load contacts tree");
      return resp.json();
    })
    .then((data) => {
      // data 應該是 root node 或節點陣列
      let html = "";
      if (Array.isArray(data)) {
        for (const node of data) {
          html += this.buildTreeHtml(node);
        }
      } else if (data) {
        html = this.buildTreeHtml(data);
      }
      treeContainer.innerHTML = html;
      this.bindTreeEvents();
    })
    .catch((err) => {
      console.error(err);
      const detailsBox = document.getElementById("details-box");
      if (detailsBox) {
        detailsBox.innerHTML =
          "<p style='color:red'>載入通訊錄失敗，請稍後再試。</p>";
      }
    });
};

document.addEventListener("DOMContentLoaded", () => {
  const manager = new ContactManager();
  manager.init();
});
