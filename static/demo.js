class OrganizationExplorer {
    constructor() {
        this.treeElement = document.getElementById('org-tree');
        this.detailsElement = document.getElementById('org-details');
        this.peopleListElement = document.getElementById('people-list');
        this.selectedOrgsElement = document.getElementById('selected-orgs');
        this.selectedPeopleElement = document.getElementById('selected-people');
        this.clearButton = document.getElementById('clear-selection');
        this.searchInput = document.getElementById('search-org');
        this.personTemplate = document.getElementById('person-item-template');

        this.treeData = [];
        this.filteredTree = null;
        this.nodeMap = new Map();
        this.parentMap = new Map();
        this.childMap = new Map();
        this.personMap = new Map();
        this.selectedOrgIds = new Set();
        this.selectedPersonIds = new Set();
        this.expandedOrgIds = new Set();
        this.currentOrgId = null;
        this.searchQuery = '';

        this.bindEvents();
        this.loadTree();
    }

    bindEvents() {
        this.clearButton.addEventListener('click', () => {
            this.selectedOrgIds.clear();
            this.selectedPersonIds.clear();
            this.render();
        });

        this.searchInput.addEventListener('input', (event) => {
            this.searchQuery = event.target.value.trim();
            this.applySearch();
        });
    }

    async loadTree() {
        try {
            const response = await fetch('/demo/organizations/tree');
            if (!response.ok) {
                throw new Error(`無法載入資料 (${response.status})`);
            }
            const data = await response.json();
            this.treeData = data;
            this.indexTree();
            this.expandRootNodes();
            this.render();
        } catch (error) {
            this.showError(error.message);
        }
    }

    indexTree() {
        this.nodeMap.clear();
        this.parentMap.clear();
        this.childMap.clear();
        this.personMap.clear();

        const walk = (node, parentId = null) => {
            this.nodeMap.set(node.id, node);
            if (!this.childMap.has(node.id)) {
                this.childMap.set(node.id, []);
            }
            if (parentId !== null) {
                this.parentMap.set(node.id, parentId);
                this.childMap.get(parentId).push(node.id);
            }

            node.people.forEach((person) => {
                this.personMap.set(person.id, person);
            });

            node.children.forEach((child) => walk(child, node.id));
        };

        this.treeData.forEach((node) => walk(node));
    }

    expandRootNodes() {
        this.treeData.forEach((node) => this.expandedOrgIds.add(node.id));
    }

    applySearch() {
        if (!this.searchQuery) {
            this.filteredTree = null;
        } else {
            const query = this.searchQuery.toLowerCase();
            const filterNodes = (nodes) => {
                const matches = [];
                nodes.forEach((node) => {
                    const nameMatch = node.name.toLowerCase().includes(query);
                    const filteredChildren = filterNodes(node.children);
                    if (nameMatch || filteredChildren.length > 0) {
                        matches.push({
                            ...node,
                            children: filteredChildren,
                        });
                    }
                });
                return matches;
            };
            this.filteredTree = filterNodes(this.treeData);
        }
        this.render();
    }

    render() {
        this.renderTree();
        this.renderDetails();
        this.updateSelectionSummary();
    }

    renderTree() {
        const targetTree = this.filteredTree !== null ? this.filteredTree : this.treeData;
        const forceExpand = Boolean(this.searchQuery);

        this.treeElement.innerHTML = '';

        if (!targetTree.length) {
            const empty = document.createElement('p');
            empty.className = 'empty-state';
            empty.textContent = this.searchQuery ? '找不到符合的組織' : '尚未載入資料';
            this.treeElement.appendChild(empty);
            return;
        }

        const tree = this.renderTreeNodes(targetTree, forceExpand);
        this.treeElement.appendChild(tree);
    }

    renderTreeNodes(nodes, forceExpand) {
        const list = document.createElement('ul');
        nodes.forEach((viewNode) => {
            const actualNode = this.nodeMap.get(viewNode.id);
            if (!actualNode) {
                return;
            }

            const item = document.createElement('li');
            item.setAttribute('role', 'treeitem');
            item.dataset.orgId = String(actualNode.id);
            item.setAttribute('aria-selected', String(actualNode.id === this.currentOrgId));

            const row = document.createElement('div');
            row.className = 'node-row';

            const hasChildren = actualNode.children.length > 0;
            const expanded = forceExpand || this.expandedOrgIds.has(actualNode.id);

            if (hasChildren) {
                item.setAttribute('aria-expanded', String(expanded));
                const toggle = document.createElement('button');
                toggle.type = 'button';
                toggle.className = 'toggle';
                toggle.setAttribute('aria-label', expanded ? '收合節點' : '展開節點');
                toggle.textContent = expanded ? '▾' : '▸';
                toggle.addEventListener('click', (event) => {
                    event.stopPropagation();
                    this.toggleExpand(actualNode.id);
                });
                row.appendChild(toggle);
            } else {
                item.setAttribute('aria-expanded', 'false');
                const spacer = document.createElement('span');
                spacer.className = 'toggle';
                spacer.setAttribute('aria-hidden', 'true');
                spacer.textContent = '•';
                row.appendChild(spacer);
            }

            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            const selectionState = this.getOrgSelectionState(actualNode.id);
            checkbox.checked = selectionState === 'checked';
            checkbox.indeterminate = selectionState === 'indeterminate';
            checkbox.addEventListener('change', (event) => {
                this.onOrgCheckboxChange(actualNode.id, event.target.checked);
            });
            label.appendChild(checkbox);

            const nameSpan = document.createElement('span');
            nameSpan.className = 'org-name';
            if (actualNode.id === this.currentOrgId) {
                nameSpan.classList.add('current');
            }
            nameSpan.textContent = actualNode.name;
            nameSpan.addEventListener('click', (event) => {
                event.preventDefault();
                this.showOrganization(actualNode.id);
            });
            label.appendChild(nameSpan);

            row.appendChild(label);
            item.appendChild(row);

            if (hasChildren && viewNode.children.length > 0) {
                const childList = this.renderTreeNodes(viewNode.children, forceExpand);
                if (!forceExpand && !expanded) {
                    childList.hidden = true;
                }
                childList.classList.add('child-list');
                item.appendChild(childList);
            }

            list.appendChild(item);
        });
        return list;
    }

    renderDetails() {
        const node = this.currentOrgId ? this.nodeMap.get(this.currentOrgId) : null;
        this.detailsElement.innerHTML = '';

        if (!node) {
            const title = document.createElement('h2');
            title.textContent = '選取一個組織以顯示詳細資訊';
            const description = document.createElement('p');
            description.textContent = '點擊左側的組織名稱即可檢視層級、成員與操作選項。';
            this.detailsElement.appendChild(title);
            this.detailsElement.appendChild(description);
            this.peopleListElement.innerHTML = '';
            const emptyPeople = document.createElement('p');
            emptyPeople.className = 'empty-state';
            emptyPeople.textContent = '尚未選取任何組織';
            this.peopleListElement.appendChild(emptyPeople);
            return;
        }

        const title = document.createElement('h2');
        title.textContent = node.name;
        this.detailsElement.appendChild(title);

        const stats = document.createElement('div');
        stats.className = 'badge';
        const descendants = this.getDescendantOrgIds(node.id).length - 1;
        const members = this.collectPeopleForOrg(node.id).length;
        stats.textContent = `含 ${descendants} 個下屬單位 · ${members} 位成員`;
        this.detailsElement.appendChild(stats);

        const breadcrumb = document.createElement('div');
        breadcrumb.className = 'breadcrumb';
        this.buildBreadcrumb(node.id).forEach((name) => {
            const crumb = document.createElement('span');
            crumb.textContent = name;
            breadcrumb.appendChild(crumb);
        });
        this.detailsElement.appendChild(breadcrumb);

        if (node.children.length) {
            const subTitle = document.createElement('h3');
            subTitle.textContent = '直屬組織';
            this.detailsElement.appendChild(subTitle);

            const list = document.createElement('ul');
            node.children.forEach((child) => {
                const item = document.createElement('li');
                item.textContent = child.name;
                list.appendChild(item);
            });
            this.detailsElement.appendChild(list);
        } else {
            const empty = document.createElement('p');
            empty.className = 'empty-state';
            empty.textContent = '沒有更下層的組織';
            this.detailsElement.appendChild(empty);
        }

        this.renderPeopleList(node);
    }

    renderPeopleList(node) {
        this.peopleListElement.innerHTML = '';

        if (!node.people.length) {
            const empty = document.createElement('p');
            empty.className = 'empty-state';
            empty.textContent = '此組織沒有登錄成員';
            this.peopleListElement.appendChild(empty);
            return;
        }

        node.people
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hant'))
            .forEach((person) => {
                const fragment = this.personTemplate.content.cloneNode(true);
                const checkbox = fragment.querySelector('input[type="checkbox"]');
                const nameSpan = fragment.querySelector('.person-name');
                const titleSpan = fragment.querySelector('.person-title');
                const emailLink = fragment.querySelector('.person-email');

                nameSpan.textContent = person.name;
                titleSpan.textContent = person.title || '職稱未提供';
                emailLink.textContent = person.email;
                emailLink.href = `mailto:${person.email}`;

                const includedByOrg = this.isOrgSelected(person.organization_id);
                const manuallySelected = this.selectedPersonIds.has(person.id);

                checkbox.checked = includedByOrg || manuallySelected;
                checkbox.disabled = includedByOrg;
                checkbox.title = includedByOrg
                    ? '已透過所屬組織自動選取'
                    : '點擊選取此成員';

                if (!includedByOrg) {
                    checkbox.addEventListener('change', (event) => {
                        this.onPersonCheckboxChange(person.id, event.target.checked);
                    });
                }

                this.peopleListElement.appendChild(fragment);
            });
    }

    updateSelectionSummary() {
        this.selectedOrgsElement.innerHTML = '';
        this.selectedPeopleElement.innerHTML = '';

        const displayOrgIds = [...this.selectedOrgIds].filter((orgId) => {
            const parentId = this.parentMap.get(orgId);
            return !parentId || !this.selectedOrgIds.has(parentId);
        });

        if (!displayOrgIds.length) {
            const empty = document.createElement('li');
            empty.className = 'empty-state';
            empty.textContent = '尚未選取任何組織';
            this.selectedOrgsElement.appendChild(empty);
        } else {
            displayOrgIds
                .map((orgId) => this.nodeMap.get(orgId))
                .filter(Boolean)
                .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hant'))
                .forEach((node) => {
                    const item = document.createElement('li');
                    item.textContent = node.name;
                    this.selectedOrgsElement.appendChild(item);
                });
        }

        const peopleMap = new Map();
        this.selectedOrgIds.forEach((orgId) => {
            const people = this.collectPeopleForOrg(orgId);
            people.forEach((person) => {
                const existing = peopleMap.get(person.id) || {
                    person,
                    viaOrg: false,
                    manual: false,
                };
                existing.viaOrg = true;
                peopleMap.set(person.id, existing);
            });
        });

        this.selectedPersonIds.forEach((personId) => {
            const person = this.personMap.get(personId);
            if (!person) {
                return;
            }
            const existing = peopleMap.get(personId) || {
                person,
                viaOrg: false,
                manual: false,
            };
            existing.manual = true;
            peopleMap.set(personId, existing);
        });

        if (!peopleMap.size) {
            const empty = document.createElement('li');
            empty.className = 'empty-state';
            empty.textContent = '尚未選取任何人員';
            this.selectedPeopleElement.appendChild(empty);
        } else {
            [...peopleMap.values()]
                .sort((a, b) => a.person.name.localeCompare(b.person.name, 'zh-Hant'))
                .forEach(({ person, viaOrg, manual }) => {
                    const item = document.createElement('li');
                    const label = document.createElement('span');
                    label.textContent = `${person.name}（${person.email}）`;
                    item.appendChild(label);

                    if (viaOrg) {
                        const badge = document.createElement('span');
                        badge.className = 'badge';
                        badge.textContent = '來自組織';
                        item.appendChild(badge);
                    }

                    if (manual && !viaOrg) {
                        const badge = document.createElement('span');
                        badge.className = 'badge';
                        badge.textContent = '個別選取';
                        item.appendChild(badge);
                    }

                    this.selectedPeopleElement.appendChild(item);
                });
        }
    }

    onOrgCheckboxChange(orgId, checked) {
        const affectedOrgIds = this.getDescendantOrgIds(orgId);
        if (checked) {
            affectedOrgIds.forEach((id) => this.selectedOrgIds.add(id));
        } else {
            affectedOrgIds.forEach((id) => this.selectedOrgIds.delete(id));
        }
        this.render();
    }

    onPersonCheckboxChange(personId, checked) {
        if (checked) {
            this.selectedPersonIds.add(personId);
        } else {
            this.selectedPersonIds.delete(personId);
        }
        this.renderDetails();
        this.updateSelectionSummary();
    }

    toggleExpand(orgId) {
        if (this.expandedOrgIds.has(orgId)) {
            this.expandedOrgIds.delete(orgId);
        } else {
            this.expandedOrgIds.add(orgId);
        }
        this.renderTree();
    }

    showOrganization(orgId) {
        if (!this.nodeMap.has(orgId)) {
            return;
        }
        this.currentOrgId = orgId;
        this.expandAncestors(orgId);
        this.render();
    }

    expandAncestors(orgId) {
        let current = orgId;
        while (current !== undefined && current !== null) {
            this.expandedOrgIds.add(current);
            current = this.parentMap.get(current);
        }
    }

    getOrgSelectionState(orgId) {
        if (this.selectedOrgIds.has(orgId)) {
            return 'checked';
        }
        const children = this.childMap.get(orgId) || [];
        const hasSelectedChild = children.some((childId) =>
            this.selectedOrgIds.has(childId)
        );
        return hasSelectedChild ? 'indeterminate' : 'unchecked';
    }

    getDescendantOrgIds(orgId) {
        const ids = [orgId];
        const children = this.childMap.get(orgId) || [];
        children.forEach((childId) => {
            ids.push(...this.getDescendantOrgIds(childId));
        });
        return ids;
    }

    collectPeopleForOrg(orgId) {
        const node = this.nodeMap.get(orgId);
        if (!node) {
            return [];
        }
        const collected = [...node.people];
        node.children.forEach((child) => {
            collected.push(...this.collectPeopleForOrg(child.id));
        });
        return collected;
    }

    buildBreadcrumb(orgId) {
        const breadcrumb = [];
        let current = orgId;
        while (current !== undefined && current !== null) {
            const node = this.nodeMap.get(current);
            if (!node) {
                break;
            }
            breadcrumb.unshift(node.name);
            current = this.parentMap.get(current);
        }
        return breadcrumb;
    }

    isOrgSelected(orgId) {
        return this.selectedOrgIds.has(orgId);
    }

    showError(message) {
        this.treeElement.innerHTML = '';
        const error = document.createElement('p');
        error.className = 'empty-state';
        error.textContent = `載入資料時發生錯誤：${message}`;
        this.treeElement.appendChild(error);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    new OrganizationExplorer();
});
