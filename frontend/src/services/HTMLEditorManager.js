/**
 * HTMLEditorManager - 管理基于 HTML 的可编辑内容
 * 
 * 方案 A+B 实现：
 * - 文本块：点击后内联编辑 (contenteditable)
 * - 表格：点击后弹出浮动编辑面板
 */
export class HTMLEditorManager {
    constructor() {
        this.container = null;
        this.currentEditingRegion = null;
        this.originalContent = new Map(); // 存储原始内容用于取消编辑
        this.modifiedRegions = new Map(); // 存储已修改的区域
        this.onRegionClick = null; // 区域点击回调
        this.onTableModified = null; // 表格修改回调
        this.tableEditorPanel = null;
    }

    /**
     * 初始化 HTML 编辑器
     * @param {string} containerId - 容器元素 ID
     */
    initialize(containerId = 'editor') {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('HTMLEditorManager: Container not found:', containerId);
            return;
        }
        
        // 添加编辑器样式
        this._injectStyles();
        
        // 创建表格编辑面板
        this._createTableEditorPanel();
        
        console.log('HTMLEditorManager initialized');
    }

    /**
     * 加载可编辑 HTML 内容
     * @param {string} htmlContent - HTML 内容
     */
    loadContent(htmlContent) {
        if (!this.container) {
            console.error('HTMLEditorManager: Container not initialized, attempting to initialize...');
            this.initialize('editor');
        }
        
        if (!this.container) {
            console.error('HTMLEditorManager: Failed to initialize container');
            return;
        }
        
        console.log('HTMLEditorManager: Loading content into container:', this.container.id);
        console.log('HTMLEditorManager: Content length:', htmlContent?.length || 0);
        
        this.container.innerHTML = htmlContent;
        
        // 绑定事件
        this._bindRegionEvents();
        
        // 验证加载结果
        const regions = this.container.querySelectorAll('.ocr-region');
        console.log('HTMLEditorManager: Loaded', regions.length, 'OCR regions');
    }

    /**
     * 注入编辑器样式
     */
    _injectStyles() {
        if (document.getElementById('html-editor-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'html-editor-styles';
        styles.textContent = `
            /* OCR 区域基础样式 */
            #editor .ocr-region {
                cursor: pointer;
                transition: all 0.2s ease;
                border-radius: 3px;
                position: relative;
                padding: 8px;
                margin: 5px 0;
                background: rgba(255, 255, 255, 0.9);
            }
            #editor .ocr-region:hover {
                background-color: rgba(255, 255, 255, 0.95);
                outline: 2px solid rgba(66, 133, 244, 0.5);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            #editor .ocr-region.selected {
                background-color: rgba(255, 255, 255, 0.98);
                outline: 2px solid #4285f4;
                box-shadow: 0 2px 12px rgba(66, 133, 244, 0.3);
            }
            #editor .ocr-region.editing {
                background-color: #fff;
                outline: 2px solid #4285f4;
                box-shadow: 0 4px 16px rgba(66, 133, 244, 0.4);
            }
            
            /* 文本区域样式 */
            .ocr-region.title {
                font-size: 1.3em;
                font-weight: bold;
                color: #1a1a1a;
            }
            .ocr-region.text-block {
                line-height: 1.6;
            }
            .ocr-region.header, .ocr-region.footer {
                font-size: 0.9em;
                color: #666;
            }
            .ocr-region.figure-caption, .ocr-region.table-caption {
                font-size: 0.9em;
                color: #666;
                text-align: center;
                font-style: italic;
            }
            .ocr-region.reference {
                font-size: 0.85em;
                color: #555;
            }
            .ocr-region.figure-placeholder {
                background: #f5f5f5;
                border: 1px dashed #ccc;
                text-align: center;
                color: #888;
                padding: 20px;
            }
            
            /* 表格区域样式 */
            .ocr-region.table-wrapper {
                overflow-x: auto;
            }
            .ocr-region.table-wrapper table {
                border-collapse: collapse;
                width: 100%;
                font-size: 0.9em;
            }
            .ocr-region.table-wrapper td,
            .ocr-region.table-wrapper th {
                border: 1px solid #ccc;
                padding: 6px 10px;
                text-align: left;
            }
            .ocr-region.table-wrapper th {
                background: #f5f5f5;
                font-weight: bold;
            }
            
            /* 可编辑内容样式 */
            .editable-content {
                display: block;
            }
            .editable-content[contenteditable="true"] {
                outline: none;
                background: rgba(255, 255, 255, 0.9);
                min-height: 1.5em;
            }
            
            /* 编辑工具栏 */
            .edit-toolbar {
                position: absolute;
                top: -32px;
                right: 0;
                background: #fff;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                display: none;
                z-index: 100;
                gap: 4px;
            }
            .ocr-region.editing .edit-toolbar {
                display: flex;
            }
            .edit-toolbar button {
                padding: 4px 10px;
                border: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
                transition: background 0.2s;
            }
            .edit-toolbar .save-btn {
                background: #4285f4;
                color: white;
            }
            .edit-toolbar .save-btn:hover {
                background: #3367d6;
            }
            .edit-toolbar .cancel-btn {
                background: #f1f1f1;
                color: #333;
            }
            .edit-toolbar .cancel-btn:hover {
                background: #e0e0e0;
            }
            
            /* 表格编辑面板 */
            .table-editor-panel {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);
                z-index: 1000;
                max-width: 90vw;
                max-height: 80vh;
                display: none;
                flex-direction: column;
            }
            .table-editor-panel.visible {
                display: flex;
            }
            .table-editor-header {
                padding: 12px 16px;
                background: #f5f5f5;
                border-bottom: 1px solid #ddd;
                border-radius: 8px 8px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .table-editor-header h3 {
                margin: 0;
                font-size: 1em;
            }
            .table-editor-content {
                padding: 16px;
                overflow: auto;
                flex: 1;
            }
            .table-editor-content table {
                border-collapse: collapse;
                width: 100%;
            }
            .table-editor-content td {
                border: 1px solid #ccc;
                padding: 8px;
                min-width: 80px;
            }
            .table-editor-content td[contenteditable="true"] {
                outline: none;
                background: #fffef0;
            }
            .table-editor-content td[contenteditable="true"]:focus {
                background: #fff8dc;
                outline: 2px solid #4285f4;
            }
            .table-editor-footer {
                padding: 12px 16px;
                background: #f5f5f5;
                border-top: 1px solid #ddd;
                border-radius: 0 0 8px 8px;
                display: flex;
                justify-content: flex-end;
                gap: 8px;
            }
            .table-editor-footer button {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            .table-editor-footer .save-btn {
                background: #4285f4;
                color: white;
            }
            .table-editor-footer .cancel-btn {
                background: #e0e0e0;
                color: #333;
            }
            
            /* 遮罩层 */
            .table-editor-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.3);
                z-index: 999;
                display: none;
            }
            .table-editor-overlay.visible {
                display: block;
            }
        `;
        document.head.appendChild(styles);
    }

    /**
     * 创建表格编辑面板
     */
    _createTableEditorPanel() {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'table-editor-overlay';
        overlay.id = 'tableEditorOverlay';
        overlay.onclick = () => this._closeTableEditor();
        document.body.appendChild(overlay);
        
        // 创建编辑面板
        const panel = document.createElement('div');
        panel.className = 'table-editor-panel';
        panel.id = 'tableEditorPanel';
        panel.innerHTML = `
            <div class="table-editor-header">
                <h3>📊 编辑表格</h3>
                <button onclick="window.htmlEditorManager._closeTableEditor()" style="background:none;border:none;font-size:18px;cursor:pointer;">✕</button>
            </div>
            <div class="table-editor-content" id="tableEditorContent">
                <!-- 表格内容将动态插入 -->
            </div>
            <div class="table-editor-footer">
                <button class="cancel-btn" onclick="window.htmlEditorManager._closeTableEditor()">取消</button>
                <button class="save-btn" onclick="window.htmlEditorManager._saveTableEdit()">保存</button>
            </div>
        `;
        document.body.appendChild(panel);
        
        this.tableEditorPanel = panel;
        
        // 暴露到全局以便 onclick 调用
        window.htmlEditorManager = this;
    }

    /**
     * 绑定区域事件
     */
    _bindRegionEvents() {
        const regions = this.container.querySelectorAll('.ocr-region');
        
        regions.forEach(region => {
            // 点击事件
            region.addEventListener('click', (e) => {
                e.stopPropagation();
                this._handleRegionClick(region);
            });
            
            // 双击进入编辑模式
            region.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                this._startEditing(region);
            });
        });
        
        // 点击空白处取消选择
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.ocr-region') && !e.target.closest('.table-editor-panel')) {
                this._clearSelection();
            }
        });
        
        // ESC 键取消编辑
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this._cancelCurrentEdit();
            }
        });
    }

    /**
     * 处理区域点击
     */
    _handleRegionClick(region) {
        // 清除之前的选择
        this.container.querySelectorAll('.ocr-region.selected').forEach(r => {
            r.classList.remove('selected');
        });
        
        // 选中当前区域
        region.classList.add('selected');
        
        // 触发回调（用于高亮左侧图像对应区域）
        if (this.onRegionClick) {
            const regionId = region.dataset.regionId;
            const bbox = JSON.parse(region.dataset.bbox || '{}');
            this.onRegionClick(regionId, bbox);
        }
    }

    /**
     * 开始编辑区域
     */
    _startEditing(region) {
        const regionType = region.dataset.regionType;
        const regionId = region.dataset.regionId;
        
        // 保存原始内容
        if (!this.originalContent.has(regionId)) {
            this.originalContent.set(regionId, region.innerHTML);
        }
        
        if (regionType === 'table') {
            this._openTableEditor(region);
        } else if (regionType === 'text') {
            this._startInlineEdit(region);
        }
    }

    /**
     * 开始内联编辑（文本块）
     */
    _startInlineEdit(region) {
        // 取消其他编辑
        this._cancelCurrentEdit();
        
        const editableContent = region.querySelector('.editable-content');
        if (!editableContent) return;
        
        // 添加编辑工具栏
        if (!region.querySelector('.edit-toolbar')) {
            const toolbar = document.createElement('div');
            toolbar.className = 'edit-toolbar';
            toolbar.innerHTML = `
                <button class="save-btn" onclick="window.htmlEditorManager._saveInlineEdit(this)">保存</button>
                <button class="cancel-btn" onclick="window.htmlEditorManager._cancelInlineEdit(this)">取消</button>
            `;
            region.insertBefore(toolbar, region.firstChild);
        }
        
        // 进入编辑模式
        region.classList.add('editing');
        editableContent.contentEditable = 'true';
        editableContent.focus();
        
        // 选中所有文本
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(editableContent);
        selection.removeAllRanges();
        selection.addRange(range);
        
        this.currentEditingRegion = region;
    }

    /**
     * 保存内联编辑
     */
    _saveInlineEdit(button) {
        const region = button.closest('.ocr-region');
        if (!region) return;
        
        const regionId = region.dataset.regionId;
        const editableContent = region.querySelector('.editable-content');
        
        // 记录修改
        this.modifiedRegions.set(regionId, {
            type: 'text',
            content: editableContent.textContent
        });
        
        // 退出编辑模式
        region.classList.remove('editing');
        editableContent.contentEditable = 'false';
        
        // 标记为已修改
        region.classList.add('modified');
        
        this.currentEditingRegion = null;
        
        console.log('Saved text edit for region:', regionId);
    }

    /**
     * 取消内联编辑
     */
    _cancelInlineEdit(button) {
        const region = button.closest('.ocr-region');
        if (!region) return;
        
        const regionId = region.dataset.regionId;
        const originalHtml = this.originalContent.get(regionId);
        
        if (originalHtml) {
            region.innerHTML = originalHtml;
            this._bindRegionEvents(); // 重新绑定事件
        }
        
        region.classList.remove('editing');
        this.currentEditingRegion = null;
    }

    /**
     * 打开表格编辑器
     */
    _openTableEditor(region) {
        const regionId = region.dataset.regionId;
        const tableHtml = region.innerHTML;
        
        // 保存当前编辑的区域引用
        this.currentEditingRegion = region;
        
        // 将表格内容复制到编辑面板
        const content = document.getElementById('tableEditorContent');
        content.innerHTML = tableHtml;
        
        // 使所有单元格可编辑
        content.querySelectorAll('td, th').forEach(cell => {
            cell.contentEditable = 'true';
        });
        
        // 显示面板
        document.getElementById('tableEditorOverlay').classList.add('visible');
        document.getElementById('tableEditorPanel').classList.add('visible');
    }

    /**
     * 关闭表格编辑器
     */
    _closeTableEditor() {
        document.getElementById('tableEditorOverlay').classList.remove('visible');
        document.getElementById('tableEditorPanel').classList.remove('visible');
        this.currentEditingRegion = null;
    }

    /**
     * 保存表格编辑
     */
    _saveTableEdit() {
        if (!this.currentEditingRegion) return;
        
        const regionId = this.currentEditingRegion.dataset.regionId;
        const content = document.getElementById('tableEditorContent');
        
        // 移除 contenteditable 属性
        content.querySelectorAll('td, th').forEach(cell => {
            cell.removeAttribute('contenteditable');
        });
        
        // 更新原区域内容
        this.currentEditingRegion.innerHTML = content.innerHTML;
        
        // 记录修改
        this.modifiedRegions.set(regionId, {
            type: 'table',
            content: content.innerHTML
        });
        
        // 标记为已修改
        this.currentEditingRegion.classList.add('modified');
        
        console.log('Saved table edit for region:', regionId);
        
        // 触发回调通知主应用
        if (this.onTableModified) {
            this.onTableModified(regionId, content.innerHTML);
        }
        
        this._closeTableEditor();
    }

    /**
     * 取消当前编辑
     */
    _cancelCurrentEdit() {
        if (this.currentEditingRegion) {
            const regionType = this.currentEditingRegion.dataset.regionType;
            
            if (regionType === 'table') {
                this._closeTableEditor();
            } else {
                const editableContent = this.currentEditingRegion.querySelector('.editable-content');
                if (editableContent) {
                    editableContent.contentEditable = 'false';
                }
                this.currentEditingRegion.classList.remove('editing');
            }
            
            this.currentEditingRegion = null;
        }
    }

    /**
     * 清除选择
     */
    _clearSelection() {
        this.container?.querySelectorAll('.ocr-region.selected').forEach(r => {
            r.classList.remove('selected');
        });
    }

    /**
     * 获取所有修改
     */
    getModifications() {
        return Object.fromEntries(this.modifiedRegions);
    }

    /**
     * 获取完整的 HTML 内容
     */
    getContent() {
        return this.container?.innerHTML || '';
    }

    /**
     * 设置区域点击回调
     */
    setRegionClickCallback(callback) {
        this.onRegionClick = callback;
    }
    
    /**
     * 设置表格修改回调
     */
    setTableModifiedCallback(callback) {
        this.onTableModified = callback;
    }
}
