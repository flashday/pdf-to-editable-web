/**
 * SmartExtract.js - 智能提取面板组件
 * 
 * 提供模板选择、自定义字段输入和提取结果显示功能
 */

class SmartExtractPanel {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            apiBaseUrl: options.apiBaseUrl || '',
            onExtract: options.onExtract || null,
            onClose: options.onClose || null,
            ...options
        };
        
        this.templates = {};
        this.customFields = [];
        this.currentJobId = null;
        this.isLoading = false;
        this.lastResult = null;
        
        this.init();
    }
    
    async init() {
        this.render();
        await this.loadTemplates();
        this.bindEvents();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="smart-extract-panel">
                <div class="panel-header">
                    <h3>🔍 智能信息提取</h3>
                    <button class="close-btn" title="关闭">&times;</button>
                </div>
                
                <div class="panel-body">
                    <!-- 模板选择 -->
                    <div class="section template-section">
                        <label>选择模板：</label>
                        <select id="template-select">
                            <option value="">-- 自定义字段 --</option>
                        </select>
                    </div>
                    
                    <!-- 字段列表 -->
                    <div class="section fields-section">
                        <label>提取字段：</label>
                        <div id="fields-container" class="fields-container">
                            <div class="field-tags" id="field-tags"></div>
                            <div class="field-input-wrapper">
                                <input type="text" id="custom-field-input" 
                                       placeholder="输入自定义字段，按回车添加" />
                                <button id="add-field-btn" class="add-btn">+</button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 提取按钮 -->
                    <div class="section action-section">
                        <button id="extract-btn" class="primary-btn" disabled>
                            <span class="btn-text">开始提取</span>
                            <span class="btn-loading" style="display:none;">提取中...</span>
                        </button>
                    </div>
                    
                    <!-- 结果显示 -->
                    <div class="section result-section" id="result-section" style="display:none;">
                        <div class="result-header">
                            <label>提取结果：</label>
                            <div class="result-actions">
                                <button id="copy-result-btn" class="small-btn" title="复制结果">📋</button>
                                <button id="export-result-btn" class="small-btn" title="导出 JSON">💾</button>
                            </div>
                        </div>
                        <div id="result-content" class="result-content"></div>
                        <div id="result-meta" class="result-meta"></div>
                    </div>
                    
                    <!-- 错误提示 -->
                    <div class="section error-section" id="error-section" style="display:none;">
                        <div class="error-message" id="error-message"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.addStyles();
    }
    
    addStyles() {
        if (document.getElementById('smart-extract-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'smart-extract-styles';
        style.textContent = `
            .smart-extract-panel {
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.15);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 400px;
                width: 100%;
            }
            
            .smart-extract-panel .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                background: #f8f9fa;
                border-radius: 8px 8px 0 0;
            }
            
            .smart-extract-panel .panel-header h3 {
                margin: 0;
                font-size: 16px;
                color: #333;
            }
            
            .smart-extract-panel .close-btn {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: #666;
                padding: 0 4px;
            }
            
            .smart-extract-panel .close-btn:hover {
                color: #333;
            }
            
            .smart-extract-panel .panel-body {
                padding: 16px;
            }
            
            .smart-extract-panel .section {
                margin-bottom: 16px;
            }
            
            .smart-extract-panel .section:last-child {
                margin-bottom: 0;
            }
            
            .smart-extract-panel label {
                display: block;
                font-size: 13px;
                font-weight: 500;
                color: #555;
                margin-bottom: 8px;
            }
            
            .smart-extract-panel select,
            .smart-extract-panel input[type="text"] {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }
            
            .smart-extract-panel select:focus,
            .smart-extract-panel input[type="text"]:focus {
                outline: none;
                border-color: #4a90d9;
                box-shadow: 0 0 0 2px rgba(74, 144, 217, 0.2);
            }
            
            .smart-extract-panel .fields-container {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                min-height: 80px;
            }
            
            .smart-extract-panel .field-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 8px;
            }
            
            .smart-extract-panel .field-tag {
                display: inline-flex;
                align-items: center;
                background: #e8f4fd;
                color: #1a73e8;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 13px;
            }
            
            .smart-extract-panel .field-tag .remove-tag {
                margin-left: 6px;
                cursor: pointer;
                font-size: 14px;
                opacity: 0.7;
            }
            
            .smart-extract-panel .field-tag .remove-tag:hover {
                opacity: 1;
            }
            
            .smart-extract-panel .field-input-wrapper {
                display: flex;
                gap: 8px;
            }
            
            .smart-extract-panel .field-input-wrapper input {
                flex: 1;
            }
            
            .smart-extract-panel .add-btn {
                padding: 8px 12px;
                background: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            
            .smart-extract-panel .add-btn:hover {
                background: #3a7bc8;
            }
            
            .smart-extract-panel .primary-btn {
                width: 100%;
                padding: 10px 16px;
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            .smart-extract-panel .primary-btn:hover:not(:disabled) {
                background: #1557b0;
            }
            
            .smart-extract-panel .primary-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            
            .smart-extract-panel .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .smart-extract-panel .result-actions {
                display: flex;
                gap: 4px;
            }
            
            .smart-extract-panel .small-btn {
                padding: 4px 8px;
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            
            .smart-extract-panel .small-btn:hover {
                background: #e0e0e0;
            }
            
            .smart-extract-panel .result-content {
                background: #f8f9fa;
                border: 1px solid #eee;
                border-radius: 4px;
                padding: 12px;
                font-size: 13px;
                max-height: 200px;
                overflow-y: auto;
            }
            
            .smart-extract-panel .result-item {
                display: flex;
                padding: 6px 0;
                border-bottom: 1px solid #eee;
            }
            
            .smart-extract-panel .result-item:last-child {
                border-bottom: none;
            }
            
            .smart-extract-panel .result-key {
                font-weight: 500;
                color: #555;
                min-width: 100px;
            }
            
            .smart-extract-panel .result-value {
                color: #333;
                flex: 1;
            }
            
            .smart-extract-panel .result-value.null {
                color: #999;
                font-style: italic;
            }
            
            .smart-extract-panel .result-meta {
                margin-top: 8px;
                font-size: 12px;
                color: #888;
            }
            
            .smart-extract-panel .error-message {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #dc2626;
                padding: 10px 12px;
                border-radius: 4px;
                font-size: 13px;
            }
        `;
        document.head.appendChild(style);
    }
    
    async loadTemplates() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/templates`);
            const data = await response.json();
            
            if (data.success && data.data.templates) {
                this.templates = data.data.templates;
                this.renderTemplateOptions();
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }
    
    renderTemplateOptions() {
        const select = this.container.querySelector('#template-select');
        
        Object.entries(this.templates).forEach(([id, template]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${template.name} (${template.name_en})`;
            select.appendChild(option);
        });
    }
    
    bindEvents() {
        // 关闭按钮
        this.container.querySelector('.close-btn').addEventListener('click', () => {
            if (this.options.onClose) this.options.onClose();
        });
        
        // 模板选择
        this.container.querySelector('#template-select').addEventListener('change', (e) => {
            this.onTemplateChange(e.target.value);
        });
        
        // 添加自定义字段
        const addFieldBtn = this.container.querySelector('#add-field-btn');
        const fieldInput = this.container.querySelector('#custom-field-input');
        
        addFieldBtn.addEventListener('click', () => this.addCustomField());
        fieldInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addCustomField();
        });
        
        // 提取按钮
        this.container.querySelector('#extract-btn').addEventListener('click', () => {
            this.doExtract();
        });
        
        // 复制结果
        this.container.querySelector('#copy-result-btn').addEventListener('click', () => {
            this.copyResult();
        });
        
        // 导出结果
        this.container.querySelector('#export-result-btn').addEventListener('click', () => {
            this.exportResult();
        });
    }
    
    onTemplateChange(templateId) {
        const tagsContainer = this.container.querySelector('#field-tags');
        tagsContainer.innerHTML = '';
        this.customFields = [];
        
        if (templateId && this.templates[templateId]) {
            const fields = this.templates[templateId].fields;
            fields.forEach(field => this.addFieldTag(field, false));
        }
        
        this.updateExtractButton();
    }
    
    addCustomField() {
        const input = this.container.querySelector('#custom-field-input');
        const field = input.value.trim();
        
        if (field && !this.customFields.includes(field)) {
            this.addFieldTag(field, true);
            this.customFields.push(field);
            input.value = '';
            this.updateExtractButton();
        }
    }
    
    addFieldTag(field, isCustom = false) {
        const tagsContainer = this.container.querySelector('#field-tags');
        const tag = document.createElement('span');
        tag.className = 'field-tag';
        tag.innerHTML = `
            ${field}
            <span class="remove-tag" data-field="${field}">&times;</span>
        `;
        
        tag.querySelector('.remove-tag').addEventListener('click', () => {
            tag.remove();
            if (isCustom) {
                this.customFields = this.customFields.filter(f => f !== field);
            }
            this.updateExtractButton();
        });
        
        tagsContainer.appendChild(tag);
    }
    
    getSelectedFields() {
        const templateId = this.container.querySelector('#template-select').value;
        
        if (templateId && this.templates[templateId]) {
            return [...this.templates[templateId].fields, ...this.customFields];
        }
        
        return this.customFields;
    }
    
    updateExtractButton() {
        const btn = this.container.querySelector('#extract-btn');
        const fields = this.getSelectedFields();
        btn.disabled = fields.length === 0 || !this.currentJobId || this.isLoading;
    }
    
    setJobId(jobId) {
        this.currentJobId = jobId;
        this.updateExtractButton();
    }
    
    async doExtract() {
        if (this.isLoading || !this.currentJobId) return;
        
        const fields = this.getSelectedFields();
        if (fields.length === 0) return;
        
        const templateId = this.container.querySelector('#template-select').value;
        
        this.setLoading(true);
        this.hideError();
        this.hideResult();
        
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/extract-info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: this.currentJobId,
                    fields: this.customFields.length > 0 ? fields : null,
                    template: templateId || null
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.lastResult = data.data;
                this.showResult(data.data);
                if (this.options.onExtract) {
                    this.options.onExtract(data.data);
                }
            } else {
                this.showError(data.error || '提取失败');
            }
        } catch (error) {
            console.error('Extract failed:', error);
            this.showError('网络错误，请稍后重试');
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        const btn = this.container.querySelector('#extract-btn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoading = btn.querySelector('.btn-loading');
        
        btnText.style.display = loading ? 'none' : 'inline';
        btnLoading.style.display = loading ? 'inline' : 'none';
        btn.disabled = loading;
    }
    
    showResult(result) {
        const section = this.container.querySelector('#result-section');
        const content = this.container.querySelector('#result-content');
        const meta = this.container.querySelector('#result-meta');
        
        // 渲染字段结果
        let html = '';
        Object.entries(result.fields || {}).forEach(([key, value]) => {
            const valueClass = value === null ? 'null' : '';
            const displayValue = value === null ? '未找到' : value;
            html += `
                <div class="result-item">
                    <span class="result-key">${key}：</span>
                    <span class="result-value ${valueClass}">${displayValue}</span>
                </div>
            `;
        });
        content.innerHTML = html;
        
        // 渲染元信息
        const confidence = (result.confidence * 100).toFixed(0);
        const time = result.processing_time.toFixed(2);
        meta.innerHTML = `置信度: ${confidence}% | 耗时: ${time}s`;
        
        if (result.warnings && result.warnings.length > 0) {
            meta.innerHTML += ` | ⚠️ ${result.warnings.join(', ')}`;
        }
        
        section.style.display = 'block';
    }
    
    hideResult() {
        this.container.querySelector('#result-section').style.display = 'none';
    }
    
    showError(message) {
        const section = this.container.querySelector('#error-section');
        const messageEl = this.container.querySelector('#error-message');
        messageEl.textContent = message;
        section.style.display = 'block';
    }
    
    hideError() {
        this.container.querySelector('#error-section').style.display = 'none';
    }
    
    copyResult() {
        if (!this.lastResult) return;
        
        const text = JSON.stringify(this.lastResult.fields, null, 2);
        navigator.clipboard.writeText(text).then(() => {
            alert('结果已复制到剪贴板');
        });
    }
    
    exportResult() {
        if (!this.lastResult) return;
        
        const blob = new Blob([JSON.stringify(this.lastResult, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `extract_${this.currentJobId}_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SmartExtractPanel;
}
