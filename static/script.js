/**
 * Outlook联系人选择器
 * 提供组织通讯录的树形展示和邮件联系人管理功能
 */

class ContactManager {
    constructor() {
        this.selectedContacts = {
            recipients: [],
            cc: [],
            bcc: []
        };
        this.contactsData = [];
        this.init();
    }

    /**
     * 初始化应用
     */
    init() {
        // Office环境初始化
        if (typeof Office !== 'undefined') {
            Office.onReady(this.onOfficeReady.bind(this));
        }
        
        // DOM内容加载完成后初始化
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', this.onDomReady.bind(this));
        } else {
            this.onDomReady();
        }
    }

    /**
     * Office环境准备就绪回调
     */
    onOfficeReady(info) {
        if (info.host === Office.HostType.Outlook) {
            console.log('Office.js is ready');
            this.loadContacts();
        }
    }

    /**
     * DOM准备就绪回调
     */
    onDomReady() {
        // 非Office环境下也加载联系人
        if (typeof Office === 'undefined' || !Office.context || Office.context.platform !== Office.PlatformType.OfficeOnline) {
            this.loadContacts();
        }
    }

    /**
     * 加载联系人数据
     */
    async loadContacts() {
        try {
            const response = await fetch('/contacts/tree');
            const data = await response.json();
            
            if (data.error) {
                this.showError('加载联系人失败: ' + data.error);
                return;
            }
            
            this.contactsData = data;
            this.renderContactsTree();
            this.bindTreeEvents();
        } catch (error) {
            this.showError('加载联系人失败: ' + error.message);
        }
    }

    /**
     * 渲染联系人树
     */
    renderContactsTree() {
        const treeContainer = document.querySelector('#contacts-tree ul');
        if (treeContainer) {
            treeContainer.innerHTML = this.buildTreeHtml(this.contactsData);
        }
    }

    /**
     * 构建树形HTML结构
     * @param {Array} nodes - 联系人节点数组
     * @returns {string} 生成的HTML字符串
     */
    buildTreeHtml(nodes) {
        // 如果没有节点数据或者节点数组为空，返回空字符串
        if (!nodes || nodes.length === 0) return '';
        
        // 初始化一个空的 HTML 字符串
        let html = '';
        
        // 遍历每个节点
        nodes.forEach(node => {
            // 检查节点是否有子节点
            const hasChildren = node.children && node.children.length > 0;
            
            // 如果有子节点，添加 'parent_li collapsed' 类，否则为空
            // 'parent_li' 表示这是一个父节点
            // 'collapsed' 表示默认是折叠状态
            const liClass = hasChildren ? 'parent_li collapsed' : '';
            
            // 获取节点的姓名和邮箱信息，如果不存在则设为空字符串
            const name = node.name || '';
            const mail = node.mail || '';
            
            // 构建 HTML 字符串，包含节点信息
            // 使用 data-name 和 data-mail 属性存储额外信息，不显示在页面上
            // 只显示姓名，不显示邮箱（符合之前的需求）
            html += `<li class="${liClass}">
                <span data-name="${name}" data-mail="${mail}">${name}</span>`;
            
            // 如果有子节点，递归构建子节点的 HTML
            // 默认隐藏子节点（display: none）
            if (hasChildren) {
                html += `<ul style="display: none;">${this.buildTreeHtml(node.children)}</ul>`;
            }
            
            // 关闭 li 标签
            html += '</li>';
        });
        
        // 返回构建完成的 HTML 字符串
        return html;
    }

    /**
     * 绑定树形结构事件
     */
    bindTreeEvents() {
        // 绑定展开/折叠事件
        document.querySelectorAll('.parent_li > span').forEach(span => {
            span.addEventListener('click', (e) => {
                e.stopPropagation();
                const parentLi = e.target.parentElement;
                const children = parentLi.querySelector('ul');
                if (children) {
                    children.style.display = children.style.display === 'none' ? 'block' : 'none';
                    parentLi.classList.toggle('collapsed');
                }
            });
        });
        
        // 绑定节点点击事件
        document.querySelectorAll('.tree li span').forEach(span => {
            span.addEventListener('click', (e) => {
                e.stopPropagation();
                this.onContactSelected(e.target);
            });
        });
    }

    /**
     * 联系人选择事件处理
     */
    onContactSelected(element) {
        // 移除之前的选中状态
        document.querySelectorAll('.tree li span').forEach(span => {
            span.classList.remove('selected');
        });
        
        // 添加当前选中状态
        element.classList.add('selected');
        
        // 获取联系人信息
        const name = element.getAttribute('data-name');
        const mail = element.getAttribute('data-mail');
        
        if (name && mail) {
            this.showContactDetails(name, mail);
        }
    }

    /**
     * 显示联系人详细信息
     */
    showContactDetails(name, mail) {
        const detailsBox = document.getElementById('details-box');
        if (detailsBox) {
            detailsBox.innerHTML = `
                <h3>联系人信息</h3>
                <p><strong>姓名:</strong> ${this.escapeHtml(name)}</p>
                <p><strong>邮箱:</strong> ${this.escapeHtml(mail)}</p>
                <div class="button-container">
                    <button class="action-button" data-action="to" data-name="${name}" data-mail="${mail}">添加收件人</button>
                    <button class="action-button" data-action="cc" data-name="${name}" data-mail="${mail}">添加抄送人</button>
                    <button class="action-button" data-action="bcc" data-name="${name}" data-mail="${mail}">添加密送人</button>
                </div>
            `;
            
            // 绑定操作按钮事件
            detailsBox.querySelectorAll('.action-button').forEach(button => {
                button.addEventListener('click', (e) => {
                    const action = e.target.getAttribute('data-action');
                    const contactName = e.target.getAttribute('data-name');
                    const contactMail = e.target.getAttribute('data-mail');
                    
                    switch (action) {
                        case 'to':
                            this.addRecipient(contactName, contactMail);
                            break;
                        case 'cc':
                            this.addCC(contactName, contactMail);
                            break;
                        case 'bcc':
                            this.addBCC(contactName, contactMail);
                            break;
                    }
                });
            });
        }
    }

    /**
     * 添加收件人
     */
    addRecipient(name, mail) {
        // 直接添加到邮件收件人，而不是添加到列表
        this.insertRecipientToEmail([{emailAddress: mail, displayName: name}], 'to');
    }

    /**
     * 添加抄送人
     */
    addCC(name, mail) {
        // 直接添加到邮件抄送人，而不是添加到列表
        this.insertRecipientToEmail([{emailAddress: mail, displayName: name}], 'cc');
    }

    /**
     * 添加密送人
     */
    addBCC(name, mail) {
        // 直接添加到邮件密送人，而不是添加到列表
        this.insertRecipientToEmail([{emailAddress: mail, displayName: name}], 'bcc');
    }

    /**
     * 直接插入联系人到邮件
     */
    insertRecipientToEmail(recipients, type) {
        // 检查Office环境
        if (typeof Office === 'undefined' || !Office.context || !Office.context.mailbox) {
            this.showMessage("此功能仅在Outlook中可用");
            return;
        }
        
        const item = Office.context.mailbox.item;
        if (!item) {
            this.showMessage("无法获取邮件项");
            return;
        }
        
        // 获取当前已有的收件人列表
        let getOperation, setOperation;
        switch (type) {
            case 'to':
                getOperation = item.to.getAsync;
                setOperation = item.to.setAsync;
                break;
            case 'cc':
                getOperation = item.cc.getAsync;
                setOperation = item.cc.setAsync;
                break;
            case 'bcc':
                getOperation = item.bcc.getAsync;
                setOperation = item.bcc.setAsync;
                break;
            default:
                this.showMessage("无效的联系人类型");
                return;
        }
        
        // 先获取当前的收件人列表
        getOperation.bind(type === 'to' ? item.to : type === 'cc' ? item.cc : item.bcc)({ coercionType: Office.CoercionType.Recipients }, (result) => {
            if (result.status === Office.AsyncResultStatus.Succeeded) {
                // 获取当前收件人列表
                const currentRecipients = result.value || [];
                
                // 将新的收件人添加到现有列表中
                const allRecipients = [...currentRecipients, ...recipients];
                
                // 去重 - 基于emailAddress字段
                const uniqueRecipients = [];
                const emailSet = new Set();
                
                allRecipients.forEach(recipient => {
                    const email = recipient.emailAddress ? recipient.emailAddress.toLowerCase() : '';
                    if (email && !emailSet.has(email)) {
                        emailSet.add(email);
                        uniqueRecipients.push(recipient);
                    }
                });
                
                // 添加新的收件人到邮件中
                setOperation.bind(type === 'to' ? item.to : type === 'cc' ? item.cc : item.bcc)(uniqueRecipients, { asyncContext: null }, (result) => {
                    if (result.status !== Office.AsyncResultStatus.Succeeded) {
                        this.showMessage("插入联系人失败: " + result.error.message);
                    } else {
                        this.showMessage("联系人已成功添加到邮件中");
                    }
                });
            } else {
                // 如果获取当前收件人失败，则直接设置新的收件人
                setOperation.bind(type === 'to' ? item.to : type === 'cc' ? item.cc : item.bcc)(recipients, { asyncContext: null }, (result) => {
                    if (result.status !== Office.AsyncResultStatus.Succeeded) {
                        this.showMessage("插入联系人失败: " + result.error.message);
                    } else {
                        this.showMessage("联系人已成功添加到邮件中");
                    }
                });
            }
        });
    }

    /**
     * 显示消息
     */
    showMessage(message) {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = 'message-toast';
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #0078d7;
            color: white;
            padding: 10px;
            border-radius: 4px;
            z-index: 1000;
            max-width: 300px;
            word-wrap: break-word;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;
        
        document.body.appendChild(messageEl);
        
        // 3秒后移除消息
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 3000);
    }

    /**
     * 显示错误信息
     */
    showError(message) {
        const treeContainer = document.getElementById('contacts-tree');
        if (treeContainer) {
            treeContainer.innerHTML = `<p style="color: red;">错误: ${message}</p>`;
        }
    }

    /**
     * HTML转义，防止XSS
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
}

// 全局函数，供HTML直接调用
let contactManager = null;

// 初始化联系人管理器
document.addEventListener('DOMContentLoaded', () => {
    contactManager = new ContactManager();
});