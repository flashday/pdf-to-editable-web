/**
 * TemplatePanel - 关键词模板面板组件
 * 管理数据提取模板
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 本地存储键
const STORAGE_KEY = 'pdf_ocr_templates';

// 预设模板
const PRESET_TEMPLATES = [
    {
        id: 'invoice',
        name: '发票',
        fields: ['发票号码', '发票代码', '开票日期', '购买方名称', '销售方名称', '金额', '税额', '价税合计'],
        isPreset: true
    },
    {
        id: 'contract',
        name: '合同',
        fields: ['合同编号', '甲方', '乙方', '签订日期', '合同金额', '有效期'],
        isPreset: true
    },
    {
        id: 'id_card',
        name: '身份证',
        fields: ['姓名', '性别', '民族', '出生日期', '住址', '身份证号码'],
        isPreset: true
    },
    {
        id: 'receipt',
        name: '收据',
        fields: ['收据编号', '日期', '付款人', '收款人', '金额', '事由'],
        isPreset: true
    }
];

export class TemplatePanel {
    constructor(container) {
        this.container = container;
        this.templates = [];
        this.selectedTemplate = null;
        this.isEditing = false;
        this.editingId = null;
    }

    /**
     * 初始化面板
     */
    init() {
        this.loadTemplates();
        this.render();
        this.bindEvents();
    }

    /**
     * 加载模板
     */
    loadTemplates() {
        // 加载预设模板
        this.templates = [...PRESET_TEMPLATES];
        
        // 加载自定义模板
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const customTemplates = JSON.parse(saved);
                this.templates = [...this.templates, ...customTemplates];
            }
        } catch (error) {
            console.error('Load templates error:', error);
        }
    }

    /**
     * 保存自定义模板到本地存储
     */
    saveTemplates() {
        const customTemplates = this.templates.filter(t => !t.isPreset);
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(customTemplates));
        } catch (error) {
            console.error('Save templates error:', error);
        }
    }

    /**
     * 渲染面板
     */
    render() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="template-panel">
                <div class="template-panel-header">
                    <h4>📋 提取模板</h4>
                    <button class="add-template-btn" id="addTemplateBtn">+ 新增</button>
                </div>
                <div class="template-list" id="templatePanelList">
                    ${this.renderTemplateList()}
                </div>
                <div class="template-editor" id="templateEditor" style="display: none;">
                    ${this.renderEditor()}
                </div>
            </div>
        `;
    }

    /**
     * 渲染模板列表
     */
    renderTemplateList() {
        return this.templates.map(template => `
            <div class="template-item ${this.selectedTemplate?.id === template.id ? 'selected' : ''}" 
                 data-template-id="${template.id}">
                <div class="template-info">
                    <span class="template-name">${template.name}</span>
                    <span class="template-fields-count">${template.fields.length} 字段</span>
                </div>
                <div class="template-actions">
                    ${!template.isPreset ? `
                        <button class="edit-btn" data-action="edit" data-id="${template.id}">✏️</button>
                        <button class="delete-btn" data-action="delete" data-id="${template.id}">🗑</button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * 渲染编辑器
     */
    renderEditor() {
        return `
            <div class="editor-content">
                <div class="form-group">
                    <label>模板名称</label>
                    <input type="text" id="templateNameInput" placeholder="输入模板名称">
                </div>
                <div class="form-group">
                    <label>提取字段（每行一个）</label>
                    <textarea id="templateFieldsInput" rows="6" placeholder="发票号码&#10;金额&#10;日期"></textarea>
                </div>
                <div class="editor-actions">
                    <button class="cancel-btn" id="cancelEditBtn">取消</button>
                    <button class="save-btn" id="saveTemplateBtn">保存</button>
                </div>
            </div>
        `;
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        if (!this.container) return;
        
        // 新增按钮
        const addBtn = this.container.querySelector('#addTemplateBtn');
        if (addBtn) {
            addBtn.onclick = () => this.showEditor();
        }
        
        // 模板项点击
        this.container.addEventListener('click', (e) => {
            const item = e.target.closest('.template-item');
            if (item && !e.target.closest('.template-actions')) {
                const id = item.dataset.templateId;
                this.selectTemplate(id);
            }
            
            // 编辑按钮
            if (e.target.dataset.action === 'edit') {
                const id = e.target.dataset.id;
                this.editTemplate(id);
            }
            
            // 删除按钮
            if (e.target.dataset.action === 'delete') {
                const id = e.target.dataset.id;
                this.deleteTemplate(id);
            }
        });
        
        // 取消编辑
        const cancelBtn = this.container.querySelector('#cancelEditBtn');
        if (cancelBtn) {
            cancelBtn.onclick = () => this.hideEditor();
        }
        
        // 保存模板
        const saveBtn = this.container.querySelector('#saveTemplateBtn');
        if (saveBtn) {
            saveBtn.onclick = () => this.saveTemplate();
        }
    }

    /**
     * 选择模板
     */
    selectTemplate(id) {
        this.selectedTemplate = this.templates.find(t => t.id === id);
        
        // 更新 UI
        this.container.querySelectorAll('.template-item').forEach(item => {
            item.classList.toggle('selected', item.dataset.templateId === id);
        });
        
        // 保存到状态
        stateManager.set('selectedTemplate', this.selectedTemplate);
        
        // 发布事件
        eventBus.emit(EVENTS.TEMPLATE_SELECTED, this.selectedTemplate);
    }

    /**
     * 显示编辑器
     */
    showEditor(template = null) {
        this.isEditing = true;
        this.editingId = template?.id || null;
        
        const editor = this.container.querySelector('#templateEditor');
        const list = this.container.querySelector('#templatePanelList');
        
        if (editor) editor.style.display = 'block';
        if (list) list.style.display = 'none';
        
        // 填充数据
        const nameInput = this.container.querySelector('#templateNameInput');
        const fieldsInput = this.container.querySelector('#templateFieldsInput');
        
        if (nameInput) nameInput.value = template?.name || '';
        if (fieldsInput) fieldsInput.value = template?.fields?.join('\n') || '';
    }

    /**
     * 隐藏编辑器
     */
    hideEditor() {
        this.isEditing = false;
        this.editingId = null;
        
        const editor = this.container.querySelector('#templateEditor');
        const list = this.container.querySelector('#templatePanelList');
        
        if (editor) editor.style.display = 'none';
        if (list) list.style.display = 'block';
    }

    /**
     * 编辑模板
     */
    editTemplate(id) {
        const template = this.templates.find(t => t.id === id);
        if (template && !template.isPreset) {
            this.showEditor(template);
        }
    }

    /**
     * 保存模板
     */
    saveTemplate() {
        const nameInput = this.container.querySelector('#templateNameInput');
        const fieldsInput = this.container.querySelector('#templateFieldsInput');
        
        const name = nameInput?.value?.trim();
        const fields = fieldsInput?.value?.split('\n').map(f => f.trim()).filter(f => f);
        
        if (!name) {
            alert('请输入模板名称');
            return;
        }
        
        if (fields.length === 0) {
            alert('请输入至少一个提取字段');
            return;
        }
        
        if (this.editingId) {
            // 更新现有模板
            const index = this.templates.findIndex(t => t.id === this.editingId);
            if (index !== -1) {
                this.templates[index] = {
                    ...this.templates[index],
                    name,
                    fields
                };
            }
        } else {
            // 新增模板
            const newTemplate = {
                id: 'custom_' + Date.now(),
                name,
                fields,
                isPreset: false
            };
            this.templates.push(newTemplate);
        }
        
        this.saveTemplates();
        this.hideEditor();
        this.render();
        this.bindEvents();
        
        eventBus.emit(EVENTS.TEMPLATE_SAVED);
    }

    /**
     * 删除模板
     */
    deleteTemplate(id) {
        const template = this.templates.find(t => t.id === id);
        if (!template || template.isPreset) return;
        
        if (!confirm(`确定删除模板 "${template.name}"？`)) return;
        
        this.templates = this.templates.filter(t => t.id !== id);
        this.saveTemplates();
        this.render();
        this.bindEvents();
        
        eventBus.emit(EVENTS.TEMPLATE_DELETED, { id });
    }

    /**
     * 获取所有模板
     */
    getTemplates() {
        return this.templates;
    }

    /**
     * 获取选中的模板
     */
    getSelectedTemplate() {
        return this.selectedTemplate;
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.TemplatePanel = TemplatePanel;
}
