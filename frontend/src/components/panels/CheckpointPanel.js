/**
 * CheckpointPanel - 检查点设定面板组件
 * 管理检查点问题配置
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 本地存储键
const STORAGE_KEY = 'pdf_ocr_checkpoints';

// 默认检查点
const DEFAULT_CHECKPOINTS = [
    { id: 'cp1', question: '文档中的主要金额是多少？', enabled: true },
    { id: 'cp2', question: '文档的日期是什么？', enabled: true },
    { id: 'cp3', question: '文档涉及的主要当事方有哪些？', enabled: true }
];

export class CheckpointPanel {
    constructor(container) {
        this.container = container;
        this.checkpoints = [];
        this.isEditing = false;
        this.editingId = null;
    }

    /**
     * 初始化面板
     */
    init() {
        this.loadCheckpoints();
        this.render();
        this.bindEvents();
    }

    /**
     * 加载检查点配置
     */
    loadCheckpoints() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                this.checkpoints = JSON.parse(saved);
            } else {
                this.checkpoints = [...DEFAULT_CHECKPOINTS];
            }
        } catch (error) {
            console.error('Load checkpoints error:', error);
            this.checkpoints = [...DEFAULT_CHECKPOINTS];
        }
    }

    /**
     * 保存检查点配置
     */
    saveCheckpoints() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(this.checkpoints));
        } catch (error) {
            console.error('Save checkpoints error:', error);
        }
    }

    /**
     * 渲染面板
     */
    render() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="checkpoint-panel">
                <div class="checkpoint-panel-header">
                    <h4>✅ 检查点配置</h4>
                    <button class="add-checkpoint-btn" id="addCheckpointBtn">+ 新增</button>
                </div>
                <div class="checkpoint-list" id="checkpointPanelList">
                    ${this.renderCheckpointList()}
                </div>
                <div class="checkpoint-editor" id="checkpointEditor" style="display: none;">
                    ${this.renderEditor()}
                </div>
                <div class="checkpoint-actions">
                    <button class="reset-btn" id="resetCheckpointsBtn">恢复默认</button>
                </div>
            </div>
        `;
    }

    /**
     * 渲染检查点列表
     */
    renderCheckpointList() {
        if (this.checkpoints.length === 0) {
            return '<div class="empty-message">暂无检查点配置</div>';
        }
        
        return this.checkpoints.map((cp, idx) => `
            <div class="checkpoint-item ${cp.enabled ? '' : 'disabled'}" data-checkpoint-id="${cp.id}">
                <div class="checkpoint-toggle">
                    <input type="checkbox" ${cp.enabled ? 'checked' : ''} data-action="toggle" data-id="${cp.id}">
                </div>
                <div class="checkpoint-info">
                    <span class="checkpoint-index">#${idx + 1}</span>
                    <span class="checkpoint-question">${cp.question}</span>
                </div>
                <div class="checkpoint-actions">
                    <button class="edit-btn" data-action="edit" data-id="${cp.id}">✏️</button>
                    <button class="delete-btn" data-action="delete" data-id="${cp.id}">🗑</button>
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
                    <label>检查点问题</label>
                    <textarea id="checkpointQuestionInput" rows="3" placeholder="输入检查点问题，例如：文档中的金额是多少？"></textarea>
                </div>
                <div class="editor-actions">
                    <button class="cancel-btn" id="cancelCheckpointBtn">取消</button>
                    <button class="save-btn" id="saveCheckpointBtn">保存</button>
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
        const addBtn = this.container.querySelector('#addCheckpointBtn');
        if (addBtn) {
            addBtn.onclick = () => this.showEditor();
        }
        
        // 列表事件委托
        this.container.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            const id = e.target.dataset.id;
            
            if (action === 'edit') {
                this.editCheckpoint(id);
            } else if (action === 'delete') {
                this.deleteCheckpoint(id);
            }
        });
        
        // 切换启用状态
        this.container.addEventListener('change', (e) => {
            if (e.target.dataset.action === 'toggle') {
                const id = e.target.dataset.id;
                this.toggleCheckpoint(id, e.target.checked);
            }
        });
        
        // 取消编辑
        const cancelBtn = this.container.querySelector('#cancelCheckpointBtn');
        if (cancelBtn) {
            cancelBtn.onclick = () => this.hideEditor();
        }
        
        // 保存检查点
        const saveBtn = this.container.querySelector('#saveCheckpointBtn');
        if (saveBtn) {
            saveBtn.onclick = () => this.saveCheckpoint();
        }
        
        // 恢复默认
        const resetBtn = this.container.querySelector('#resetCheckpointsBtn');
        if (resetBtn) {
            resetBtn.onclick = () => this.resetToDefault();
        }
    }

    /**
     * 显示编辑器
     */
    showEditor(checkpoint = null) {
        this.isEditing = true;
        this.editingId = checkpoint?.id || null;
        
        const editor = this.container.querySelector('#checkpointEditor');
        const list = this.container.querySelector('#checkpointPanelList');
        
        if (editor) editor.style.display = 'block';
        if (list) list.style.display = 'none';
        
        // 填充数据
        const questionInput = this.container.querySelector('#checkpointQuestionInput');
        if (questionInput) {
            questionInput.value = checkpoint?.question || '';
        }
    }

    /**
     * 隐藏编辑器
     */
    hideEditor() {
        this.isEditing = false;
        this.editingId = null;
        
        const editor = this.container.querySelector('#checkpointEditor');
        const list = this.container.querySelector('#checkpointPanelList');
        
        if (editor) editor.style.display = 'none';
        if (list) list.style.display = 'block';
    }

    /**
     * 编辑检查点
     */
    editCheckpoint(id) {
        const checkpoint = this.checkpoints.find(cp => cp.id === id);
        if (checkpoint) {
            this.showEditor(checkpoint);
        }
    }

    /**
     * 保存检查点
     */
    saveCheckpoint() {
        const questionInput = this.container.querySelector('#checkpointQuestionInput');
        const question = questionInput?.value?.trim();
        
        if (!question) {
            alert('请输入检查点问题');
            return;
        }
        
        if (this.editingId) {
            // 更新现有检查点
            const index = this.checkpoints.findIndex(cp => cp.id === this.editingId);
            if (index !== -1) {
                this.checkpoints[index].question = question;
            }
        } else {
            // 新增检查点
            const newCheckpoint = {
                id: 'cp_' + Date.now(),
                question,
                enabled: true
            };
            this.checkpoints.push(newCheckpoint);
        }
        
        this.saveCheckpoints();
        this.hideEditor();
        this.render();
        this.bindEvents();
        
        eventBus.emit(EVENTS.CHECKPOINT_CONFIG_CHANGED);
    }

    /**
     * 删除检查点
     */
    deleteCheckpoint(id) {
        const checkpoint = this.checkpoints.find(cp => cp.id === id);
        if (!checkpoint) return;
        
        if (!confirm(`确定删除检查点 "${checkpoint.question.substring(0, 30)}..."？`)) return;
        
        this.checkpoints = this.checkpoints.filter(cp => cp.id !== id);
        this.saveCheckpoints();
        this.render();
        this.bindEvents();
        
        eventBus.emit(EVENTS.CHECKPOINT_CONFIG_CHANGED);
    }

    /**
     * 切换检查点启用状态
     */
    toggleCheckpoint(id, enabled) {
        const checkpoint = this.checkpoints.find(cp => cp.id === id);
        if (checkpoint) {
            checkpoint.enabled = enabled;
            this.saveCheckpoints();
            
            // 更新 UI
            const item = this.container.querySelector(`.checkpoint-item[data-checkpoint-id="${id}"]`);
            if (item) {
                item.classList.toggle('disabled', !enabled);
            }
            
            eventBus.emit(EVENTS.CHECKPOINT_CONFIG_CHANGED);
        }
    }

    /**
     * 恢复默认配置
     */
    resetToDefault() {
        if (!confirm('确定恢复默认检查点配置？自定义配置将被清除。')) return;
        
        this.checkpoints = [...DEFAULT_CHECKPOINTS];
        this.saveCheckpoints();
        this.render();
        this.bindEvents();
        
        eventBus.emit(EVENTS.CHECKPOINT_CONFIG_CHANGED);
    }

    /**
     * 获取启用的检查点
     */
    getEnabledCheckpoints() {
        return this.checkpoints.filter(cp => cp.enabled);
    }

    /**
     * 获取所有检查点
     */
    getAllCheckpoints() {
        return this.checkpoints;
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.CheckpointPanel = CheckpointPanel;
}
