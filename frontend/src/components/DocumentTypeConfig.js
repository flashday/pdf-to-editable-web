/**
 * DocumentTypeConfig.js - 单据类型配置弹窗组件
 * 
 * 功能：
 * - 定义单据类型（发票、合同、收据等）
 * - 对每种单据类型定义关键词提取模板
 * - 对每种单据类型定义检查点问题
 */

class DocumentTypeConfig {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: options.apiBaseUrl || '',
            onSave: options.onSave || null,
            onClose: options.onClose || null,
            ...options
        };
        
        this.documentTypes = [];
        this.selectedTypeId = null;
        this.isVisible = false;
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        this.createModal();
        this.addStyles();
        await this.loadDocumentTypes();
    }
    
    createModal() {
        // 创建遮罩
        if (!document.getElementById('docTypeConfigOverlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'docTypeConfigOverlay';
            overlay.className = 'doc-type-overlay';
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) this.hide();
            });
            document.body.appendChild(overlay);
        }
        
        // 创建弹窗容器
        if (!document.getElementById('docTypeConfigModal')) {
            const modal = document.createElement('div');
            modal.id = 'docTypeConfigModal';
            modal.className = 'doc-type-modal';
            document.body.appendChild(modal);
        }
    }
    
    addStyles() {
        if (document.getElementById('doc-type-config-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'doc-type-config-styles';
        style.textContent = `
            .doc-type-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                z-index: 2000;
                display: none;
            }
            
            .doc-type-overlay.visible {
                display: block;
            }
            
            .doc-type-modal {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 700px;
                max-width: 90vw;
                max-height: 85vh;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                z-index: 2001;
                display: none;
                overflow: hidden;
            }
            
            .doc-type-modal.visible {
                display: block;
            }
            
            .doc-type-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .doc-type-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .doc-type-close-btn {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                opacity: 0.8;
                transition: opacity 0.2s;
            }
            
            .doc-type-close-btn:hover {
                opacity: 1;
            }
            
            .doc-type-body {
                display: flex;
                height: calc(85vh - 140px);
                max-height: 500px;
            }
            
            .doc-type-sidebar {
                width: 180px;
                background: #f8f9fa;
                border-right: 1px solid #e9ecef;
                overflow-y: auto;
            }
            
            .doc-type-list {
                padding: 10px;
            }
            
            .doc-type-item {
                padding: 10px 12px;
                margin-bottom: 4px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .doc-type-item:hover {
                background: #e9ecef;
            }
            
            .doc-type-item.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .doc-type-item .delete-btn {
                opacity: 0;
                background: none;
                border: none;
                color: inherit;
                cursor: pointer;
                padding: 2px 6px;
                font-size: 12px;
            }
            
            .doc-type-item:hover .delete-btn {
                opacity: 0.6;
            }
            
            .doc-type-item .delete-btn:hover {
                opacity: 1;
            }
            
            .doc-type-add-btn {
                width: calc(100% - 20px);
                margin: 10px;
                padding: 8px;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: background 0.2s;
            }
            
            .doc-type-add-btn:hover {
                background: #218838;
            }
            
            .doc-type-content {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }
            
            .doc-type-section {
                margin-bottom: 20px;
            }
            
            .doc-type-section h4 {
                margin: 0 0 10px 0;
                font-size: 14px;
                color: #333;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .doc-type-section h4 .icon {
                font-size: 16px;
            }
            
            .doc-type-input {
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.2s;
            }
            
            .doc-type-input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .doc-type-textarea {
                width: 100%;
                min-height: 120px;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.5;
                resize: vertical;
                font-family: inherit;
            }
            
            .doc-type-textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .doc-type-hint {
                font-size: 12px;
                color: #666;
                margin-top: 6px;
            }
            
            .doc-type-footer {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 16px 20px;
                background: #f8f9fa;
                border-top: 1px solid #e9ecef;
            }
            
            .doc-type-btn {
                padding: 10px 24px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .doc-type-btn-cancel {
                background: #6c757d;
                color: white;
            }
            
            .doc-type-btn-cancel:hover {
                background: #5a6268;
            }
            
            .doc-type-btn-save {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
            }
            
            .doc-type-btn-save:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
            }
            
            .doc-type-btn-save:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .doc-type-empty {
                text-align: center;
                padding: 40px 20px;
                color: #666;
            }
            
            .doc-type-loading {
                text-align: center;
                padding: 40px 20px;
                color: #666;
            }
        `;
        document.head.appendChild(style);
    }
    
    async loadDocumentTypes() {
        this.isLoading = true;
        this.renderLoading();
        
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/document-types`);
            const data = await response.json();
            
            if (data.success) {
                this.documentTypes = data.data;
                if (this.documentTypes.length > 0 && !this.selectedTypeId) {
                    this.selectedTypeId = this.documentTypes[0].id;
                }
            }
        } catch (error) {
            console.error('Failed to load document types:', error);
        } finally {
            this.isLoading = false;
            if (this.isVisible) {
                this.render();
            }
        }
    }
    
    show() {
        this.isVisible = true;
        document.getElementById('docTypeConfigOverlay').classList.add('visible');
        document.getElementById('docTypeConfigModal').classList.add('visible');
        this.render();
    }
    
    hide() {
        this.isVisible = false;
        document.getElementById('docTypeConfigOverlay').classList.remove('visible');
        document.getElementById('docTypeConfigModal').classList.remove('visible');
        
        if (this.options.onClose) {
            this.options.onClose();
        }
    }
    
    renderLoading() {
        const modal = document.getElementById('docTypeConfigModal');
        modal.innerHTML = `
            <div class="doc-type-header">
                <h3>📋 单据设定</h3>
                <button class="doc-type-close-btn" onclick="window.docTypeConfig.hide()">✕</button>
            </div>
            <div class="doc-type-loading">
                <p>加载中...</p>
            </div>
        `;
    }
    
    render() {
        if (this.isLoading) {
            this.renderLoading();
            return;
        }
        
        const modal = document.getElementById('docTypeConfigModal');
        const selectedType = this.documentTypes.find(t => t.id === this.selectedTypeId);
        
        modal.innerHTML = `
            <div class="doc-type-header">
                <h3>📋 单据设定</h3>
                <button class="doc-type-close-btn" onclick="window.docTypeConfig.hide()">✕</button>
            </div>
            <div class="doc-type-body">
                <div class="doc-type-sidebar">
                    <div class="doc-type-list">
                        ${this.documentTypes.map(type => `
                            <div class="doc-type-item ${type.id === this.selectedTypeId ? 'active' : ''}" 
                                 data-type-id="${type.id}">
                                <span>${type.name}</span>
                                ${!type.is_default ? `<button class="delete-btn" data-delete-id="${type.id}" title="删除">✕</button>` : ''}
                            </div>
                        `).join('')}
                    </div>
                    <button class="doc-type-add-btn" id="addDocTypeBtn">+ 新增单据类型</button>
                </div>
                <div class="doc-type-content">
                    ${selectedType ? this.renderTypeEditor(selectedType) : this.renderEmpty()}
                </div>
            </div>
            <div class="doc-type-footer">
                <button class="doc-type-btn doc-type-btn-cancel" onclick="window.docTypeConfig.hide()">取消</button>
                <button class="doc-type-btn doc-type-btn-save" id="saveDocTypeBtn" ${!selectedType ? 'disabled' : ''}>保存</button>
            </div>
        `;
        
        this.bindEvents();
    }
    
    renderTypeEditor(type) {
        return `
            <div class="doc-type-section">
                <h4><span class="icon">📝</span> 单据名称</h4>
                <input type="text" class="doc-type-input" id="docTypeName" value="${type.name}" 
                       ${type.is_default ? 'readonly' : ''} placeholder="输入单据类型名称">
            </div>
            
            <div class="doc-type-section">
                <h4><span class="icon">🔑</span> 关键词提取字段</h4>
                <textarea class="doc-type-textarea" id="docTypeFields" placeholder="每行一个字段名，例如：&#10;发票号码&#10;金额&#10;日期">${(type.fields || []).join('\n')}</textarea>
                <p class="doc-type-hint">每行输入一个要提取的字段名称，系统将根据这些字段从文档中提取信息</p>
            </div>
            
            <div class="doc-type-section">
                <h4><span class="icon">✅</span> 检查点问题</h4>
                <textarea class="doc-type-textarea" id="docTypeCheckpoints" placeholder="每行一个检查点问题，例如：&#10;发票号码是多少？&#10;金额合计是多少？">${(type.checkpoints || []).join('\n')}</textarea>
                <p class="doc-type-hint">每行输入一个验证问题，系统将基于文档内容回答这些问题进行数据校验</p>
            </div>
        `;
    }
    
    renderEmpty() {
        return `
            <div class="doc-type-empty">
                <p>请从左侧选择一个单据类型进行编辑</p>
                <p>或点击"新增单据类型"创建新的类型</p>
            </div>
        `;
    }
    
    bindEvents() {
        // 选择单据类型
        document.querySelectorAll('.doc-type-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('delete-btn')) return;
                this.selectedTypeId = item.dataset.typeId;
                this.render();
            });
        });
        
        // 删除按钮
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteType(btn.dataset.deleteId);
            });
        });
        
        // 新增按钮
        const addBtn = document.getElementById('addDocTypeBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddDialog());
        }
        
        // 保存按钮
        const saveBtn = document.getElementById('saveDocTypeBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveCurrentType());
        }
    }
    
    showAddDialog() {
        const name = prompt('请输入新单据类型名称：');
        if (!name || !name.trim()) return;
        
        const id = name.trim().toLowerCase()
            .replace(/[\u4e00-\u9fa5]/g, (char) => {
                // 简单的中文转拼音映射
                const map = {'发':'fa','票':'piao','合':'he','同':'tong','收':'shou','据':'ju','身':'shen','份':'fen','证':'zheng','报':'bao','告':'gao','单':'dan'};
                return map[char] || char;
            })
            .replace(/[^a-z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        
        this.createType({
            id: id || 'custom_' + Date.now(),
            name: name.trim(),
            fields: [],
            checkpoints: []
        });
    }
    
    async createType(typeData) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/document-types`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(typeData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.documentTypes.push(data.data);
                this.selectedTypeId = data.data.id;
                this.render();
            } else {
                alert('创建失败: ' + data.error);
            }
        } catch (error) {
            console.error('Create type error:', error);
            alert('创建失败: ' + error.message);
        }
    }
    
    async saveCurrentType() {
        if (!this.selectedTypeId) return;
        
        const nameInput = document.getElementById('docTypeName');
        const fieldsInput = document.getElementById('docTypeFields');
        const checkpointsInput = document.getElementById('docTypeCheckpoints');
        
        const updateData = {
            name: nameInput.value.trim(),
            fields: fieldsInput.value.split('\n').map(f => f.trim()).filter(f => f),
            checkpoints: checkpointsInput.value.split('\n').map(c => c.trim()).filter(c => c)
        };
        
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/document-types/${this.selectedTypeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新本地数据
                const index = this.documentTypes.findIndex(t => t.id === this.selectedTypeId);
                if (index !== -1) {
                    this.documentTypes[index] = { ...this.documentTypes[index], ...updateData };
                }
                
                // 触发保存回调
                if (this.options.onSave) {
                    this.options.onSave(data.data);
                }
                
                alert('保存成功！');
                this.render();
            } else {
                alert('保存失败: ' + data.error);
            }
        } catch (error) {
            console.error('Save type error:', error);
            alert('保存失败: ' + error.message);
        }
    }
    
    async deleteType(typeId) {
        if (!confirm('确定要删除这个单据类型吗？')) return;
        
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/document-types/${typeId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.documentTypes = this.documentTypes.filter(t => t.id !== typeId);
                if (this.selectedTypeId === typeId) {
                    this.selectedTypeId = this.documentTypes.length > 0 ? this.documentTypes[0].id : null;
                }
                this.render();
            } else {
                alert('删除失败: ' + data.error);
            }
        } catch (error) {
            console.error('Delete type error:', error);
            alert('删除失败: ' + error.message);
        }
    }
    
    // 获取当前选中的单据类型
    getSelectedType() {
        return this.documentTypes.find(t => t.id === this.selectedTypeId);
    }
    
    // 获取所有单据类型
    getAllTypes() {
        return this.documentTypes;
    }
    
    // 根据ID获取单据类型
    getTypeById(typeId) {
        return this.documentTypes.find(t => t.id === typeId);
    }
}

// 全局实例
let docTypeConfig = null;

// 初始化函数
function initDocumentTypeConfig(options = {}) {
    if (!docTypeConfig) {
        docTypeConfig = new DocumentTypeConfig(options);
        window.docTypeConfig = docTypeConfig;
    }
    return docTypeConfig;
}

// 显示单据设定弹窗
function showDocumentTypeConfig() {
    if (!docTypeConfig) {
        initDocumentTypeConfig();
    }
    docTypeConfig.show();
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DocumentTypeConfig, initDocumentTypeConfig, showDocumentTypeConfig };
}
